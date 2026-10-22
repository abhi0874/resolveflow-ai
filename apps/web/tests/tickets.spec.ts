import {
  test,
  expect,
  type Page,
  type APIRequestContext,
} from "@playwright/test";
import { randomUUID } from "node:crypto";

async function write(
  request: APIRequestContext,
  path: string,
  body: unknown,
  method = "POST",
) {
  const csrf = await request.get("/api/v1/auth/csrf");
  expect(csrf.ok()).toBe(true);
  return request.fetch("/api/v1" + path, {
    method,
    data: body,
    headers: {
      Origin: "http://127.0.0.1:3100",
      "X-CSRF-Token": (await csrf.json()).csrf_token,
    },
  });
}
async function account(page: Page) {
  const email = `tickets-${randomUUID()}@example.com`;
  const response = await write(page.request, "/auth/register", {
    email,
    password: "ticket browser passphrase 123!",
    password_confirmation: "ticket browser passphrase 123!",
  });
  expect(response.status()).toBe(201);
  return response.json();
}
async function setup(page: Page) {
  const user = await account(page);
  const response = await write(page.request, "/workspaces", {
    name: "Customer experience",
    slug: `tickets-${randomUUID()}`,
  });
  expect(response.status()).toBe(201);
  const workspace = await response.json();
  await page.goto(`/app/tickets?workspace=${workspace.id}`);
  await expect(
    page.getByRole("heading", { name: "Your ticket inbox." }),
  ).toBeVisible();
  return { user, workspace, base: `/workspaces/${workspace.id}/tickets` };
}

test("ticket create, edit, assign, notes, filters and persisted activity across reload", async ({
  page,
}) => {
  const { user, workspace, base } = await setup(page);
  await expect(page.getByText("No tickets here yet.")).toBeVisible();
  await page.getByRole("button", { name: "＋ Create ticket" }).click();
  await page
    .getByRole("button", { name: "Create ticket", exact: true })
    .click();
  expect(
    await page
      .getByLabel("Ticket title")
      .evaluate((el: HTMLInputElement) => el.validity.valueMissing),
  ).toBe(true);
  await page.getByLabel("Ticket title").fill("Invoice export fails");
  await page
    .getByLabel("Description", { exact: true })
    .fill("The monthly export returns an error. Invoice number 42.");
  await page.getByLabel("Category", { exact: true }).fill("Billing");
  await page.getByLabel("Priority", { exact: true }).selectOption("high");
  await page.getByLabel("Assignee", { exact: true }).selectOption(user.id);
  await page
    .getByRole("button", { name: "Create ticket", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Invoice export fails", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("list", { name: "activity" })).toContainText(
    "Ticket created",
  );
  const url = page.url();
  await page.getByRole("button", { name: "Edit ticket", exact: true }).click();
  await page.getByLabel("Ticket title").fill("Invoice export recovered");
  await page.getByLabel("Status", { exact: true }).selectOption("resolved");
  await page.getByLabel("Priority", { exact: true }).selectOption("urgent");
  await page.getByLabel("Assignee", { exact: true }).selectOption("");
  await page.getByRole("button", { name: "Save ticket" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "Ticket saved." }),
  ).toBeVisible();
  await page
    .getByLabel("Add internal note")
    .fill("<script>window.attacked=true</script> Export verified.");
  await page.getByRole("button", { name: "Add note", exact: true }).click();
  await expect(page.getByRole("list", { name: "notes" })).toContainText(
    "<script>window.attacked=true</script>",
  );
  expect(await page.evaluate(() => "attacked" in window)).toBe(false);
  await expect(page.getByRole("list", { name: "activity" })).toContainText(
    "Status: Open → Resolved",
  );
  await page.reload();
  await expect(
    page.getByRole("heading", {
      name: "Invoice export recovered",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByRole("list", { name: "notes" })).toContainText(
    "Export verified",
  );
  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    await page.screenshot({
      path: `../../.cache/verification/ticket-detail-${colorScheme}.png`,
      fullPage: true,
    });
  }
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
  await page.screenshot({
    path: "../../.cache/verification/ticket-detail-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole("link", { name: "← Ticket inbox" }).click();
  await page.getByLabel("Search tickets").fill("monthly export");
  await page.getByLabel("Status", { exact: true }).selectOption("resolved");
  await page.getByLabel("Priority", { exact: true }).selectOption("urgent");
  await page.getByLabel("Assignee", { exact: true }).selectOption("unassigned");
  await page.getByLabel("Category", { exact: true }).fill("Billing");
  await page.getByLabel("Sort by").selectOption("updated_at");
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(
    page.getByRole("link", { name: "Invoice export recovered", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Search tickets").fill("not found");
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(page.getByText("No tickets here yet.")).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).click();
  await expect(
    page.getByRole("link", { name: "Invoice export recovered", exact: true }),
  ).toBeVisible();
  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    await page.screenshot({
      path: `../../.cache/verification/ticket-inbox-${colorScheme}.png`,
      fullPage: true,
    });
  }
  const persisted = await page.request.get("/api/v1" + base);
  expect((await persisted.json()).total).toBe(1);
  await page.goto(url.replace(workspace.id, randomUUID()));
  await expect(
    page.getByRole("heading", { name: "Choose a workspace." }),
  ).toBeVisible();
  await expect(page.getByText("Invoice export recovered")).toHaveCount(0);
});

test("server pagination, viewer restrictions and agent assignment limits in browser", async ({
  page,
  browser,
}) => {
  const { user, workspace, base } = await setup(page);
  // Synthetic rows are inserted through the real authenticated API into the isolated test DB.
  for (let i = 0; i < 26; i++) {
    expect(
      (
        await write(page.request, base, {
          title: `Request ${String(i).padStart(2, "0")}`,
          assigned_user_id: user.id,
        })
      ).status(),
    ).toBe(201);
  }
  await page.reload();
  await expect(page.getByRole("table").locator("tbody tr")).toHaveCount(25);
  await page.getByRole("button", { name: "Next →" }).click();
  await expect(page.getByRole("table").locator("tbody tr")).toHaveCount(1);
  await page.getByRole("button", { name: "← Previous" }).click();
  await expect(page.getByRole("table").locator("tbody tr")).toHaveCount(25);
  const memberContext = await browser.newContext();
  try {
    const memberPage = await memberContext.newPage();
    const member = await account(memberPage);
    expect(
      (
        await write(page.request, `/workspaces/${workspace.id}/members`, {
          email: member.email,
          role: "viewer",
        })
      ).status(),
    ).toBe(201);
    await memberPage.goto(`/app/tickets?workspace=${workspace.id}`);
    await expect(
      memberPage.getByRole("link", { name: "Request 25", exact: true }),
    ).toBeVisible();
    await expect(
      memberPage.getByRole("button", { name: "＋ Create ticket" }),
    ).toHaveCount(0);
    await memberPage
      .getByRole("link", { name: "Request 25", exact: true })
      .click();
    await expect(
      memberPage.getByRole("heading", { name: "Request 25", exact: true }),
    ).toBeVisible();
    await expect(
      memberPage.getByRole("button", { name: "Edit ticket", exact: true }),
    ).toHaveCount(0);
    await expect(memberPage.getByLabel("Add internal note")).toHaveCount(0);
    expect(
      (
        await write(memberPage.request, base, { title: "Not allowed" })
      ).status(),
    ).toBe(403);
    expect(
      (
        await write(
          page.request,
          `/workspaces/${workspace.id}/members/${member.id}`,
          { role: "support_agent" },
          "PATCH",
        )
      ).status(),
    ).toBe(200);
    await memberPage.reload();
    await expect(memberPage.getByLabel("Add internal note")).toBeVisible();
    await expect(
      memberPage.getByRole("button", { name: "Edit ticket", exact: true }),
    ).toHaveCount(0);
    await memberPage.getByRole("link", { name: "← Ticket inbox" }).click();
    await memberPage.getByRole("button", { name: "＋ Create ticket" }).click();
    await expect(
      memberPage.getByLabel("Priority", { exact: true }),
    ).toHaveCount(0);
    await expect(
      memberPage.getByLabel("Assignee", { exact: true }),
    ).toHaveCount(0);
    await memberPage.getByLabel("Ticket title").fill("Agent created");
    await memberPage
      .getByRole("button", { name: "Create ticket", exact: true })
      .click();
    await expect(
      memberPage.getByRole("heading", { name: "Agent created", exact: true }),
    ).toBeVisible();
    await expect(
      memberPage.getByRole("button", { name: "Edit ticket", exact: true }),
    ).toBeVisible();
  } finally {
    await memberContext.close();
  }
});

test("loading, unavailable requests, stale edits, validation, and expired ticket session", async ({
  page,
  context,
}) => {
  const { base } = await setup(page);
  let release: () => void = () => {};
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/tickets?*", async (route) => {
    await gate;
    await route.continue();
  });
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(
    page.getByRole("status", { name: "Loading tickets" }),
  ).toBeVisible();
  const completed = page.waitForResponse((response) =>
    response.url().includes("/tickets?"),
  );
  release();
  await completed;
  await page.unroute("**/tickets?*");
  await expect(page.getByText("No tickets here yet.")).toBeVisible();
  await page.route("**/tickets?*", (route) => route.abort());
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(
    page.getByRole("region", { name: "Ticket results" }).getByRole("alert"),
  ).toContainText("couldn’t reach the service");
  await page.unroute("**/tickets?*");
  await page.getByRole("button", { name: "Try again", exact: true }).click();
  await expect(page.getByText("No tickets here yet.")).toBeVisible();
  await page.getByRole("button", { name: "＋ Create ticket" }).click();
  await page.getByLabel("Ticket title").fill("Conflict case");
  await page
    .getByRole("button", { name: "Create ticket", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Conflict case", exact: true }),
  ).toBeVisible();
  const id = new URL(page.url()).pathname.split("/").at(-1)!;
  await page.getByRole("button", { name: "Edit ticket", exact: true }).click();
  expect(
    (
      await write(
        page.request,
        base + "/" + id,
        { title: "Concurrent revision", expected_version: 1 },
        "PATCH",
      )
    ).status(),
  ).toBe(200);
  await page.getByLabel("Ticket title").fill("My unsaved title");
  await page.getByRole("button", { name: "Save ticket" }).click();
  await expect(page.locator("form").getByRole("alert")).toContainText(
    "changed since you opened it",
  );
  await expect(page.getByLabel("Ticket title")).toHaveValue("My unsaved title");
  await page
    .getByRole("button", { name: "Refresh ticket", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Concurrent revision", exact: true }),
  ).toBeVisible();
  await page.setViewportSize({ width: 320, height: 844 });
  await page.getByRole("link", { name: "← Ticket inbox" }).click();
  await expect(
    page.getByRole("link", { name: "Concurrent revision", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../../.cache/verification/ticket-inbox-mobile.png",
    fullPage: true,
  });
  expect(
    (await page.request.get("/api/v1" + base + "?unexpected=1")).status(),
  ).toBe(404);
  expect(
    (await page.request.get("/api/v1" + base + "?page=1&page=2")).status(),
  ).toBe(404);
  await context.clearCookies();
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(page).toHaveURL(/\/login\?expired=1$/);
});
