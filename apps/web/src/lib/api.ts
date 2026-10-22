export type HealthResponse = { status: "ok"; service: "resolveflow-api" };

export async function checkApiHealth(
  signal: AbortSignal,
): Promise<HealthResponse> {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
  const url = new URL(base);
  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password
  ) {
    throw new Error("Invalid API origin");
  }
  url.pathname = `${url.pathname.replace(/\/$/, "")}/api/v1/health`;
  url.search = "";
  url.hash = "";

  const response = await fetch(url, {
    signal,
    cache: "no-store",
    credentials: "omit",
  });
  if (!response.ok) throw new Error("Health check failed");
  const result: unknown = await response.json();
  if (
    !result ||
    typeof result !== "object" ||
    !("status" in result) ||
    result.status !== "ok" ||
    !("service" in result) ||
    result.service !== "resolveflow-api"
  )
    throw new Error("Unexpected health response");
  return { status: "ok", service: "resolveflow-api" };
}
