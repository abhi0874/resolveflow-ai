import { test, expect, type Page, type APIRequestContext } from "@playwright/test";
import { randomUUID } from "node:crypto";

async function write(request: APIRequestContext, path: string, data: unknown, method = "POST") {
  const csrf = await request.get("/api/v1/auth/csrf");
  return request.fetch("/api/v1" + path, {
    method, data,
    headers: { Origin: "http://127.0.0.1:3100", "X-CSRF-Token": (await csrf.json()).csrf_token },
  });
}
async function register(page: Page) {
  const result = await write(page.request, "/auth/register", {
    email: `ml-${randomUUID()}@example.com`, password: "classification test passphrase 42!",
    password_confirmation: "classification test passphrase 42!",
  });
  expect(result.status()).toBe(201);
  return result.json();
}
async function setup(page: Page, unknown = false) {
  await register(page);
  const response = await write(page.request, "/workspaces", { name: "Classification team", slug: `ml-${randomUUID()}` });
  expect(response.status()).toBe(201);
  const workspace = await response.json();
  const base = `/workspaces/${workspace.id}/tickets`;
  const created = await write(page.request, base, {
    title: unknown ? "zzzzzzz qqqqqqq xxxxzzzz" : "Duplicate debit",
    description: unknown ? "" : "My card shows two payments for one purchase. Please return the extra amount.",
    category: "Unreviewed",
  });
  expect(created.status()).toBe(201);
  const ticket = await created.json();
  const detail = `${base}/${ticket.id}`;
  const url = `/app/tickets/${ticket.id}?workspace=${workspace.id}`;
  await page.goto(url);
  await expect(page.getByRole("button", { name: "Classify with ML" })).toBeVisible();
  return { workspace, ticket, detail, url };
}

test("real ML loading, prediction, dismissal and authorized acceptance with history", async ({ page }) => {
  const { detail, ticket } = await setup(page);
  const panel = page.getByRole("region", { name: "ML classification" });
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  await page.route("**/classify", async (route) => { await gate; await route.continue(); });
  const classified = page.waitForResponse((r) => r.url().endsWith("/classify") && r.ok());
  await panel.getByRole("button", { name: "Classify with ML" }).click();
  await expect(panel.getByRole("status")).toHaveText("Classifying this ticket…");
  await expect(panel.getByRole("button", { name: "Classifying…" })).toBeDisabled();
  release();
  const prediction = await (await classified).json();
  await page.unroute("**/classify");
  await expect(panel.getByRole("heading", { name: prediction.suggested_category, exact: true })).toBeVisible();
  await expect(panel).toContainText(`${(prediction.score * 100).toFixed(1)}%`);
  await expect(panel).toContainText("browser-v1");
  await expect(panel).toContainText("Uncalibrated model probability");
  await expect((await page.request.get("/api/v1" + detail)).json()).resolves.toMatchObject({ category: "Unreviewed", version: 1 });
  await panel.getByRole("button", { name: "Dismiss suggestion" }).click();
  await expect(panel.getByRole("status")).toContainText("category unchanged");
  expect((await (await page.request.get("/api/v1" + detail)).json()).category).toBe("Unreviewed");
  await panel.getByRole("button", { name: "Classify with ML" }).click();
  await expect(panel.getByRole("button", { name: "Accept suggestion" })).toBeVisible();
  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    await panel.screenshot({ path: `../../.cache/verification/classification-${colorScheme}.png` });
  }
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  await panel.screenshot({ path: "../../.cache/verification/classification-mobile.png" });
  await panel.getByRole("button", { name: "Accept suggestion" }).click();
  await expect(page.getByText("Suggested category applied. Ticket activity updated.")).toBeVisible();
  await expect(page.getByRole("list", { name: "activity", exact: true })).toContainText("Updated category");
  const saved = await (await page.request.get("/api/v1" + detail)).json();
  expect(saved.category).toBe(prediction.suggested_category);
  expect(saved.version).toBe(ticket.version + 1);
  await page.reload();
  await expect(page.locator(".ticket-properties")).toContainText(prediction.suggested_category);
});

test("ML uncertainty, unavailable errors, stale acceptance and expired session", async ({ page, context }) => {
  const { detail } = await setup(page, true);
  const panel = page.getByRole("region", { name: "ML classification" });
  await panel.getByRole("button", { name: "Classify with ML" }).click();
  await expect(panel.getByRole("heading", { name: "No reliable suggestion" })).toBeVisible();
  await expect(panel.getByRole("button", { name: "Accept suggestion" })).toHaveCount(0);
  await expect(panel).toContainText("manual review needed");
  await page.route("**/classify", (route) => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ error: { message: "Unavailable" } }) }));
  await panel.getByRole("button", { name: "Classify with ML" }).click();
  await expect(panel.getByRole("alert")).toContainText("classifier is unavailable");
  await page.unroute("**/classify");
  expect((await write(page.request, detail, { expected_version: 1, title: "Duplicate debit", description: "My card shows two payments for one purchase. Please return the extra amount." }, "PATCH")).status()).toBe(200);
  await page.reload();
  await panel.getByRole("button", { name: "Classify with ML" }).click();
  await expect(panel.getByRole("button", { name: "Accept suggestion" })).toBeVisible();
  expect((await write(page.request, detail, { expected_version: 2, title: "A changed request" }, "PATCH")).status()).toBe(200);
  await panel.getByRole("button", { name: "Accept suggestion" }).click();
  await expect(panel.getByRole("alert")).toContainText("changed");
  expect((await (await page.request.get("/api/v1" + detail)).json()).category).toBe("Unreviewed");
  await context.clearCookies();
  await panel.getByRole("button", { name: "Classify with ML" }).click();
  await expect(page).toHaveURL(/\/login\?expired=1$/);
});

test("ML viewer and assigned-agent controls match backend authorization", async ({ page, browser }) => {
  const { workspace, detail, url } = await setup(page);
  const context = await browser.newContext();
  try {
    const other = await context.newPage();
    const user = await register(other);
    const members = `/workspaces/${workspace.id}/members`;
    expect((await write(page.request, members, { email: user.email, role: "viewer" })).status()).toBe(201);
    await other.goto(url);
    await expect(other.getByRole("heading", { name: "Duplicate debit", exact: true })).toBeVisible();
    await expect(other.getByRole("button", { name: "Classify with ML" })).toHaveCount(0);
    expect((await write(other.request, detail + "/classify", {})).status()).toBe(403);
    expect((await write(page.request, members + "/" + user.id, { role: "support_agent" }, "PATCH")).status()).toBe(200);
    await other.reload();
    await expect(other.getByRole("button", { name: "Classify with ML" })).toBeVisible();
    await other.getByRole("button", { name: "Classify with ML" }).click();
    await other.getByRole("button", { name: "Accept suggestion" }).click();
    await expect(other.getByText("Suggested category applied. Ticket activity updated.")).toBeVisible();
  } finally { await context.close(); }
});
