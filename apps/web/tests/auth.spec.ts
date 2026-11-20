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

test("signed-out HTML and RSC requests cannot reach private routes", async ({ page, request }) => {
  const id = randomUUID();
  const routes = [
    "/app",
    `/app?workspace=${id}`,
    `/app/tickets?workspace=${id}`,
    `/app/tickets/${id}?workspace=${id}`,
    `/app/knowledge-base?workspace=${id}`,
    `/app/knowledge-base/${id}?workspace=${id}`,
    `/app/analytics?workspace=${id}`,
    "/app/settings",
    "/app/workflows",
  ];
  for (const path of routes) {
    for (const headers of [undefined, { RSC: "1", "Next-Router-Prefetch": "1" }]) {
      const response = await request.get(path, { maxRedirects: 0, headers });
      expect(response.status(), path).toBe(307);
      const location = new URL(response.headers().location, response.url());
      expect(location.pathname).toBe("/login");
      expect(location.searchParams.get("next")).toBe(path === "/app" ? null : path);
      expect(response.headers()["cache-control"]).toContain("no-store");
      expect(await response.text()).not.toContain("SIGNED IN AS");
    }
  }
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  for (const path of ["/register", "/verify-email", "/verification-required", "/forgot-password", "/reset-password"]) {
    expect((await request.get(path, { maxRedirects: 0 })).status(), path).toBe(200);
  }
  expect((await request.get("/demo")).status()).toBe(404);
  expect((await request.post("/api/demo/generate")).status()).toBe(404);
  expect((await request.post("/api/v1/workspaces", { data: { name: "Denied", slug: "denied" } })).status()).toBe(401);
});

test("login resumes a safe workspace deep link and rejects untrusted destinations", async ({ page, context }) => {
  const email = await register(page);
  const name = "Private deep link " + randomUUID();
  await page.getByLabel("Workspace name").fill(name);
  await page.getByLabel("Workspace slug").fill(`care-${randomUUID()}`);
  await page.getByRole("button", { name: "Create workspace", exact: true }).click();
  await expect(page.getByRole("heading", { name, exact: true })).toBeVisible();
  const origin = new URL(page.url()).origin;
  const workspace = new URL(page.url()).searchParams.get("workspace");
  const destination = `/app/tickets?workspace=${workspace}`;
  const cookie = (await context.cookies()).find((item) => item.name === "resolveflow_session")!;
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
  // A well-formed revoked cookie must pass neither the FastAPI check nor SSR.
  await context.addCookies([cookie]);
  const signedOutResponse = await page.goto(destination);
  expect(signedOutResponse?.headers()["cache-control"]).toContain("no-store");
  await expect(page).toHaveURL((url) => url.pathname === "/login" && url.searchParams.get("next") === destination);
  expect(await page.content()).not.toContain(name);
  expect(await page.content()).not.toContain(email);
  expect((await page.request.get("/api/v1/workspaces")).status()).toBe(401);
  await expect(page.getByRole("link", { name: "Create an account" })).toHaveAttribute(
    "href", `/register?${new URLSearchParams({ next: destination })}`,
  );
  async function login() {
    await page.getByLabel("Email address").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
  }
  await login();
  await expect(page).toHaveURL(origin + destination);
  await expect(page.getByRole("navigation", { name: "Workspaces" }).getByRole("link", { name: new RegExp(name) })).toBeVisible();
  const privatePage = await page.request.get(destination);
  expect(privatePage.headers()["cache-control"]).toContain("no-store");
  expect(await privatePage.text()).toContain(name);

  for (const unsafe of [
    "https://example.invalid/", "//example.invalid/", "/app/../login",
    "/app/%2f%2fexample.invalid", "/app\\..\\login", "/login?next=/app",
  ]) {
    await page.goto(`/login?${new URLSearchParams({ next: unsafe })}`);
    await expect(page.getByRole("link", { name: "Create an account" })).toHaveAttribute("href", "/register");
  }
  await login();
  await expect(page).toHaveURL(origin + "/app");
});

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
  await page.goto(firstUrl);
  await expect(page).toHaveURL(firstUrl);
  await context.clearCookies();
  await page.reload();
  const lastDestination = new URL(firstUrl);
  await expect(page).toHaveURL((url) => url.pathname === "/login" &&
    url.searchParams.get("next") === lastDestination.pathname + lastDestination.search);
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
