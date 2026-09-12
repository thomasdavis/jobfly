"""Full-model integration experiment using a frozen real-job catalog."""
import json
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMBA_NUM_THREADS", "2")
from backend.storage import Store
from backend.engine import Engine
import httpx

root = Path("/mnt/donto-data/donto-resources/research/jobfly-neural-v2")
directory = root / os.getenv("JOBFLY_BENCH_RUN", "integration-state")
store = Store(directory)
if not store.latest() and directory.name != "integration-state":
    seed = Store(root / "integration-state")
    data = seed.latest()
    seed.db.close()
    data.update(marks={}, reasons={}, updates=0, factors=[1.] * len(data["factors"]))
    data["neural"].update(samples={}, ecosystem={})
    store.save(data)
if not store.latest():
    jobs = json.loads((root / "catalog.json").read_text())
    resume = httpx.get("https://registry.jsonresume.org/thomasdavis.json", timeout=30).json()
    store.save(dict(jobs=jobs, resume=resume, source="arbeitnow", marks={}, reasons={}))
store.db.close()
start = time.monotonic()
engine = Engine(directory)
previous = None
while engine.status == "loading":
    if previous != engine.loading_stage:
        previous = engine.loading_stage
        print(round(time.monotonic() - start), previous, flush=True)
    time.sleep(2)
assert engine.status == "ready", engine.error
engine.stopped = True
engine.thread.join(timeout=3)
print("READY", len(engine.jobs), round(time.monotonic() - start), flush=True)
p = engine.policy
initial = p.public_flies()
report = dict(jobs=len(engine.jobs), neurons=engine.brain.n, connections=len(engine.brain.weights), calibration=p.motor_decoder.calibration)
for block in range(12):
    for _ in range(2000):
        p.tick()
    summary = p.summary()
    moved = sum(abs(f["x"]-i["x"]) + abs(f["z"]-i["z"]) > .01 for f,i in zip(p.public_flies(),initial))
    print(dict(block=block, elapsed=round(p.elapsed), explored=summary["explored"], recommendations=len(summary["recommendations"]), moved=moved, landings=p.landings), flush=True)
    engine.persist()
    (root / "swarm-progress.json").write_text(json.dumps(dict(block=block, elapsed=p.elapsed, explored=summary["explored"], recommendations=summary["recommendations"], moved=moved, landings=p.landings)))
    if summary["recommendations"] and moved == p.count and p.landings:
        break
assert moved == p.count
assert p.summary()["recommendations"]
assert p.landings > 0
assert engine.plastic.updates == 0
report["ecosystem"] = p.summary()
report["moved"] = moved
report["landings"] = p.landings
report["activeNeurons"] = int(engine.brain.ever_active.sum())
key = next(iter(p.features))
before = p.decoder.predict(p.features[key])
changed = engine.feedback(key, 1, "Integration experiment: explicit positive feedback")
assert changed > 0
report["reward"] = dict(before=before, after=p.decoder.predict(p.features[key]), **p.last_reward)
report["wallSeconds"] = round(time.monotonic()-start,2)
(root / "swarm-integration.json").write_text(json.dumps(report, indent=2))
print("RESULT", json.dumps({k:v for k,v in report.items() if k != "ecosystem"}), flush=True)
engine.store.db.close()
