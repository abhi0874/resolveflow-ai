/** Fail-closed future provider boundary. No SDK, key lookup or outbound request. */
export function POST() {
  return Response.json({ error: { code: "demo_live_disabled", message: "Live inference is disabled. Explore the precomputed examples instead." } }, { status: 403, headers: { "Cache-Control": "no-store" } });
}
