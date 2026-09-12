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
