import { test, expect } from "@playwright/test";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
test("client bundles contain no server-only secret canary", () => {
  function files(path: string): string[] { return readdirSync(path, { withFileTypes: true }).flatMap(entry => entry.isDirectory() ? files(join(path, entry.name)) : [join(path, entry.name)]); }
  const assets = files(".next/static").filter(path => path.endsWith(".js"));
  expect(assets.length).toBeGreaterThan(0);
  for (const asset of assets) expect(readFileSync(asset, "utf8").includes("resolveflow-server-only-test-canary-13")).toBe(false);
});
