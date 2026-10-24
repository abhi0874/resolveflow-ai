import { invitationCode } from "./invitation-helper";
import { test, expect, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";
const password = "browser test passphrase 123!";

async function register(page: Page) {
  const email = `browser-${randomUUID()}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel("Confirm password", { exact: true }).fill(password);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(page).toHaveURL(/\/app$/);
  return email;
}

test("protected rendering, validation, and real login error", async ({
  page,
  request,
}) => {
  const result = await request.get("/app", { maxRedirects: 0 });
  expect(result.status()).toBe(307);
  expect(result.headers().location).toBe("/login");
  expect(await result.text()).not.toContain("SIGNED IN AS");
  await page.goto("/app");
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel("Email address").fill("missing@example.com");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page
    .getByRole("button", { name: "Show password", exact: true })
    .click();
  await expect(page.getByLabel("Password", { exact: true })).toHaveAttribute(
    "type",
    "text",
  );
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator("form").getByRole("alert")).toHaveText(
    "Email or password is incorrect.",
  );
  await page.goto("/register");
  await page.getByLabel("Email address").fill("invalid");
  expect(
    await page
      .getByLabel("Email address")
      .evaluate((input: HTMLInputElement) => input.validity.typeMismatch),
  ).toBe(true);
  await page.getByLabel("Email address").fill("valid@example.com");
  await page.getByLabel("Password", { exact: true }).fill("short");
  await page.getByLabel("Confirm password", { exact: true }).fill(password);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(page).toHaveURL(/\/register$/);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page
    .getByLabel("Confirm password", { exact: true })
    .fill(password + "different");
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(page.locator("form").getByRole("alert")).toHaveText(
    "Passwords don’t match.",
  );
});

test("registration, workspace navigation, settings, session persistence and logout", async ({
  page,
  context,
}) => {
  const email = await register(page);
  const cookie = (await context.cookies()).find(
    (cookie) => cookie.name === "resolveflow_session",
  )!;
  expect(cookie.httpOnly).toBe(true);
  expect(cookie.sameSite).toBe("Lax");
  expect(await page.evaluate(() => document.cookie)).not.toContain(
    cookie.value,
  );
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([]);
  await page.getByLabel("Workspace name").fill("Customer Care");
  await page.getByLabel("Workspace slug").fill(`care-${randomUUID()}`);
  await page
    .getByRole("button", { name: "Create workspace", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Customer Care", exact: true }),
  ).toBeVisible();
  const firstUrl = page.url();
  await page.reload();
  await expect(page.getByText(email, { exact: true }).first()).toBeVisible();
  await page.getByLabel("Workspace name").fill("Care Team");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("status")).toHaveText(
    "Workspace settings saved.",
  );
  await expect(
    page.getByRole("heading", { name: "Care Team", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "＋ Create workspace" }).click();
  await page.getByLabel("Workspace name").fill("Operations");
  await page.getByLabel("Workspace slug").fill(`ops-${randomUUID()}`);
  await page
    .getByRole("button", { name: "Create workspace", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Operations", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("navigation", { name: "Workspaces" })
    .getByRole("link", { name: /Care Team/ })
    .click();
  await expect(page).toHaveURL(firstUrl);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../../.cache/verification/workspace-mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
  const replay = await page.request.get("/api/v1/auth/me", {
    headers: { cookie: `resolveflow_session=${cookie.value}` },
  });
  expect(replay.status()).toBe(401);
  await page.goto("/app");
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/app$/);
  await expect(
    page.getByRole("navigation", { name: "Workspaces" }).getByRole("link"),
  ).toHaveCount(2);
  await context.clearCookies();
  await page.reload();
  await expect(page).toHaveURL(/\/login$/);
});

test("real membership UI and viewer protection", async ({ page, browser }) => {
  const memberContext = await browser.newContext();
  const memberPage = await memberContext.newPage();
  const memberEmail = await register(memberPage);
  await register(page);
  await page.getByLabel("Workspace name").fill("Shared team");
  await page.getByLabel("Workspace slug").fill(`shared-${randomUUID()}`);
  await page
    .getByRole("button", { name: "Create workspace", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Shared team" }),
  ).toBeVisible();
  const workspaceUrl = page.url();
  await page.getByLabel("Invite a registered teammate").fill(memberEmail);
  await page.getByRole("button", { name: "Send invitation", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Invitation created. Access begins only after the recipient accepts.");
  const workspaceId = new URL(workspaceUrl).searchParams.get("workspace")!;
  const invitations = await page.request.get(`/api/v1/workspaces/${workspaceId}/invitations`);
  expect(invitations.status()).toBe(200);
  const invitation = (await invitations.json())[0];
  expect((await memberPage.request.get(`/api/v1/workspaces/${workspaceId}`)).status()).toBe(404);
  await memberPage.getByLabel("Invitation code").fill(await invitationCode(workspaceId, invitation.id));
  await memberPage.getByRole("button", { name: "Accept invitation", exact: true }).click();
  await expect(memberPage).toHaveURL(workspaceUrl);
  expect((await memberPage.request.get("/api/v1/auth/me")).status()).toBe(200);
  await page.reload();
  await memberPage.goto(workspaceUrl);
  await expect(
    memberPage.getByRole("heading", { name: "Shared team" }),
  ).toBeVisible();
  await expect(
    memberPage.getByRole("button", { name: "Save changes" }),
  ).toHaveCount(0);
  await expect(
    memberPage.getByRole("button", { name: "Send invitation", exact: true }),
  ).toHaveCount(0);
  await page
    .getByLabel(`Role for ${memberEmail}`)
    .selectOption("support_agent");
  await expect(page.getByRole("status")).toHaveText("Member role updated.");
  page.once("dialog", (dialog) => dialog.accept());
  await page
    .getByRole("button", { name: `Remove ${memberEmail}`, exact: true })
    .click();
  await expect(page.getByRole("status")).toHaveText("Member removed.");
  await memberPage.reload();
  await expect(
    memberPage.getByRole("heading", { name: "Shared team" }),
  ).toHaveCount(0);
  await memberContext.close();
});

test("responsive auth page and unavailable service", async ({ page }) => {
  await page.goto("/login");
  await page.screenshot({
    path: "../../.cache/verification/login-desktop.png",
    fullPage: true,
  });
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
  await page.screenshot({
    path: "../../.cache/verification/login-mobile.png",
    fullPage: true,
  });
  await page.route("**/api/v1/auth/csrf", (route) => route.abort());
  await page.getByLabel("Email address").fill("x@example.com");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator("form").getByRole("alert")).toContainText(
    "couldn’t reach the service",
  );
});
