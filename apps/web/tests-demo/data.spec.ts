import { test, expect } from "@playwright/test";
import { fixtures } from "../src/lib/demo/fixtures";
import { apply, createDemoSource, STORAGE_KEY, validAction } from "../src/lib/demo/store";
import { demoAnalytics } from "../src/lib/demo/analytics";
import { appMode, validateDemoLiveConfig } from "../src/lib/app-mode";

test("fixture relationships, citations and analytics are consistent", () => {
  const data = fixtures(); const passages = data.documents.flatMap(d => d.passages.map(p => p.id));
  for (const s of data.scenarios) { expect(data.tickets.some(t => t.id === s.ticketId)).toBe(true); for (const id of s.evidence) { expect(passages).toContain(id); expect(s.draft).toContain(`[${id}]`); } }
  const metrics = demoAnalytics(data, "2026-10-01", "2026-10-21");
  expect(metrics.tickets.total).toBe(8); expect(metrics.tickets.statuses.reduce((n, b) => n + b.count, 0)).toBe(8);
  expect(metrics.tickets.resolution_median_seconds.value).toBe(18000);
  expect(metrics.workflows.total).toBe(5); expect(metrics.reviews.approval_rate.value).toBe(.5);
  expect(metrics.knowledge_base.chunks).toBe(passages.length); expect(metrics.knowledge_base.indexed).toBe(0);
  expect(metrics.jobs.initial_wait_average_seconds.value).toBeNull();
  expect(demoAnalytics(data, "2020-01-01", "2020-01-02").reviews.approval_rate.value).toBeNull();
  expect(() => demoAnalytics(data, "2020-01-01", "2026-01-02")).toThrow();
});
test("edits update metrics without mutating fixtures; abstention and duplicate decisions fail closed", () => {
  const original = fixtures(); const changed = apply(original, { type: "status", id: "refund", value: "resolved" });
  expect(original.tickets[0].status).toBe("waiting_for_approval");
  expect(demoAnalytics(changed, "2026-10-01", "2026-10-21").tickets.statuses.find(b => b.label === "resolved")?.count).toBe(3);
  expect(() => apply(original, { type: "review", id: "insufficient", value: "approved" })).toThrow();
  const reviewed = apply(original, { type: "review", id: "billing", value: "approved" });
  expect(demoAnalytics(reviewed, "2026-10-01", "2026-10-21").reviews.approval_rate.value).toBeCloseTo(2 / 3);
  expect(() => apply(reviewed, { type: "review", id: "billing", value: "rejected" })).toThrow();
});
test("session journal validates untrusted storage, caps actions and removes only its own key", () => {
  const saved = new Map<string, string>([["unrelated", "preserve"]]);
  const storage = { getItem: (key: string) => saved.get(key) ?? null, setItem: (key: string, value: string) => { saved.set(key, value); }, removeItem: (key: string) => { saved.delete(key); } };
  let source = createDemoSource(storage); source.dispatch({ type: "note", id: "refund", value: "Synthetic local note" });
  expect(createDemoSource(storage).read().tickets[0].notes).toContain("Synthetic local note");
  source.reset(); expect(saved.get("unrelated")).toBe("preserve"); expect(saved.has(STORAGE_KEY)).toBe(false);
  for (const raw of ['{"tickets":[]}', '[{"type":"status","id":"refund","value":"root"}]', 'x'.repeat(180001)]) {
    saved.set(STORAGE_KEY, raw); source = createDemoSource(storage); expect(source.notice).toContain("could not be restored"); expect(source.read().tickets).toHaveLength(8);
  }
  expect(validAction({ type: "note", id: "refund", value: "x".repeat(501) })).toBe(false);
  expect(validAction({ type: "assign", id: "refund", value: "Maya Chen", secret: true })).toBe(false);
  const blocked = createDemoSource({ getItem: () => null, setItem: () => { throw new Error("Blocked"); }, removeItem: () => { throw new Error("Blocked"); } });
  blocked.dispatch({ type: "assign", id: "refund", value: "Unassigned" });
  expect(blocked.notice).toContain("storage is unavailable"); expect(blocked.read().tickets[0].assignee).toBe("Unassigned");
  blocked.reset(); expect(blocked.read().tickets[0].assignee).toBe("Maya Chen");
  source = createDemoSource(); for (let i = 0; i < 100; i++) source.dispatch({ type: "assign", id: "refund", value: "Unassigned" });
  expect(() => source.dispatch({ type: "assign", id: "refund", value: "Unassigned" })).toThrow();
});
test("configuration rejects unknown modes and any attempt to enable public inference", () => {
  const mode = process.env.NEXT_PUBLIC_APP_MODE, live = process.env.DEMO_LIVE_AI_ENABLED;
  try {
    delete process.env.NEXT_PUBLIC_APP_MODE; expect(appMode()).toBe("full");
    process.env.NEXT_PUBLIC_APP_MODE = "demo"; expect(appMode()).toBe("demo");
    process.env.NEXT_PUBLIC_APP_MODE = "invalid"; expect(() => appMode()).toThrow();
    delete process.env.DEMO_LIVE_AI_ENABLED; expect(() => validateDemoLiveConfig()).not.toThrow();
    process.env.DEMO_LIVE_AI_ENABLED = "true"; expect(() => validateDemoLiveConfig()).toThrow();
  } finally { if (mode === undefined) delete process.env.NEXT_PUBLIC_APP_MODE; else process.env.NEXT_PUBLIC_APP_MODE = mode; if (live === undefined) delete process.env.DEMO_LIVE_AI_ENABLED; else process.env.DEMO_LIVE_AI_ENABLED = live; }
});
