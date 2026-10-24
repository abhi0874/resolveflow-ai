import { test, expect, type APIRequestContext } from "@playwright/test";
import { randomUUID } from "node:crypto";

const password = "browser identity passphrase 123!";
const replacement = "replacement identity passphrase 456!";
const inbox = process.env.RESOLVEFLOW_TEST_INBOX_URL;
if (process.env.RESOLVEFLOW_E2E_ISOLATED !== "1" || !inbox?.startsWith("http://127.0.0.1:"))
  throw new Error("Identity browser tests require the isolated local inbox harness");

async function mailLink(request: APIRequestContext, email: string, page: string) {
  let link = "";
  await expect.poll(async () => {
    const listing = await (await request.get(`${inbox}/api/v1/messages`)).json();
    for (const entry of listing.messages) {
      if (!entry.To.some((recipient: { Address: string }) => recipient.Address === email)) continue;
      const message = await (await request.get(`${inbox}/api/v1/message/${entry.ID}`)).json();
      const match = message.Text.match(new RegExp(`http://127\\.0\\.0\\.1:3100/${page}#token=[A-Za-z0-9_-]{43}`));
      if (match) { link = match[0]; return true; }
    }
    return false;
  }, { timeout: 20000, message: "Expected local SMTP message was delivered" }).toBe(true);
  return link;
}

test("real SMTP verification and password recovery with session invalidation", async ({ page, request }) => {
  test.setTimeout(60000);
  const email = `identity-${randomUUID()}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel("Confirm password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page).toHaveURL(/\/app$/);
  const verification = await mailLink(request, email, "verify-email");
  await page.goto(verification);
  await expect.poll(() => page.evaluate(() => location.hash)).toBe("");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Verify email", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Email verified. Sign in to continue.");
  await page.goto("/app");
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/app$/);
  await page.goto("/forgot-password");
  await page.getByLabel("Email address").fill(email);
  await page.getByRole("button", { name: "Send recovery email" }).click();
  await expect(page.getByRole("status")).toContainText("If the account is eligible");
  const reset = await mailLink(request, email, "reset-password");
  await page.goto(reset);
  await expect.poll(() => page.evaluate(() => location.hash)).toBe("");
  await page.getByLabel("New password", { exact: true }).fill(replacement);
  await page.getByLabel("Confirm password", { exact: true }).fill(replacement);
  await page.getByRole("button", { name: "Reset password", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Your previous sessions have been signed out");
  await page.goto("/login");
  await page.goto(reset);
  await page.getByLabel("New password", { exact: true }).fill(replacement);
  await page.getByLabel("Confirm password", { exact: true }).fill(replacement);
  await page.getByRole("button", { name: "Reset password", exact: true }).click();
  await expect(page.locator("form").getByRole("alert")).toContainText("invalid, expired or already used");
  await page.goto("/login");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(replacement);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/app$/);
});

test("identity forms handle loading, service failure and generic requests", async ({ page }) => {
  await page.goto("/forgot-password");
  await page.getByLabel("Email address").fill("unknown-identity@example.com");
  let release: () => void = () => {};
  const held = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/api/v1/auth/password/request", async route => { await held; await route.fulfill({ status: 503, contentType: "application/json", body: "{}" }); });
  await page.getByRole("button", { name: "Send recovery email" }).click();
  await expect(page.getByRole("button", { name: "Please wait…" })).toBeDisabled();
  release();
  await expect(page.locator("form").getByRole("alert")).toContainText("couldn’t reach the service");
  await page.unroute("**/api/v1/auth/password/request");
  await page.getByRole("button", { name: "Send recovery email" }).click();
  await expect(page.getByRole("status")).toContainText("If the account is eligible");
  await page.goto("/verification-required");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByLabel("Email address").fill("unknown-identity@example.com");
  await page.getByLabel("Email address").press("Tab");
  await expect(page.getByRole("button", { name: "Resend verification email" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("status")).toContainText("If the account is eligible");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test("invalid verification link and production registration notice", async ({ page }) => {
  await page.goto("/verify-email#token=invalid");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Verify email", exact: true }).click();
  await expect(page.locator("form").getByRole("alert")).toContainText("invalid, expired or already used");
  await page.route("**/api/v1/auth/register", route => route.fulfill({ status: 202, contentType: "application/json", body: JSON.stringify({ status: "accepted" }) }));
  await page.goto("/register");
  await page.getByLabel("Email address").fill("notice@example.com");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel("Confirm password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page).toHaveURL(/\/verification-required$/);
  await expect(page.getByRole("heading", { name: "Check your email" })).toBeVisible();
});
