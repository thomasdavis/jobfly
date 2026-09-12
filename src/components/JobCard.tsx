import {
  ArrowUpRight,
  Check,
  Heart,
  MapPin,
  MoveRight,
  ThumbsDown,
} from "lucide-react";
import { useState } from "react";
import { display, type Job, type State } from "../types";

export default function JobCard({
  job,
  state,
  busy,
  onFeedback,
  onVisit,
  onDepart,
}: {
  job: Job | null;
  state: State | null;
  busy: boolean;
  onFeedback: (reward: number, reason: string) => Promise<boolean>;
  onVisit: () => void;
  onDepart: () => void;
}) {
  const [reason, setReason] = useState("");
  if (!job)
    return (
      <section className="job-card empty">
        <p>Let curiosity do the searching.</p>
        <span>
          Select a marker or start exploring to meet your first opportunity.
        </span>
      </section>
    );
  const landed = state?.landed === job.id;
  const href =
    typeof job.url === "string" && /^https?:\/\//i.test(job.url)
      ? job.url
      : null;
  async function teach(reward: number) {
    if (await onFeedback(reward, reason)) setReason("");
  }
  return (
    <section
      className={`job-card ${landed ? "has-landed" : ""}`}
      aria-label="Selected opportunity"
    >
      <div className="job-card-head">
        <span className="company-monogram">{job.company.slice(0, 1)}</span>
        <div>
          <span className="company-name">{job.company}</span>
          <span className="job-source">
            {job.source === "example"
              ? "Imaginary company · Example job"
              : "Imported opportunity"}
          </span>
        </div>
        {state?.marks[job.id] === "liked" && (
          <span className="saved-label">
            <Check size={13} /> Liked
          </span>
        )}
        <span className={`landing-badge ${landed ? "arrived" : ""}`}>
          {landed ? "Just landed" : "On the radar"}
        </span>
      </div>
      <div className="job-card-body">
        <div className="job-summary">
          <h2>{job.title}</h2>
          <div className="job-meta">
            <span>
              <MapPin size={13} />
              {display(job.location)}
            </span>
            <span>{display(job.salary)}</span>
          </div>
          <p>{job.description}</p>
          {job.interpretation && (
            <p className="interpretation">{job.interpretation}</p>
          )}
          {href && (
            <a href={href} target="_blank" rel="noreferrer">
              Read the original posting <ArrowUpRight size={14} />
            </a>
          )}
        </div>
        <div className="feedback-panel">
          <p>
            {landed
              ? "Something worth landing on?"
              : "Your fly makes the first move."}
          </p>
          <span className="feedback-hint">
            {landed
              ? "Your feedback teaches its next instinct."
              : "Guide its attention here, or let it wander."}
          </span>
          {landed ? (
            <>
              <label className="sr-only" htmlFor="reason">
                Optional feedback reason
              </label>
              <input
                id="reason"
                value={reason}
                maxLength={2000}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Why? A little context helps. (optional)"
              />
              <div className="feedback-actions">
                <button
                  className="secondary"
                  disabled={busy || !state?.learning}
                  onClick={() => teach(-1)}
                >
                  <ThumbsDown size={15} /> Not for me
                </button>
                <button
                  className="primary reward"
                  disabled={busy || !state?.learning}
                  onClick={() => teach(1)}
                >
                  <Heart size={15} /> I like this
                </button>
              </div>
              <button
                className="text-button"
                disabled={busy}
                onClick={onDepart}
              >
                Keep wandering without feedback <MoveRight size={13} />
              </button>
            </>
          ) : (
            <button
              className="secondary visit"
              disabled={busy || state?.status !== "ready"}
              onClick={onVisit}
            >
              Catch its attention <MoveRight size={16} />
            </button>
          )}
          {landed && !state?.learning && (
            <span className="feedback-hint">
              Learning is paused. Enable it in the neural panel to teach.
            </span>
          )}
        </div>
      </div>
    </section>
  );
}
