import { inviteMember } from "./invitation-helper";
import { test, expect, type APIRequestContext } from "@playwright/test";
import { randomUUID } from "node:crypto";
async function write(request: APIRequestContext, path: string, data: unknown) {
  const csrf = await request.get("/api/v1/auth/csrf");
  return request.post("/api/v1" + path, { data, headers: { Origin: "http://127.0.0.1:3100", "X-CSRF-Token": (await csrf.json()).csrf_token } });
}
async function setup(request: APIRequestContext) {
  expect((await write(request, "/auth/register", { email: `analytics-${randomUUID()}@example.com`, password: "analytics test passphrase 42!", password_confirmation: "analytics test passphrase 42!" })).status()).toBe(201);
  const response = await write(request, "/workspaces", { name: "Analytics test workspace", slug: `analytics-${randomUUID()}` });
  expect(response.status()).toBe(201); return response.json();
}

test("analytics real counts, charts, UTC filters and responsive navigation", async ({ page }) => {
  const space = await setup(page.request);
  for (const priority of ["high", "medium"]) expect((await write(page.request, `/workspaces/${space.id}/tickets`, { title: "Synthetic analytics case", priority, category: "Billing" })).status()).toBe(201);
  await page.goto(`/app?workspace=${space.id}`);
  await page.getByRole("link", { name: "Workspace analytics" }).click();
  await expect(page.getByRole("heading", { name: "Analytics", exact: true })).toBeVisible();
  await expect(page.getByRole("article", { name: "Tickets created" }).locator("strong")).toHaveText("2");
  const status = page.getByRole("region", { name: "Ticket status", exact: true });
  await expect(status.getByText("open", { exact: true })).toBeVisible();
  const trend = page.getByRole("region", { name: "Ticket creation trend", exact: true });
  await expect(trend.locator(".recharts-surface")).toBeVisible();
  await trend.getByText("View ticket creation trend data").click();
  await expect(trend.getByRole("table")).toBeVisible();
  await expect(page.getByRole("article", { name: "Median resolution time" }).locator("strong")).toHaveText("Unavailable");
  await page.screenshot({ path: "../../.cache/verification/analytics-desktop.png", fullPage: true });
  await page.emulateMedia({ colorScheme: "dark" });
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
  }
  await page.screenshot({ path: "../../.cache/verification/analytics-mobile-dark.png", fullPage: true });
  await page.getByLabel("From (UTC)").fill("2020-01-01");
  await page.getByLabel("Through (UTC)").fill("2020-01-02");
  await page.getByRole("button", { name: "Apply range" }).click();
  await expect(page.getByRole("heading", { name: "No activity in this range" })).toBeVisible();
  await expect(page.getByRole("article", { name: "Tickets created" }).locator("strong")).toHaveText("0");
});

test("analytics loading, unavailable response and retry", async ({ page }) => {
  const space = await setup(page.request);
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/analytics/overview?*", async route => { await gate; await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ error: { code: "database_unavailable" } }) }); });
  await page.goto(`/app/analytics?workspace=${space.id}`);
  await expect(page.getByRole("status", { name: "Loading analytics" })).toBeVisible();
  release();
  await expect(page.getByRole("alert")).toBeVisible();
  await page.unroute("**/analytics/overview?*");
  await page.getByRole("button", { name: "Retry analytics" }).click();
  await expect(page.getByRole("heading", { name: "No activity in this range" })).toBeVisible();
  const forbidden = await page.request.get(`/api/v1/workspaces/${randomUUID()}/analytics/overview`);
  expect(forbidden.status()).toBe(404);
  expect((await page.request.get(`/api/v1/workspaces/${space.id}/analytics/overview?start=2020-01-01&start=2020-01-02`)).status()).toBe(404);
});

test("viewer analytics permissions are enforced in navigation and API", async ({ page, browser }) => {
  const space = await setup(page.request);
  const context = await browser.newContext({ baseURL: "http://127.0.0.1:3100" });
  try {
    const email = `analytics-viewer-${randomUUID()}@example.com`;
    expect((await write(context.request, "/auth/register", { email, password: "analytics viewer passphrase!", password_confirmation: "analytics viewer passphrase!" })).status()).toBe(201);
    expect((await inviteMember(page.request, context.request, `/workspaces/${space.id}/members`, { email, role: "viewer" })).status()).toBe(201);
    const viewer = await context.newPage();
    await viewer.goto(`/app/analytics?workspace=${space.id}`);
    await expect(viewer.getByRole("heading", { name: "Analytics access restricted" })).toBeVisible();
    await expect(viewer.getByRole("navigation", { name: "Workspace tools" }).getByRole("link", { name: "Analytics" })).toHaveCount(0);
    expect((await context.request.get(`/api/v1/workspaces/${space.id}/analytics/overview`)).status()).toBe(403);
  } finally { await context.close(); }
});
