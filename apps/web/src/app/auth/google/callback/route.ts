import { appMode } from "@/lib/app-mode";
import { accountDestination } from "@/lib/account-navigation";
import { backendOrigin, sessionCookies } from "@/lib/server-api";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  if (appMode() === "demo") return new Response(null, { status: 404 });
  const headers = new Headers({
    "Cache-Control": "private, no-store",
    "Referrer-Policy": "no-referrer",
    Location: "/login?google=failed",
    Vary: "Cookie",
  });
  const params = new URL(request.url).searchParams;
  const states = params.getAll("state");
  const codes = params.getAll("code");
  if (states.length === 1 && /^[A-Za-z0-9_-]{43}$/.test(states[0])) {
    try {
      const result = await fetch(`${backendOrigin()}/api/v1/auth/google/complete`, {
        method: "POST", redirect: "error", cache: "no-store",
        headers: { cookie: await sessionCookies(), "Content-Type": "application/json" },
        body: JSON.stringify({ state: states[0], code: !params.has("error") &&
          codes.length === 1 && codes[0].length <= 2048 ? codes[0] : null }),
        signal: AbortSignal.timeout(15000),
      });
      if (result.ok) {
        const { destination } = await result.json();
        headers.set("Location", destination === "/verification-required" ? destination : accountDestination(destination));
        for (const cookie of result.headers.getSetCookie()) headers.append("Set-Cookie", cookie);
      }
    } catch {
      // Leave only the generic failure on the clean sign-in URL.
    }
  }
  return new Response(null, { status: 303, headers });
}
