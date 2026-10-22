import { test, expect, type APIRequestContext, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";

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
  const panel = page.getByRole("region", { name: "Response assistant", exact: true });
  await expect(panel.getByText("No drafts yet.", { exact: false })).toBeVisible();
  return { panel, base, space, ticket, documentId };
}

test("generate from real retrieval, review exact draft, preserve history and invalidate stale approval", async ({ page }) => {
  const { panel, base, space, documentId } = await setup(page);
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/generate-response", async route => { await gate; await route.continue(); });
  await panel.getByRole("button", { name: "Generate response draft" }).click();
  await expect(panel.getByRole("button", { name: "Working…" })).toBeDisabled();
  await expect(panel.getByText("Processing your draft request…")).toBeVisible();
  release();
  await expect(panel.locator(".draft-text")).toHaveText("Customers can request a refund within thirty days of their first purchase.");
  await expect(panel.getByText("Deterministic test fixture · not Gemini inference")).toBeVisible();
  await expect(panel.getByRole("link", { name: "refund-guide.txt · Chunk 1" })).toBeVisible();
  await page.unroute("**/generate-response");
  await panel.scrollIntoViewIfNeeded();
  await page.screenshot({ path: "../../.cache/verification/rag-light.png", fullPage: true });
  await page.emulateMedia({ colorScheme: "dark" });
  await page.setViewportSize({ width: 390, height: 844 });
  await panel.locator(".draft-result").scrollIntoViewIfNeeded();
  await page.screenshot({ path: "../../.cache/verification/rag-mobile-dark.png" });
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
  }
  await panel.getByRole("button", { name: "Approve exact draft" }).click();
  await expect(panel.getByText("Approved internally. No customer action was taken.", { exact: false })).toBeVisible();
  const approved = (await (await page.request.get("/api/v1" + base + "/drafts")).json()).items[0];
  await page.reload();
  await expect(panel.getByText("Approved internally. No customer action was taken.", { exact: false })).toBeVisible();
  await panel.getByRole("button", { name: "Generate response draft" }).click();
  await expect(panel.getByRole("button", { name: "Reject draft" })).toBeEnabled();
  await panel.getByRole("button", { name: "Reject draft" }).click();
  await expect(panel.locator(".draft-result .role-badge").first()).toHaveText("Rejected");
  await panel.getByRole("button", { name: "Generate response draft" }).click();
  await expect(panel.getByRole("button", { name: "Request revision" })).toBeEnabled();
  await panel.getByRole("button", { name: "Request revision" }).click();
  await expect(panel.locator(".draft-result .role-badge").first()).toHaveText("Revision requested");
  await panel.getByLabel("Draft history").selectOption(approved.id);
  expect((await write(page.request, `/workspaces/${space.id}/documents/${documentId}`, {}, "DELETE")).status()).toBe(204);
  await panel.getByRole("button", { name: "Refresh drafts" }).click();
  await expect(panel.getByText("This draft is stale:", { exact: false })).toBeVisible();
  await expect(panel.getByRole("link", { name: "refund-guide.txt · Chunk 1" })).toHaveCount(0);
});

test("empty evidence abstains, provider failure is visible, and retry is deliberate", async ({ page }) => {
  const { panel } = await setup(page, false);
  await panel.getByRole("button", { name: "Generate response draft" }).click();
  await expect(panel.getByText("Insufficient evidence · human verification required.", { exact: false })).toBeVisible();
  await expect(panel.getByRole("button", { name: "Approve exact draft" })).toBeDisabled();
  await page.route("**/generate-response", route => route.fulfill({
    status: 429, contentType: "application/json",
    body: JSON.stringify({ error: { code: "ai_quota_exhausted", message: "Synthetic UI failure test" } }),
  }));
  await panel.getByRole("button", { name: "Generate response draft" }).click();
  await expect(panel.getByRole("alert")).toContainText("quota is exhausted");
  await page.unroute("**/generate-response");
  await panel.getByRole("button", { name: "Generate response draft" }).click();
  await expect(panel.getByRole("alert")).toHaveCount(0);
});

test("viewer cannot read document-derived drafts or review them", async ({ page, browser }) => {
  const { panel, base, space, ticket } = await setup(page);
  await panel.getByRole("button", { name: "Generate response draft" }).click();
  await expect(panel.getByRole("button", { name: "Approve exact draft" })).toBeEnabled();
  const other = await browser.newContext({ baseURL: "http://127.0.0.1:3100" });
  try {
    const viewer = await other.newPage();
    const user = await account(viewer);
    expect((await write(page.request, `/workspaces/${space.id}/members`, { email: user.email, role: "viewer" })).status()).toBe(201);
    await viewer.goto(`/app/tickets/${ticket.id}?workspace=${space.id}`);
    await expect(viewer.getByRole("heading", { name: ticket.title, exact: true })).toBeVisible();
    await expect(viewer.getByRole("region", { name: "Response assistant" })).toHaveCount(0);
    await expect(viewer.getByRole("region", { name: "AI workflow" })).toHaveCount(0);
    expect((await viewer.request.get("/api/v1" + base + "/workflows")).status()).toBe(403);
    expect((await viewer.request.get("/api/v1" + base + "/drafts")).status()).toBe(403);
    expect((await write(viewer.request, base + "/generate-response", { request_id: randomUUID(), expected_ticket_version: 1 })).status()).toBe(403);
  } finally { await other.close(); }
});
