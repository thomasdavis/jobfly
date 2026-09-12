export async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(
    `/api/${path}`,
    body === undefined
      ? undefined
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  const data = await response.json();
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "That request could not be completed.",
    );
  return data;
}

let bootstrap: Promise<import("./types").State> | null = null;
export function bootstrapSession() {
  if (!bootstrap)
    bootstrap = api<import("./types").State>("state").catch((error) => {
      bootstrap = null;
      throw error;
    });
  return bootstrap;
}
