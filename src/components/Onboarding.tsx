import { useRef, useState } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  Bug,
  Check,
  FileText,
  Upload,
} from "lucide-react";
import { api } from "../api";

export default function Onboarding() {
  const input = useRef<HTMLInputElement>(null);
  const [draft, setDraft] = useState("");
  const [review, setReview] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  async function run(label: string, work: () => Promise<void>) {
    setBusy(label);
    setError("");
    try {
      await work();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  function accept(data: unknown) {
    setDraft(JSON.stringify(data, null, 2));
    setReview(true);
  }
  async function upload(file: File) {
    await run(
      file.name.endsWith(".json")
        ? "Reading your resume…"
        : "Converting your resume…",
      async () => {
        if (file.size > 5_000_000) throw new Error("Choose a file under 5 MB.");
        const body = new FormData();
        body.append("file", file);
        const response = await fetch("/api/convert", { method: "POST", body });
        const data = await response.json();
        if (!response.ok)
          throw new Error(
            data.detail || "Could not read this file. Try another format.",
          );
        accept(data);
      },
    );
  }
  function download() {
    try {
      const blob = new Blob([JSON.stringify(JSON.parse(draft), null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob),
        anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "resume.json";
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      setError("Check the JSON syntax before downloading.");
    }
  }
  let name = "Your resume",
    role = "";
  try {
    const data = JSON.parse(draft);
    name = typeof data.basics?.name === "string" ? data.basics.name : name;
    role = typeof data.basics?.label === "string" ? data.basics.label : "";
  } catch {
    /* Editable draft may be incomplete. */
  }
  return (
    <div className="setup-shell">
      <header className="setup-header">
        <a className="brand" href="/">
          <Bug size={26} />
          <span>
            jobfly<span className="brand-period">.</span>
          </span>
        </a>
        <a href="https://jsonresume.org" target="_blank" rel="noreferrer">
          By JSON Resume ↗
        </a>
      </header>
      <main className="setup-layout">
        <section className="setup-intro">
          <span className="setup-kicker">
            A different way to find your next job
          </span>
          <h1>
            Your next move.
            <br />
            <em>A fly’s brain.</em>
          </h1>
          <p>
            Real jobs, your resume, and a swarm with time to explore. Watch what
            draws their attention. React whenever you feel like it.
          </p>
          <ol className="setup-steps">
            <li>
              <span>01</span>
              <div>
                <strong>Add your resume</strong>
                <p>Upload a file or try Thomas Davis’s.</p>
              </div>
            </li>
            <li>
              <span>02</span>
              <div>
                <strong>Explore real jobs</strong>
                <p>A whole world of jobs. Twenty-four flies.</p>
              </div>
            </li>
            <li>
              <span>03</span>
              <div>
                <strong>See what keeps their attention</strong>
                <p>Let discoveries build. Feedback is optional.</p>
              </div>
            </li>
          </ol>
          <div className="setup-footnote">
            <Bug size={18} />
            <span>
              166,700 simulated neurons.
              <br />
              You still make the career decisions.
            </span>
          </div>
        </section>
        <section className="setup-form" aria-label="Resume setup">
          <div className="setup-form-heading">
            <span className="step-label">
              {review ? "02 / Review" : "01 / Your resume"}
            </span>
            <FileText size={22} />
          </div>
          <h2>{review ? "Looks like you?" : "Start with your resume."}</h2>
          <p>
            {review
              ? "Check the details. You can edit anything before searching."
              : "PDF, Word, text, or JSON Resume. We’ll handle the format."}
          </p>
          {!review ? (
            <>
              <button
                className={`upload-zone ${dragging ? "dragging" : ""}`}
                disabled={!!busy}
                onClick={() => input.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  if (!busy) setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragging(false);
                  if (!busy && e.dataTransfer.files[0])
                    void upload(e.dataTransfer.files[0]);
                }}
              >
                <Upload size={26} />
                <strong>Upload your resume</strong>
                <span>Drop a file here or click to browse</span>
                <small>PDF, DOCX, TXT, JSON · up to 5 MB</small>
              </button>
              <input
                ref={input}
                className="sr-only"
                type="file"
                aria-label="Upload resume file"
                accept=".pdf,.docx,.txt,.json"
                disabled={!!busy}
                onChange={(e) => {
                  if (e.target.files?.[0]) void upload(e.target.files[0]);
                  e.target.value = "";
                }}
              />
              <div className="setup-divider">
                <span>or</span>
              </div>
              <button
                className="thomas-button"
                disabled={!!busy}
                onClick={() =>
                  void run("Loading Thomas’s resume…", async () =>
                    accept(await api("thomas")),
                  )
                }
              >
                <span className="thomas-avatar">TD</span>
                <span>
                  <strong>Use thomasdavis resume</strong>
                  <small>Thomas Davis · JSON Resume founder</small>
                </span>
                <ArrowRight size={18} />
              </button>
              <button
                className="paste-button"
                disabled={!!busy}
                onClick={() => {
                  setReview(true);
                  setDraft(
                    '{\n  "basics": {\n    "name": "",\n    "label": "",\n    "summary": ""\n  }\n}',
                  );
                }}
              >
                Paste JSON Resume instead
              </button>
            </>
          ) : (
            <>
              <div className="resume-summary">
                <Check size={18} />
                <div>
                  <strong>{name}</strong>
                  <span>{role || "JSON Resume"}</span>
                </div>
                <button
                  className="icon-button"
                  aria-label="Download resume.json"
                  title="Download resume.json"
                  onClick={download}
                >
                  <ArrowDownToLine size={17} />
                </button>
              </div>
              <label className="json-label" htmlFor="resume-json">
                resume.json <span>Editable</span>
              </label>
              <textarea
                id="resume-json"
                className="resume-editor"
                spellCheck={false}
                value={draft}
                disabled={!!busy}
                onChange={(e) => setDraft(e.target.value)}
              />
              <button
                className="primary start-session"
                disabled={!!busy}
                onClick={() =>
                  void run("Finding jobs for you…", async () => {
                    let resume;
                    try {
                      resume = JSON.parse(draft);
                    } catch {
                      throw new Error(
                        "This JSON isn’t valid yet. Check for a missing comma or bracket.",
                      );
                    }
                    const result = await api<{ url: string }>("sessions", {
                      resume,
                    });
                    location.assign(result.url);
                  })
                }
              >
                Find my jobs <ArrowRight size={17} />
              </button>
              <button
                className="paste-button"
                disabled={!!busy}
                onClick={() => {
                  setReview(false);
                  setError("");
                }}
              >
                Choose another resume
              </button>
            </>
          )}
          {busy && (
            <div className="setup-progress" role="status">
              <span className="progress-dot" />
              {busy}
              <small>This can take up to a minute. Keep this page open.</small>
            </div>
          )}
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <p className="setup-privacy">
            Document text is sent to an AI provider through OpenRouter for
            conversion. JSON files stay as they are. Your resume, jobs, and
            feedback are saved to your session. Keep the session link
            private—anyone with it can open and update it.
          </p>
        </section>
      </main>
      <footer>
        <span>Built with the fly.ai connectome.</span>
        <a
          href="https://github.com/thomasdavis/jobfly"
          target="_blank"
          rel="noreferrer"
        >
          View on GitHub ↗
        </a>
      </footer>
    </div>
  );
}
