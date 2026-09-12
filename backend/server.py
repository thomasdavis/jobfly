import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .engine import Engine
from .jobs import annotate, fetch_resume_jobs
from .sessions import SessionPool
from .onboarding import router, session_exists

pool = None


@asynccontextmanager
async def lifespan(app):
    global pool
    pool = SessionPool(Engine)
    yield
    pool.close()


app = FastAPI(title="Jobfly", lifespan=lifespan)
app.include_router(router)


@app.get("/healthz")
def health():
    model = Path(os.getenv("FLY_DATA", "/mnt/donto-data/donto-resources/research/jobfly-runtime/brain"))
    present = (model / "weights.npz").exists() and (model / "brain.npz").exists()
    return JSONResponse({"service": "jobfly", "model_files": present}, status_code=200 if present else 503)


@app.middleware("http")
async def local_guard(request: Request, call_next):
    # The signed cookie selects an isolated brain and private learning history.
    origin = request.headers.get("origin")
    if request.method not in ("GET", "HEAD") and origin:
        from urllib.parse import urlparse
        allowed = {"localhost", "127.0.0.1", os.getenv("JOBFLY_HOST", "fly.jsonresume.org")}
        if urlparse(origin).hostname not in allowed:
            return JSONResponse({"detail": "Cross-site actions are not allowed."}, status_code=403)
    if request.url.path.startswith("/api/"):
        token = request.headers.get("X-Session-Id") or request.query_params.get("session")
        if token and not session_exists(token):
            return JSONResponse({"detail": "This session link is invalid. Start a new session."}, status_code=404)
        public = {"/api/thomas", "/api/convert", "/api/sessions"}
        if not token and request.url.path not in public:
            return JSONResponse({"detail": "Open a session link or start a new session."}, status_code=401)
        request.state.session_id = token
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response
    return await call_next(request)


def get_engine(request: Request):
    return pool.get(request.state.session_id)


SessionEngine = Annotated[Engine, Depends(get_engine)]


def ready(engine):
    if engine.status != "ready":
        raise HTTPException(503, engine.error or "The connectome is loading.")


@app.get("/api/state")
def state(engine: SessionEngine):
    return engine.snapshot()


@app.get("/api/brain")
def brain(engine: SessionEngine):
    ready(engine)
    return engine.map_data


@app.get("/api/jobs")
def jobs(engine: SessionEngine):
    with engine.lock:
        return dict(jobs=engine.jobs, source=engine.source, llm=bool(os.getenv("OPENAI_API_KEY")))


@app.get("/api/events")
async def events(request: Request, engine: SessionEngine):
    async def stream():
        with engine.lock:
            engine.clients += 1
        try:
            while not await request.is_disconnected():
                yield "data: " + json.dumps(engine.snapshot()) + "\n\n"
                await asyncio.sleep(.15)
        finally:
            with engine.lock:
                engine.clients -= 1
    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


class Control(BaseModel):
    action: str
    jobId: str | None = None


@app.post("/api/control")
def control(body: Control, engine: SessionEngine):
    ready(engine)
    with engine.lock:
        if body.action == "play":
            if not engine.jobs:
                raise HTTPException(409, "Add a resume to find jobs first.")
            engine.running = True
        elif body.action == "pause":
            engine.running = False
        elif body.action == "depart":
            engine.depart()
        elif body.action == "learning":
            engine.learning_enabled = not engine.learning_enabled
        elif body.action == "visit":
            ids = [j["id"] for j in engine.jobs]
            if body.jobId not in ids:
                raise HTTPException(404, "Job not found.")
            engine.depart()
            engine.target = ids.index(body.jobId)
            engine.plastic.eligibility[:] = 0
            engine.running = True
        else:
            raise HTTPException(400, "Unknown control.")
    return engine.snapshot()


class Feedback(BaseModel):
    jobId: str
    reward: int = Field(ge=-1, le=1)
    reason: str = Field(default="", max_length=2000)


@app.post("/api/feedback")
def feedback(body: Feedback, engine: SessionEngine):
    ready(engine)
    if body.reward == 0:
        raise HTTPException(400, "Choose like or dislike; use depart to skip without learning.")
    try:
        return dict(changed=engine.feedback(body.jobId, body.reward, body.reason))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


class ImportData(BaseModel):
    jobs: list[dict] = Field(min_length=1, max_length=100)


def validate_jobs(rows):
    result, seen = [], set()
    for i, row in enumerate(rows):
        identifier = str(row.get("id", i))
        if identifier in seen:
            raise ValueError("Job ids must be unique.")
        seen.add(identifier)
        if not isinstance(row.get("title"), str) or not isinstance(row.get("company"), str) or not row["title"].strip() or not row["company"].strip():
            raise ValueError("Each job needs a title and company.")
        if len(row["title"]) > 300 or len(row["company"]) > 200:
            raise ValueError("Job titles must be under 300 characters and company names under 200.")
        result.append({**row, "id": identifier, "description": str(row.get("description", ""))[:12000],
                       "source": row.get("source", "imported")})
    return result


class ResumeData(BaseModel):
    resume: dict


@app.post("/api/resume")
def resume(body: ResumeData, engine: SessionEngine):
    ready(engine)
    if not body.resume.get("basics"):
        raise HTTPException(400, "Choose a JSON Resume with a basics section.")
    try:
        rows = validate_jobs(fetch_resume_jobs(body.resume))
        engine.replace_jobs(rows, rows[0]["source"], body.resume)
        return {"count": len(rows)}
    except Exception as exc:
        raise HTTPException(502, f"Could not load matches: {exc}") from exc


@app.post("/api/interpret")
def interpret(engine: SessionEngine):
    ready(engine)
    with engine.lock:
        rows = list(engine.jobs)
        resume_data = engine.resume
        feedback_text = json.dumps(engine.reasons)
        revision = engine.revision
    try:
        interpreted = annotate(rows, resume_data, feedback_text)
        with engine.lock:
            if engine.revision != revision:
                raise ValueError("The habitat changed during interpretation. Try again.")
            engine.replace_jobs(interpreted, engine.source, resume_data)
        return {"count": len(interpreted)}
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/history")
def history(engine: SessionEngine):
    with engine.lock:
        return engine.store.history()


dist = Path(__file__).resolve().parents[1] / "dist"
if dist.exists():
    @app.get("/s/{identifier}")
    def session_page(identifier: str):
        return FileResponse(dist / "index.html", headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Robots-Tag": "noindex, nofollow"})

    app.mount("/", StaticFiles(directory=dist, html=True), name="app")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.server:app", host=os.getenv("JOBFLY_BIND", "127.0.0.1"), port=int(os.getenv("JOBFLY_PORT", "8787")), access_log=False)
