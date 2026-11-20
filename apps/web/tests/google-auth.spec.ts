import { test, expect } from "@playwright/test";

test("Google registration and return login use the real account session", async ({ page, request }) => {
  test.skip(process.env.RESOLVEFLOW_TEST_GOOGLE !== "1", "Requires the isolated Google provider");
  let authorizations = 0;
  await page.route("https://accounts.google.com/o/oauth2/v2/auth?**", async route => {
    const query = new URL(route.request().url()).search;
    const granted = await request.get("http://127.0.0.1:8100/_fixture/google/authorize" + query);
    expect(granted.status()).toBe(200);
    const callback = new URL("http://127.0.0.1:3100/auth/google/callback");
    callback.search = new URLSearchParams(await granted.json()).toString();
    authorizations += 1;
    await route.fulfill({ status: 302, headers: { Location: callback.href }, body: "" });
  });
  let userId = "";
  for (const path of ["/register", "/login"]) {
    await page.goto(path + "?next=%2Fapp%2Fanalytics");
    await page.getByRole("button", { name: "Continue with Google" }).click();
    await expect(page).toHaveURL("http://127.0.0.1:3100/app/analytics");
    const me = await page.request.get("/api/v1/auth/me");
    expect(me.status()).toBe(200);
    const user = await me.json();
    expect(user.email).toBe("fixture@example.com");
    if (userId) expect(user.id).toBe(userId);
    userId = user.id;
    await page.goto("/app");
    await page.getByRole("button", {name: "Sign out"}).click();
    await expect(page).toHaveURL(/\/login$/);
    expect((await page.request.get("/api/v1/auth/me")).status()).toBe(401);
  }
  expect(authorizations).toBe(2);
  await page.goto("/auth/google/callback?state=invalid");
  await expect(page).toHaveURL(/\/login\?google=failed$/);
  await expect(page.locator("form").getByRole("alert")).toContainText("use your existing sign-in method");
});
