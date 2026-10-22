import { test, expect, type APIRequestContext, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";

test.setTimeout(90000);
test.use({ actionTimeout: 20000 });

async function write(request: APIRequestContext, path: string, data: unknown, method = "POST") {
  const csrf = await request.get("/api/v1/auth/csrf");
  return request.fetch("/api/v1" + path, {
    method, data, headers: { Origin: "http://127.0.0.1:3100", "X-CSRF-Token": (await csrf.json()).csrf_token },
  });
}
async function account(page: Page) {
  const response = await write(page.request, "/auth/register", {
    email: `draft-${randomUUID()}@example.com`, password: "draft browser passphrase 42!",
    password_confirmation: "draft browser passphrase 42!",
  });
  expect(response.status()).toBe(201);
  return response.json();
}
async function setup(page: Page, indexed = true) {
  await account(page);
  const spaceResponse = await write(page.request, "/workspaces", { name: "Draft review workspace", slug: `draft-${randomUUID()}` });
  const space = await spaceResponse.json();
  let documentId: string | undefined;
  if (indexed) {
    const csrf = await page.request.get("/api/v1/auth/csrf");
    const upload = await page.request.post(`/api/v1/workspaces/${space.id}/documents`, {
      data: Buffer.from("Customers can request a refund within thirty days of their first purchase."),
      headers: { Origin: "http://127.0.0.1:3100", "X-CSRF-Token": (await csrf.json()).csrf_token,
        "Content-Type": "application/octet-stream", "X-Upload-Filename": "refund-guide.txt" },
    });
    expect(upload.status()).toBe(201);
    documentId = (await upload.json()).id;
    const index = await write(page.request, `/workspaces/${space.id}/documents/${documentId}/index`, {});
    expect((await index.json()).indexing_status).toBe("indexed");
  }
  const ticketResponse = await write(page.request, `/workspaces/${space.id}/tickets`, {
    title: "First purchase refund eligibility", description: "Can I request a refund for my first purchase?",
  });
  expect(ticketResponse.status()).toBe(201);
  const ticket = await ticketResponse.json();
  const base = `/workspaces/${space.id}/tickets/${ticket.id}`;
  await page.goto(`/app/tickets/${ticket.id}?workspace=${space.id}`);
  const panel = page.getByRole("region", { name: "AI workflow", exact: true });
  await expect(panel.getByText("No workflows yet", { exact: true })).toBeVisible({ timeout: 20000 });
  return { panel, base, space, ticket, documentId };
}

test("real workflow stages, persistent pause, review and completion", async ({ page }) => {
  const { panel, base, space } = await setup(page);
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/tickets/*/workflows", async route => {
    if (route.request().method() === "POST") await gate;
    await route.continue();
  });
  await panel.getByRole("button", { name: "Start AI workflow" }).click();
  await expect(panel.getByRole("button", { name: "Processing workflow…" })).toBeDisabled();
  await expect(panel.getByRole("status")).toContainText("saved server progress");
  release();
  await expect(panel.getByRole("heading", { name: "Awaiting human review" })).toBeVisible({ timeout: 20000 });
  await expect(panel.locator(".workflow-stages li[data-state=complete]")).toHaveCount(6);
  await expect(panel.locator(".workflow-stages li").last()).toContainText("Awaiting review");
  await expect(panel.locator(".draft-text")).toContainText("refund within thirty days");
  await expect(panel.getByRole("button", { name: "Resume reviewed workflow" })).toBeDisabled();
  const run = (await (await page.request.get("/api/v1" + base + "/workflows")).json()).items[0];
  await panel.screenshot({ path: "../../.cache/verification/workflow-desktop.png" });
  await page.emulateMedia({ colorScheme: "dark" });
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
  }
  await panel.screenshot({ path: "../../.cache/verification/workflow-mobile-dark.png" });
  // Review through the existing API, then reload as a new browser request before resuming.
  expect((await write(page.request, base + `/drafts/${run.draft.id}/review`, {
    expected_version: run.draft.version, action: "approved",
  })).status()).toBe(200);
  await page.reload();
  await panel.getByRole("button", { name: "Resume reviewed workflow" }).click();
  await expect(panel.getByRole("heading", { name: "Completed", exact: true })).toBeVisible({ timeout: 20000 });
  await expect(panel.locator(".workflow-stages li[data-state=complete]")).toHaveCount(7);
  await expect(panel.getByText("Approved internally. No customer action was taken.", { exact: false })).toBeVisible({ timeout: 20000 });
  const result = await page.request.get(`/api/v1/workspaces/${space.id}/workflows/${run.id}`);
  expect((await result.json()).draft.id).toBe(run.draft.id);
  expect((await (await page.request.get("/api/v1" + base + "/drafts")).json()).total).toBe(1);
});

test("workflow review buttons reject, request revision and approve", async ({ page }) => {
  const { panel } = await setup(page);
  for (const [button, status] of [["Reject draft", "Rejected"], ["Request revision", "Revision requested"], ["Approve exact draft", "Completed"]]) {
    await panel.getByRole("button", { name: "Start AI workflow" }).click();
    await panel.getByRole("button", { name: button, exact: true }).click();
    await expect(panel.getByRole("heading", { name: status, exact: true })).toBeVisible({ timeout: 20000 });
  }
});

test("workflow empty evidence, stop and transport error states", async ({ page }) => {
  const { panel } = await setup(page, false);
  await panel.getByRole("button", { name: "Start AI workflow" }).click();
  await expect(panel.getByText("Insufficient evidence · human verification required.", { exact: false })).toBeVisible({ timeout: 20000 });
  await expect(panel.getByRole("button", { name: "Approve exact draft" })).toBeDisabled();
  await panel.getByRole("button", { name: "Stop workflow" }).click();
  await expect(panel.getByRole("heading", { name: "Stopped", exact: true })).toBeVisible({ timeout: 20000 });
  await page.route("**/tickets/*/workflows", route => route.request().method() === "POST"
    ? route.fulfill({ status: 429, contentType: "application/json", body: JSON.stringify({ error: { code: "rate_limited", message: "Synthetic UI failure" } }) })
    : route.continue());
  await panel.getByRole("button", { name: "Start AI workflow" }).click();
  await expect(panel.getByRole("alert")).toContainText("limit has been reached");
});

test("unsafe ticket fails at the actual workflow stage without generation", async ({ page }) => {
  const { panel, base } = await setup(page);
  expect((await write(page.request, base, { expected_version: 1, description: "Contact synthetic@example.com about this policy." }, "PATCH")).status()).toBe(200);
  await page.reload();
  await panel.getByRole("button", { name: "Start AI workflow" }).click();
  await expect(panel.getByRole("heading", { name: "Failed", exact: true })).toBeVisible({ timeout: 20000 });
  await expect(panel.locator(".workflow-stages li[data-state=failed]")).toContainText("Retrieval");
  await expect(panel.locator(".draft-result")).toHaveCount(0);
  const run = (await (await page.request.get("/api/v1" + base + "/workflows")).json()).items[0];
  expect(run.status).toBe("failed");
  expect(run.draft).toBeNull();
});

test("accepted jobs show queued state and polling stops at human review", async ({ page }) => {
  const { panel } = await setup(page);
  let submitted = false;
  let release!: () => void;
  const hold = new Promise<void>(resolve => { release = resolve; });
  let reads = 0;
  await page.route("**/tickets/*/workflows?*", async route => {
    reads += 1;
    if (submitted) await hold;
    await route.continue();
  });
  const accepted = page.waitForResponse(response => response.url().endsWith("/workflows") && response.request().method() === "POST");
  submitted = true;
  await panel.getByRole("button", { name: "Start AI workflow" }).click();
  const response = await accepted;
  expect(response.status()).toBe(202);
  expect((await response.json()).job.status).toBe("queued");
  await expect(panel.getByRole("heading", { name: "Queued", exact: true })).toBeVisible();
  release();
  await expect(panel.getByRole("heading", { name: "Awaiting human review" })).toBeVisible({ timeout: 20000 });
  await page.waitForTimeout(2500); // Allow the transition's final history refresh to settle.
  const stopped = reads;
  await page.waitForTimeout(4500);
  expect(reads).toBe(stopped);
});
