import type { NextConfig } from "next";

import { appMode, validateDemoLiveConfig } from "./src/lib/app-mode";
const demo = appMode() === "demo";
validateDemoLiveConfig();

// Static CSP preserves prerendering. Inline hydration/styles remain necessary;
// this is an origin restriction policy, not a nonce-based XSS defense.
const demoCsp = [
  "default-src 'self'", "script-src 'self' 'unsafe-inline'",
  "script-src-attr 'none'", "style-src 'self' 'unsafe-inline'",
  "connect-src 'self'", "img-src 'self' data:", "font-src 'self'",
  "object-src 'none'", "base-uri 'none'", "form-action 'self'",
  "frame-ancestors 'none'", "frame-src 'none'", "worker-src 'none'",
].join("; ");

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: [
      ...(demo && process.env.NODE_ENV === "production" ? [{ key: "Content-Security-Policy", value: demoCsp }] : []),
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "X-Frame-Options", value: "DENY" },
      { key: "Referrer-Policy", value: "same-origin" },
      ...(process.env.NODE_ENV === "production" ? [{ key: "Strict-Transport-Security", value: "max-age=31536000" }] : []),
    ] }];
  },
};

export default nextConfig;
