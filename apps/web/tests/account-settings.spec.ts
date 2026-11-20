import { test, expect, type APIRequestContext } from "@playwright/test";
import { randomUUID } from "node:crypto";

const inbox = process.env.RESOLVEFLOW_TEST_INBOX_URL;
const settings = "/app/settings/account";
const password = "browser profile passphrase 123!";
const replacement = "browser profile replacement 456!";
if (process.env.RESOLVEFLOW_E2E_ISOLATED !== "1" || !inbox?.startsWith("http://127.0.0.1:")) {
  throw new Error("Profile settings tests require an isolated local inbox");
}

async function mail(request: APIRequestContext, address: string, subject: string) {
  let body = "";
  await expect.poll(async () => {
    const listing = await (await request.get(`${inbox}/api/v1/messages`)).json();
    for (const entry of listing.messages) {
      if (entry.Subject !== subject || !entry.To.some((recipient: { Address: string }) => recipient.Address === address)) continue;
      const message = await (await request.get(`${inbox}/api/v1/message/${entry.ID}`)).json();
      body = message.Text;
      return true;
    }
    return false;
  }, { timeout: 20000, message: "Expected local account email was delivered" }).toBe(true);
  return body;
}

test("profile and picture persist, email proof and password change revoke sessions", async ({ page, browser, request }) => {
  test.setTimeout(80000);
  const email = `profile-${randomUUID()}@example.com`;
  const next = `next-${randomUUID()}@example.com`;
  await page.setViewportSize({ width: 350, height: 750 });
  await page.goto(settings);
  await expect(page).toHaveURL(/\/login\?next=/);
  expect((await page.request.get("/api/v1/account/profile")).status()).toBe(401);
  await page.goto("/register");
  await page.getByLabel("Email address", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel("Confirm password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page).toHaveURL(/\/app$/);
  await page.getByRole("link", { name: "Personal settings" }).click();
  await expect(page.getByRole("heading", { name: "Personal settings" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(350);
  await expect(page.getByRole("form", { name: "Email address" })).toHaveAttribute("method", "post");
  await expect(page.getByRole("form", { name: "Password" })).toHaveAttribute("method", "post");
  await page.getByLabel("Display name").pressSequentially("Ada Profile");
  const avatar = await page.evaluate(() => {
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 64;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Canvas unavailable");
    ctx.fillStyle = "teal";
    ctx.fillRect(0, 0, 64, 64);
    return canvas.toDataURL("image/png").split(",")[1];
  });
  await page.getByLabel("Profile picture").setInputFiles({
    name: "avatar.png", mimeType: "image/png", buffer: Buffer.from(avatar, "base64"),
  });
  await page.getByRole("button", { name: "Save profile" }).click();
  await expect(page.getByText("Profile saved.")).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Display name")).toHaveValue("Ada Profile");
  await expect(page.getByRole("img", { name: "Your profile picture" })).toBeVisible();
  await expect.poll(() => page.getByRole("img", { name: "Your profile picture" }).evaluate((img: HTMLImageElement) => img.naturalWidth)).toBe(56);

  const second = await browser.newPage();
  try {
    await second.goto("/login");
    await second.getByLabel("Email address").fill(email);
    await second.getByLabel("Password", { exact: true }).fill(password);
    await second.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(second).toHaveURL(/\/app$/);
    await page.getByLabel("New email address").fill(next);
    await page.getByLabel("Current password for email change", { exact: true }).fill("wrong");
    await page.getByRole("button", { name: "Request email change" }).click();
    await expect(page.getByRole("form", { name: "Email address" }).getByRole("alert")).toContainText("Enter your current password");
    await page.getByLabel("Current password for email change", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Request email change" }).click();
    await expect(page.getByText("Check your new inbox", { exact: false })).toBeVisible();
    const message = await mail(request, next, "Verify your new ResolveFlow email");
    const link = message.match(/http:\/\/127\.0\.0\.1:3100\/app\/settings\/account\/confirm-email#token=[A-Za-z0-9_-]{43}/)?.[0];
    if (!link) throw new Error("Missing verification link");
    await second.goto(link);
    await second.getByRole("button", { name: "Verify new email" }).click();
    await expect(second.getByText("This link cannot be used.", { exact: false })).toBeVisible();
    await page.goto(link);
    await expect.poll(() => page.evaluate(() => location.hash)).toBe("");
    await page.getByRole("button", { name: "Verify new email" }).click();
    await expect(page.getByText("Email updated. All sessions have been signed out.")).toBeVisible();
    expect((await second.request.get("/api/v1/account/profile")).status()).toBe(401);
    expect(await mail(request, email, "Your ResolveFlow email changed")).toContain("all sessions were signed out");
    await page.getByRole("link", { name: "Sign in again" }).click();
    await page.getByLabel("Email address").fill(next);
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page).toHaveURL(/\/app$/);
    await page.goto(settings);
    await page.getByLabel("Current password", { exact: true }).fill(password);
    await page.getByLabel("New password", { exact: true }).fill(replacement);
    await page.getByLabel("Confirm new password", { exact: true }).fill(replacement);
    await page.getByRole("button", { name: "Change password" }).click();
    await expect(page).toHaveURL(/\/login$/);
    expect((await page.request.get("/api/v1/account/profile")).status()).toBe(401);
    await page.getByLabel("Email address").fill(next);
    await page.getByLabel("Password", { exact: true }).fill(replacement);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page).toHaveURL(/\/app$/);
  } finally {
    await second.close();
  }
});

test("Google-only settings show Google without a password editor", async ({ page, request }) => {
  test.skip(process.env.RESOLVEFLOW_TEST_GOOGLE !== "1", "Requires the isolated Google provider");
  await page.route("https://accounts.google.com/o/oauth2/v2/auth?**", async route => {
    const granted = await request.get("http://127.0.0.1:8100/_fixture/google/authorize" + new URL(route.request().url()).search);
    expect(granted.status()).toBe(200);
    const callback = new URL("http://127.0.0.1:3100/auth/google/callback");
    callback.search = new URLSearchParams(await granted.json()).toString();
    await route.fulfill({ status: 302, headers: { Location: callback.href }, body: "" });
  });
  await page.goto("/login?next=%2Fapp%2Fsettings%2Faccount");
  await page.getByRole("button", { name: "Continue with Google" }).click();
  await expect(page).toHaveURL(new RegExp(settings + "$"));
  await expect(page.getByRole("listitem").filter({ hasText: /^Google$/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Change password" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Verify your current email before changing it" })).toBeVisible();
});
