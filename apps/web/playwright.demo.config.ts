import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests-demo", fullyParallel: false, workers: 1, retries: 0, timeout: 30000,
  reporter: "list", use: { baseURL: "http://127.0.0.1:3200", channel: "chrome", headless: true, trace: "off", screenshot: "only-on-failure" },
  webServer: {
    command: "npm run start -- --port 3200", url: "http://127.0.0.1:3200/demo", reuseExistingServer: false,
    env: { NEXT_PUBLIC_APP_MODE: "demo", DEMO_LIVE_AI_ENABLED: "false", API_INTERNAL_URL: "http://127.0.0.1:9", NEXT_PUBLIC_API_BASE_URL: "http://127.0.0.1:9", NEXT_TELEMETRY_DISABLED: "1" },
    timeout: 60000,
  },
});
