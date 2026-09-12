import { useEffect, useRef, useState } from "react";
import { Maximize2, RotateCcw } from "lucide-react";
import { createHabitat } from "../scene/habitat";
import type { Job, State } from "../types";

export default function World({
  jobs,
  state,
  selected,
  onSelect,
}: {
  jobs: Job[];
  state: State | null;
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const canvas = useRef<HTMLCanvasElement>(null),
    labels = useRef<HTMLDivElement>(null),
    root = useRef<HTMLElement>(null);
  const instance = useRef<ReturnType<typeof createHabitat> | null>(null),
    select = useRef(onSelect);
  select.current = onSelect;
  const [error, setError] = useState("");
  useEffect(() => {
    if (!canvas.current || !labels.current || !jobs.length) return;
    try {
      instance.current = createHabitat(
        canvas.current,
        jobs,
        (id) => select.current(id),
        labels.current,
      );
    } catch (e) {
      setError(
        "Your browser could not start WebGL. The job list and feedback controls are still available.",
      );
      console.error(e);
    }
    return () => instance.current?.dispose();
  }, [jobs]);
  useEffect(() => {
    if (state) instance.current?.update(state, selected);
  }, [state, selected]);
  return (
    <section
      className="habitat"
      ref={root}
      aria-label="Interactive job habitat"
    >
      <canvas
        ref={canvas}
        aria-label="Three-dimensional habitat. Use the adjacent job list for keyboard access."
      />
      <div ref={labels} className="world-labels" />
      <div className="habitat-heading">
        <span className="live-dot" />
        <span>
          {state?.landed
            ? "Landed. Like it or pass."
            : state?.running
              ? "Searching your jobs"
              : "Ready to explore"}
        </span>
      </div>
      <div className="habitat-caption">
        <span className="habitat-coordinate">
          JOBS / {jobs.length.toString().padStart(2, "0")} MATCHES
        </span>
        <p>
          Real jobs.
          <br />
          <em>Your next move.</em>
        </p>
      </div>
      <div className="world-controls">
        <button
          className="icon-button"
          title="Reset camera"
          aria-label="Reset camera"
          onClick={() => instance.current?.resetCamera()}
        >
          <RotateCcw size={16} />
        </button>
        <button
          className="icon-button"
          title="Fullscreen habitat"
          aria-label="Fullscreen habitat"
          onClick={() =>
            root.current
              ?.requestFullscreen()
              .catch(() =>
                setError("Fullscreen is unavailable in this browser."),
              )
          }
        >
          <Maximize2 size={16} />
        </button>
      </div>
      <div className="world-foot">
        <span>Drag to orbit · Scroll to zoom</span>
        <span className="compass">
          N <span>↑</span>
        </span>
      </div>
      {error && (
        <div className="canvas-error" role="status">
          {error}
        </div>
      )}
    </section>
  );
}
