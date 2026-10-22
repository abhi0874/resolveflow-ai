import { defineConfig } from "@playwright/test";
if (process.env.RESOLVEFLOW_E2E_ISOLATED !== "1")
  throw new Error(
    "Run apps/api/scripts/test_browser.py to provision an isolated database.",
  );
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 30000,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3100",
    channel: "chrome",
    headless: true,
    screenshot: "only-on-failure",
    trace: "off",
  },
});
