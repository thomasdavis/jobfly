import { useCallback, useEffect, useState } from "react";
import {
  ArrowDownToLine,
  ArrowUpRight,
  BookOpen,
  Bug,
  Check,
  ChevronRight,
  CircleHelp,
  Cpu,
  Heart,
  Leaf,
  Pause,
  Play,
  Sparkles,
  Upload,
} from "lucide-react";
import { api, bootstrapSession } from "./api";
import type { BrainData, Job, State } from "./types";
import World from "./components/World";
import Brain from "./components/Brain";
import JobCard from "./components/JobCard";
import ImportDialog from "./components/ImportDialog";

type History = {
  created: string;
  jobId: string;
  reward: number;
  reason: string;
  changed: number;
};

export default function App() {
  const [state, setState] = useState<State | null>(null),
    [brain, setBrain] = useState<BrainData | null>(null),
    [jobs, setJobs] = useState<Job[]>([]);
  const [selected, setSelected] = useState<string | null>(null),
    [tab, setTab] = useState("habitat"),
    [importing, setImporting] = useState(false),
    [llm, setLlm] = useState(false);
  const [busy, setBusy] = useState(false),
    [message, setMessage] = useState(""),
    [connected, setConnected] = useState(false),
    [history, setHistory] = useState<History[]>([]),
    [help, setHelp] = useState(false);
  const refresh = useCallback(async () => {
    const data = await api<{ jobs: Job[]; llm: boolean }>("jobs");
    setJobs(data.jobs);
    setLlm(data.llm);
  }, []);
  useEffect(() => {
    let stream: EventSource | undefined,
      disposed = false;
    let retry: ReturnType<typeof setTimeout>;
    const connect = () => {
      void bootstrapSession()
        .then((initial) => {
          if (disposed) return;
          setState(initial);
          stream = new EventSource("/api/events");
          stream.onmessage = (event) => {
            setState(JSON.parse(event.data));
            setConnected(true);
          };
          stream.onerror = () => setConnected(false);
        })
        .catch((e) => {
          if (!disposed) {
            setMessage(e.message);
            retry = setTimeout(connect, 15000);
          }
        });
    };
    connect();
    return () => {
      disposed = true;
      clearTimeout(retry);
      stream?.close();
    };
  }, []);
  useEffect(() => {
    if (state?.status === "ready") {
      void refresh().catch((e) => setMessage(e.message));
      if (!brain)
        void api<BrainData>("brain")
          .then(setBrain)
          .catch((e) => setMessage(e.message));
    }
  }, [state?.status, state?.revision, refresh, brain]);
  useEffect(() => {
    if (state?.landed) setSelected(state.landed);
  }, [state?.landed]);
  useEffect(() => {
    if (tab === "notebook")
      void api<History[]>("history")
        .then(setHistory)
        .catch((e) => setMessage(e.message));
  }, [tab, state?.updates]);
  useEffect(() => {
    if (!message) return;
    const timeout = setTimeout(() => setMessage(""), 7000);
    return () => clearTimeout(timeout);
  }, [message]);
  const chosen =
    jobs.find((j) => j.id === (selected || state?.landed || state?.target)) ||
    null;
  const liked = jobs.filter((j) => state?.marks[j.id] === "liked");
  async function action(name: string, body?: unknown) {
    setBusy(true);
    try {
      await api(name, body ?? {});
      return true;
    } catch (e) {
      setMessage((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  }
  async function control(name: string, jobId?: string) {
    await action("control", { action: name, jobId });
  }
  async function feedback(reward: number, reason: string) {
    if (!chosen) return false;
    setBusy(true);
    try {
      const result = await api<{ changed: number }>("feedback", {
        jobId: chosen.id,
        reward,
        reason,
      });
      setMessage(
        `${reward > 0 ? "A good find." : "Noted."} ${result.changed.toLocaleString()} connections updated. Your reason is saved${llm ? " for the interpreter" : ""}.`,
      );
      return true;
    } catch (e) {
      setMessage((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  }
  function download() {
    const blob = new Blob(
      [
        JSON.stringify(
          { title: "My Jobfly discoveries", jobs: liked, feedback: history },
          null,
          2,
        ),
      ],
      { type: "application/json" },
    );
    const url = URL.createObjectURL(blob),
      a = document.createElement("a");
    a.href = url;
    a.download = "jobfly-discoveries.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const ready = state?.status === "ready" && connected;
  const time = state
    ? `${Math.floor(state.elapsed / 60)
        .toString()
        .padStart(2, "0")}:${Math.floor(state.elapsed % 60)
        .toString()
        .padStart(2, "0")}`
    : "00:00";
  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Jobfly home">
          <Bug size={25} strokeWidth={1.4} />
          <span>
            jobfly<span className="brand-period">.</span>
          </span>
        </a>
        <nav aria-label="Main navigation">
          {[
            { id: "habitat", label: "The habitat", icon: Leaf },
            { id: "brain", label: "The brain", icon: Cpu },
            { id: "notebook", label: "Field notes", icon: BookOpen },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={tab === id ? "current" : ""}
              onClick={() => setTab(id)}
            >
              <Icon size={15} />
              {label}
            </button>
          ))}
        </nav>
        <button
          className="import-button"
          onClick={() => setImporting(true)}
          disabled={!ready}
        >
          <Upload size={14} /> Bring your resume <ArrowUpRight size={14} />
        </button>
      </header>
      <main>
        <div className="intro">
          <div>
            <div className="experiment-label">
              <span className="tiny-fly">✳</span> An experiment in finding your
              thing
            </div>
            <h1>
              Follow your <em>instinct.</em>
            </h1>
          </div>
          <div className="intro-aside">
            <p>
              A little fly. A whole brain.
              <br />
              An entirely different job hunt.
            </p>
            <button className="text-button" onClick={() => setHelp(!help)}>
              <CircleHelp size={13} /> How this works
            </button>
          </div>
        </div>
        {help && (
          <section className="help-panel">
            <p>
              Every little pile is a job. The fly follows neural steering
              signals and lands on opportunities. Like or pass to change
              existing learning-circuit connections. Drag either 3D view to look
              around.
            </p>
            <p>
              The connectome is real anatomical data; its dynamics and reward
              rule are simplified experiments. Example jobs are fictional.
              Optional written feedback is saved; the LLM interpreter can
              incorporate it when explicitly run.
            </p>
            <button className="text-button" onClick={() => setHelp(false)}>
              Got it <Check size={14} />
            </button>
          </section>
        )}
        <div className="session-bar">
          <div>
            <span className={`status-dot ${ready ? "online" : ""}`} />
            <strong>
              {!connected
                ? "Connecting"
                : state?.status === "loading"
                  ? "Waking up the brain"
                  : state?.status === "error"
                    ? "Brain needs attention"
                    : state?.landed
                      ? "Waiting for your feedback"
                      : state?.running
                        ? "Your fly is exploring"
                        : "Ready when you are"}
            </strong>
            <span className="session-source">
              {state?.source === "example"
                ? "Example habitat"
                : state?.source === "jsonresume"
                  ? "Your JSON Resume matches"
                  : "Your imported jobs"}
            </span>
          </div>
          <span className="sim-clock">
            {time} <span>SIM TIME</span>
          </span>
          <button
            className="primary play-button"
            disabled={!ready || busy}
            onClick={() => control(state?.running ? "pause" : "play")}
          >
            {state?.running ? <Pause size={14} /> : <Play size={14} />}{" "}
            {state?.running ? "Pause" : "Start exploring"}
          </button>
        </div>
        {state?.error && (
          <div className="form-error" role="alert">
            {state.error}. See the README’s brain setup instructions.
          </div>
        )}
        {tab !== "notebook" ? (
          <div
            className={`observation-deck ${tab === "brain" ? "brain-mode" : ""}`}
          >
            {tab === "habitat" ? (
              <World
                jobs={jobs}
                state={state}
                selected={selected}
                onSelect={setSelected}
              />
            ) : (
              <section className="large-brain">
                <div className="habitat-heading">
                  The whole nervous system <span>Drag to inspect</span>
                </div>
                <Brain data={brain} state={state} expanded />
                <div className="large-brain-caption">
                  166,700 possibilities.
                  <br />
                  <em>One little decision.</em>
                </div>
              </section>
            )}
            <aside className="neural-panel">
              <div className="instrument-title">
                <span>Inside a little mind</span>
                <span className="live-label">
                  <span className={ready ? "live-dot" : ""} />
                  {state?.running && !state?.landed ? "LIVE" : "STANDBY"}
                </span>
              </div>
              {tab === "habitat" && <Brain data={brain} state={state} />}
              <div className="brain-legend">
                <span>
                  <i className="violet" /> Neurons
                </span>
                <span>
                  <i className="peach" /> Learning
                </span>
                <span>
                  <i className="mint" /> Motor
                </span>
              </div>
              <div className="neural-facts">
                <div>
                  <span>Neurons in simulation</span>
                  <strong>{brain?.neurons.toLocaleString() || "—"}</strong>
                </div>
                <div>
                  <span>Connections</span>
                  <strong>
                    {brain
                      ? (brain.connections / 1e6).toFixed(2) + " million"
                      : "—"}
                  </strong>
                </div>
                <div>
                  <span>Spikes / update</span>
                  <strong>{state?.totalSpikes.toLocaleString() || "0"}</strong>
                </div>
              </div>
              <div className="signal-block">
                <h3>Sense → decide → move</h3>
                {[
                  { name: "Left stimulus", value: state?.drive[0] || 0 },
                  { name: "Right stimulus", value: state?.drive[1] || 0 },
                  {
                    name: "Motor · left",
                    value: Math.min((state?.motor[0] || 0) / 4, 1),
                  },
                  {
                    name: "Motor · right",
                    value: Math.min((state?.motor[1] || 0) / 4, 1),
                  },
                ].map((s, i) => (
                  <div className="signal" key={s.name}>
                    <span>{s.name}</span>
                    <div className="signal-track">
                      <i
                        style={{ transform: `scaleX(${s.value})` }}
                        className={i < 2 ? "sensory" : "motor"}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <div className="learning-block">
                <div>
                  <span className="learning-icon">
                    <Sparkles size={17} />
                  </span>
                  <div>
                    <strong>Learning from you</strong>
                    <span>
                      {state?.updates || 0} lessons ·{" "}
                      {state?.changed.toLocaleString() || 0} edges changed last
                    </span>
                  </div>
                  <button
                    className={`switch ${state?.learning ? "on" : ""}`}
                    role="switch"
                    aria-checked={state?.learning || false}
                    aria-label="Enable reward learning"
                    disabled={!ready || busy}
                    onClick={() => control("learning")}
                  >
                    <span />
                  </button>
                </div>
                <p>
                  {state?.updates
                    ? "A little more familiar with what you like."
                    : "A blank slate, with a little curiosity."}
                </p>
              </div>
              <div className="brain-foot">
                {brain?.mapped.toLocaleString() || "—"} mapped positions ·
                spikes sampled
                <br />
                {state?.stepMs || "—"} ms / step · CPU simulation
              </div>
            </aside>
          </div>
        ) : (
          <section className="notebook">
            <div className="notebook-heading">
              <h2>A record of small discoveries.</h2>
              <button className="secondary" onClick={download}>
                <ArrowDownToLine size={15} /> Export discoveries
              </button>
            </div>
            <div className="notebook-columns">
              <div>
                <h3>Your lessons</h3>
                {history.length ? (
                  history.map((h, i) => (
                    <article className="history-row" key={`${h.created}-${i}`}>
                      <span className={h.reward > 0 ? "positive" : "negative"}>
                        {h.reward > 0 ? (
                          <Heart size={16} />
                        ) : (
                          <ChevronRight size={16} />
                        )}
                      </span>
                      <div>
                        <strong>
                          {jobs.find((j) => j.id === h.jobId)?.company ||
                            h.jobId}
                        </strong>
                        <p>
                          {h.reason ||
                            (h.reward > 0
                              ? "A good find."
                              : "Not the right fit.")}
                        </p>
                        <small>
                          {h.changed.toLocaleString()} connections changed ·{" "}
                          {h.created}
                        </small>
                      </div>
                    </article>
                  ))
                ) : (
                  <div className="notes-empty">
                    <BookOpen size={28} />
                    <p>Every preference starts somewhere.</p>
                    <span>
                      Teach your fly after its first landing. Your lessons will
                      collect here.
                    </span>
                  </div>
                )}
              </div>
              <div className="interpreter">
                <Sparkles size={23} />
                <h3>A little help with the words.</h3>
                <p>
                  The optional LLM interpreter compares jobs, your resume and
                  your written feedback. It updates the sensory descriptions the
                  fly receives.
                </p>
                <button
                  className="secondary"
                  disabled={!llm || busy || !ready}
                  onClick={() =>
                    action("interpret").then((ok) => {
                      if (ok)
                        setMessage(
                          "Interpretation complete; check the habitat for updated descriptions.",
                        );
                    })
                  }
                >
                  {busy ? "Interpreting…" : "Interpret this habitat"}
                </button>
                <small>
                  {llm
                    ? "Explicit run · sends jobs, resume and feedback to the configured OpenAI model. API charges may apply."
                    : "Optional: configure OPENAI_API_KEY on the server. The fly works without it."}
                </small>
              </div>
            </div>
          </section>
        )}
        {tab !== "notebook" && (
          <JobCard
            key={chosen?.id || "empty"}
            job={chosen}
            state={state}
            busy={busy}
            onFeedback={feedback}
            onVisit={() => chosen && void control("visit", chosen.id)}
            onDepart={() => control("depart")}
          />
        )}
        <section className="opportunity-list">
          <div className="list-heading">
            <h2>
              {tab === "notebook" ? "Your shortlist" : "Around the habitat"}{" "}
              <span>{tab === "notebook" ? liked.length : jobs.length}</span>
            </h2>
            <span>
              {tab === "notebook"
                ? "Good finds, kept close."
                : "Pick a pile. See what’s underneath."}
            </span>
          </div>
          <div className="job-chips">
            {(tab === "notebook" ? liked : jobs).map((j) => (
              <button
                key={j.id}
                onClick={() => {
                  setSelected(j.id);
                  setTab("habitat");
                }}
                className={selected === j.id ? "selected" : ""}
              >
                <span className="chip-monogram">{j.company.slice(0, 1)}</span>
                <span>
                  <strong>{j.company}</strong>
                  <small>{j.title}</small>
                </span>
                {state?.marks[j.id] === "liked" ? (
                  <Heart size={14} className="liked-heart" />
                ) : (
                  <ArrowUpRight size={14} />
                )}
              </button>
            ))}
          </div>
        </section>
      </main>
      <footer>
        <span>
          <Bug size={14} /> Built on a real fly’s wiring. Guided by you.
        </span>
        <a
          href="https://github.com/alextitonis/fly.ai"
          target="_blank"
          rel="noreferrer"
        >
          fly.ai · MaleCNS / CC BY 4.0 <ArrowUpRight size={12} />
        </a>
      </footer>
      {message && (
        <div className="toast" role="status">
          {message}
          <button
            aria-label="Dismiss notification"
            onClick={() => setMessage("")}
          >
            ×
          </button>
        </div>
      )}
      {importing && (
        <ImportDialog
          llm={llm}
          onClose={() => setImporting(false)}
          onLoaded={() => {
            setSelected(null);
            void refresh();
          }}
        />
      )}
    </div>
  );
}
