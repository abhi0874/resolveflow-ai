import "server-only";
import { appMode } from "./app-mode";
import { cookies } from "next/headers";

export function backendOrigin(): string {
  const value =
    process.env.API_INTERNAL_URL ??
    (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "");
  if (!value) throw new Error("API_INTERNAL_URL is required");
  const url = new URL(value);
  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    url.pathname !== "/"
  ) {
    throw new Error("API_INTERNAL_URL must be a server-only HTTP(S) origin");
  }
  return url.origin;
}

export async function sessionCookies(): Promise<string> {
  const jar = await cookies();
  return ["resolveflow_session", "__Host-resolveflow_session"]
    .flatMap((name) => {
      const value = jar.get(name)?.value;
      return value && /^[A-Za-z0-9_-]{43}$/.test(value)
        ? [`${name}=${value}`]
        : [];
    })
    .join("; ");
}

export async function serverGet(path: string): Promise<Response> {
  if (appMode() === "demo") return new Response(null, { status: 401 });
  return fetch(`${backendOrigin()}/api/v1${path}`, {
    headers: { cookie: await sessionCookies() },
    cache: "no-store",
    redirect: "error",
    signal: AbortSignal.timeout(10000),
  });
}
