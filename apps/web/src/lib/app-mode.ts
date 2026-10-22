/** Deployment configuration, never chosen from a URL, cookie or request header. */
export function appMode(): "full" | "demo" {
  const mode = process.env.NEXT_PUBLIC_APP_MODE ?? "full";
  if (mode !== "full" && mode !== "demo") throw new Error("NEXT_PUBLIC_APP_MODE must be full or demo");
  return mode;
}
export function validateDemoLiveConfig(): void {
  const value = process.env.DEMO_LIVE_AI_ENABLED;
  if (value !== undefined && value !== "false") throw new Error("Public demo live inference is unsupported. Set DEMO_LIVE_AI_ENABLED=false.");
}
