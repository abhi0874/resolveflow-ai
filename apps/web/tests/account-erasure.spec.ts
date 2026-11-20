import { expect, test } from "@playwright/test";

test("delete account requires a password and typed confirmation and closes private access", async ({ page }) => {
  const password = "disposable passphrase for deletion only!";
  await page.setViewportSize({width: 365, height: 790});
  await page.goto("/register");
  await page.getByLabel("Email address", {exact: true}).fill(`erase-${crypto.randomUUID()}@example.com`);
  await page.getByLabel("Password", {exact: true}).fill(password);
  await page.getByLabel("Confirm password", {exact: true}).fill(password);
  await page.getByRole("button", {name:"Create account",exact:true}).click();
  await expect(page).toHaveURL(/\/app$/);
  await page.getByRole("link",{name:"Personal settings"}).click();
  const trigger=page.getByRole("button",{name:"Delete account",exact:true});
  await trigger.click();
  const dialog=page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
  await trigger.click();
  await dialog.getByLabel("Current password for deletion", {exact:true}).fill(password);
  await dialog.getByRole("button",{name:"Verify password"}).click();
  const submit=dialog.getByRole("button",{name:"Permanently delete my account"});
  await expect(submit).toBeDisabled();
  await dialog.getByLabel("Type DELETE to confirm").fill("DELETE");
  await submit.click();
  await expect(page.getByText("Your ResolveFlow account was deleted.")).toBeVisible();
  expect((await page.request.get("/api/v1/account/profile")).status()).toBe(401);
  await page.goto("/app/settings/account");
  await expect(page).toHaveURL(/\/login/);
});

test("linked Google user reauthenticates before typed deletion", async ({ page, request }) => {
  test.skip(process.env.RESOLVEFLOW_TEST_GOOGLE !== "1", "Requires the isolated Google provider");
  let freshChecks = 0;
  await page.route("https://accounts.google.com/o/oauth2/v2/auth?**", async route => {
    const url = new URL(route.request().url());
    if (url.searchParams.get("claims")) {
      expect(JSON.parse(url.searchParams.get("claims")!)).toEqual({id_token: {auth_time: {essential: true}}});
      freshChecks++;
    }
    const grant = await request.get("http://127.0.0.1:8100/_fixture/google/authorize" + url.search);
    expect(grant.ok()).toBeTruthy();
    const callback = new URL("http://127.0.0.1:3100/auth/google/callback");
    callback.search = new URLSearchParams(await grant.json()).toString();
    await route.fulfill({status: 302, headers: {Location: callback.href}, body: ""});
  });
  await page.goto("/register");
  await page.getByRole("button", {name: "Continue with Google"}).click();
  await expect(page).toHaveURL(/\/app$/);
  await page.getByRole("link", {name:"Personal settings"}).click();
  await page.getByRole("button", {name:"Delete account",exact:true}).click();
  await page.getByRole("button", {name:"Verify with Google"}).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Type DELETE to confirm").fill("DELETE");
  await dialog.getByRole("button", {name:"Permanently delete my account"}).click();
  await expect(page.getByText("Your ResolveFlow account was deleted.")).toBeVisible();
  expect(freshChecks).toBe(1);
});
