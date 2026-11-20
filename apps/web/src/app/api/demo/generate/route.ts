import { appMode } from "@/lib/app-mode";

/** Fail-closed future provider boundary. No SDK, key lookup or outbound request. */
export function POST() {
  if (appMode() !== "demo") return new Response(null, { status: 404 });
  return Response.json({ error: { code: "demo_live_disabled", message: "Live inference is disabled. Explore the precomputed examples instead." } }, { status: 403, headers: { "Cache-Control": "no-store" } });
}
