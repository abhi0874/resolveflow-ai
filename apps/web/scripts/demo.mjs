// Cross-platform local commands; never link, provision or deploy a hosted service.
import { spawnSync } from "node:child_process";
const commands = { build: ["build", "--webpack"], start: ["start", "--hostname", "127.0.0.1", "--port", "3200"], dev: ["dev", "--webpack", "--hostname", "127.0.0.1", "--port", "3200"] };
const command = commands[process.argv[2]];
if (!command) throw new Error("Choose build, start or dev");
const result = spawnSync(process.execPath, ["node_modules/next/dist/bin/next", ...command], {
  stdio: "inherit", env: { ...process.env, NEXT_PUBLIC_APP_MODE: "demo", DEMO_LIVE_AI_ENABLED: "false", NEXT_TELEMETRY_DISABLED: "1" },
});
process.exit(result.status ?? 1);
