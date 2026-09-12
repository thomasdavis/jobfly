import { useEffect, useRef, useState } from "react";
import { createBrain } from "../scene/brain";
import type { BrainData, State } from "../types";

export default function Brain({
  data,
  state,
  expanded = false,
}: {
  data: BrainData | null;
  state: State | null;
  expanded?: boolean;
}) {
  const canvas = useRef<HTMLCanvasElement>(null),
    instance = useRef<ReturnType<typeof createBrain> | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    if (!canvas.current || !data) return;
    try {
      instance.current = createBrain(canvas.current, data);
    } catch {
      setError(true);
    }
    return () => instance.current?.dispose();
  }, [data, expanded]);
  useEffect(() => {
    if (state) instance.current?.update(state);
  }, [state]);
  return (
    <div className={`brain-view ${expanded ? "expanded" : ""}`}>
      <canvas
        ref={canvas}
        aria-label="Actual MaleCNS neuron positions; light pulses represent simulated spikes"
      />
      {(!data || error) && (
        <div className="brain-loading">
          {error
            ? "3D unavailable — telemetry remains live."
            : state?.status === "error"
              ? "Connectome unavailable"
              : "Loading the connectome…"}
        </div>
      )}
      <div className="brain-orientation">
        L<span>MaleCNS v1.0</span>R
      </div>
    </div>
  );
}
