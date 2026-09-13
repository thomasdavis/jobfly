export interface Job {
  id: string;
  title: string;
  company: string;
  description: string;
  location?: unknown;
  salary?: unknown;
  url?: string | null;
  source: string;
  x: number;
  z: number;
  interpretation?: string;
  similarity?: number | null;
}
export interface State {
  status: string;
  error: string | null;
  running: boolean;
  fly: { x: number; z: number; heading: number };
  target: string | null;
  landed: string | null;
  spikes: number[];
  totalSpikes: number;
  motor: number[];
  drive: number[];
  stepMs: number;
  elapsed: number;
  revision: number;
  source: string;
  updates: number;
  changed: number;
  landings: number;
  learning: boolean;
  marks: Record<string, string>;
  preferences: Record<string, number>;
  loadingStage: string;
  phase: string;
  intervention: string;
  activeNeurons: number;
  decoderSamples: number;
  swarm: {
    id: number;
    x: number;
    z: number;
    heading: number;
    phase: string;
    target: string | null;
    attending: string | null;
    landed: string | null;
    motor: number[];
    active: boolean;
    brainSteps: number;
    activeNeurons: number;
    learningUpdates: number;
    pendingFeedback: number;
  }[];
  ecosystem: {
    explored: number;
    total: number;
    settling: boolean;
    minimumSeconds: number;
    recommendations: string[];
    activeFly: number;
    sharedBrain: boolean;
    independentBrains: number;
    feedback: { id: number; completed: number[]; changed: number }[];
    activity: Record<
      string,
      {
        visits: number;
        flies: number;
        landings: number;
        value: number;
        mature: boolean;
      }
    >;
  } | null;
}
export interface BrainData {
  positions: number[];
  classes: number[];
  neurons: number;
  connections: number;
  mapped: number;
  learningEdges: number;
  kc: number;
  mbon: number;
}
export const display = (value: unknown) =>
  typeof value === "string"
    ? value
    : value && typeof value === "object"
      ? Object.values(value)
          .filter((v) => typeof v === "string")
          .join(" · ")
      : "Not specified";
