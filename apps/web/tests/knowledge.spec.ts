import { inviteMember } from "./invitation-helper";
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
  const result = await write(page.request, "/auth/register", {
    email: `knowledge-${randomUUID()}@example.com`,
    password: "knowledge test passphrase 42!",
    password_confirmation: "knowledge test passphrase 42!",
  });
  expect(result.status()).toBe(201);
  return result.json();
}
async function setup(page: Page) {
  const user = await account(page);
  const result = await write(page.request, "/workspaces", {
    name: "Support library",
    slug: `library-${randomUUID()}`,
  });
  expect(result.status()).toBe(201);
  const workspace = await result.json();
  await page.goto(`/app/knowledge-base?workspace=${workspace.id}`);
  await expect(
    page.getByRole("heading", { name: "Knowledge base.", exact: true }),
  ).toBeVisible();
  return { user, workspace, base: `/workspaces/${workspace.id}/documents` };
}
async function upload(
  request: APIRequestContext,
  base: string,
  name: string,
  data: Buffer,
) {
  const csrf = await request.get("/api/v1/auth/csrf");
  return request.post("/api/v1" + base, {
    data,
    headers: {
      "Content-Type": "application/octet-stream",
      "X-Upload-Filename": encodeURIComponent(name),
      Origin: "http://127.0.0.1:3100",
      "X-CSRF-Token": (await csrf.json()).csrf_token,
    },
  });
}
test("real upload, literal text preview, download, search and confirmed deletion", async ({
  page,
}) => {
  const { workspace, base } = await setup(page);
  await expect(page.getByText("No documents found.")).toBeVisible();
  await page.getByRole("button", { name: "↑ Upload document" }).click();
  await page
    .getByLabel("Choose document file")
    .setInputFiles({
      name: "program.exe",
      mimeType: "application/octet-stream",
      buffer: Buffer.from("MZ"),
    });
  await expect(
    page.getByRole("region", { name: "Document upload" }).getByRole("alert"),
  ).toContainText("PDF, TXT or Markdown");
  await page
    .getByLabel("Choose document file")
    .setInputFiles({
      name: "large.txt",
      mimeType: "text/plain",
      buffer: Buffer.alloc(2097153, 65),
    });
  await expect(
    page.getByRole("region", { name: "Document upload" }).getByRole("alert"),
  ).toContainText("no larger than");
  await page
    .getByLabel("Choose document file")
    .setInputFiles({
      name: "empty.txt",
      mimeType: "text/plain",
      buffer: Buffer.alloc(0),
    });
  await expect(
    page.getByRole("region", { name: "Document upload" }).getByRole("alert"),
  ).toContainText("empty");
  const body =
    "# Account handbook\n\n<script>window.executed=true</script>\n\n" +
    "Reset your password using the secure account settings. ".repeat(160);
  // Exercise actual drag-and-drop, backed by a real browser File and DataTransfer.
  const transfer = await page.evaluateHandle((content) => {
    const transfer = new DataTransfer();
    transfer.items.add(
      new File([content], "account-handbook.md", { type: "text/markdown" }),
    );
    return transfer;
  }, body);
  await page
    .locator(".document-dropzone")
    .dispatchEvent("drop", { dataTransfer: transfer });
  await page
    .getByRole("button", { name: "Upload document", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "account-handbook.md", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("list", { name: "Document chunks" }),
  ).toContainText("<script>window.executed=true</script>");
  expect(await page.evaluate(() => "executed" in window)).toBe(false);
  await page.getByRole("button", { name: "Next chunks" }).click();
  await expect(
    page.getByRole("list", { name: "Document chunks" }),
  ).toContainText("Chunk 6");
  await page.getByRole("button", { name: "Previous chunks" }).click();
  await expect(
    page.getByRole("list", { name: "Document chunks" }),
  ).toContainText("Chunk 1");
  const downloadEvent = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download original ↓" }).click();
  const download = await downloadEvent;
  expect(download.suggestedFilename()).toBe("account-handbook.md");
  const stream = await download.createReadStream();
  const buffers: Buffer[] = [];
  for await (const chunk of stream!) buffers.push(Buffer.from(chunk));
  expect(Buffer.concat(buffers).toString()).toBe(body);
  const detailUrl = page.url();
  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    await page.screenshot({
      path: `../../.cache/verification/knowledge-detail-${colorScheme}.png`,
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
    path: "../../.cache/verification/knowledge-detail-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page
    .getByRole("link", { name: "← Knowledge base", exact: true })
    .click();
  await page.getByLabel("Search documents").fill("account");
  await page.getByLabel("Processing status").selectOption("completed");
  await page.getByLabel("Sort by").selectOption("file_size");
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(
    page.getByRole("link", { name: "account-handbook.md", exact: true }),
  ).toBeVisible();
  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    await page.screenshot({
      path: `../../.cache/verification/knowledge-list-${colorScheme}.png`,
      fullPage: true,
    });
  }
  await page.getByLabel("Search documents").fill("absent");
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(page.getByText("No documents found.")).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).click();
  await expect(
    page.getByRole("link", { name: "account-handbook.md", exact: true }),
  ).toBeVisible();
  await page.goto(detailUrl);
  await expect(
    page.getByRole("button", { name: "Delete document", exact: true }),
  ).toBeVisible();
  page.once("dialog", (dialog) => dialog.dismiss());
  await page
    .getByRole("button", { name: "Delete document", exact: true })
    .click();
  await expect(page).toHaveURL(detailUrl);
  page.once("dialog", (dialog) => dialog.accept());
  await page
    .getByRole("button", { name: "Delete document", exact: true })
    .click();
  await expect(page).toHaveURL(
    `http://127.0.0.1:3100/app/knowledge-base?workspace=${workspace.id}`,
  );
  await expect(page.getByText("No documents found.")).toBeVisible();
  expect((await page.request.get("/api/v1" + base)).ok()).toBe(true);
  await page.goto(detailUrl);
  await expect(
    page.locator(".workspace-content").getByRole("alert"),
  ).toContainText("unavailable");
});
test("document role controls, tenant isolation and paginated library", async ({
  page,
  browser,
}) => {
  const { workspace, base } = await setup(page);
  for (let i = 0; i < 26; i++)
    expect(
      (
        await upload(
          page.request,
          base,
          `guide-${i}.txt`,
          Buffer.from(`Unique guide ${i}`),
        )
      ).status(),
    ).toBe(201);
  await page.reload();
  await expect(page.getByRole("table").locator("tbody tr")).toHaveCount(25);
  await page.getByRole("button", { name: "Next →" }).click();
  await expect(page.getByRole("table").locator("tbody tr")).toHaveCount(1);
  await page.getByRole("button", { name: "← Previous" }).click();
  await expect(page.getByRole("table").locator("tbody tr")).toHaveCount(25);
  const context = await browser.newContext();
  try {
    const other = await context.newPage();
    const user = await account(other);
    await other.goto(page.url());
    await expect(
      other.getByRole("heading", { name: "Choose a workspace." }),
    ).toBeVisible();
    expect(
      (
        await inviteMember(page.request, other.request, `/workspaces/${workspace.id}/members`, {
          email: user.email,
          role: "viewer",
        })
      ).status(),
    ).toBe(201);
    await other.goto(page.url());
    await expect(
      other.getByRole("link", { name: "guide-25.txt", exact: true }),
    ).toBeVisible();
    await expect(
      other.getByRole("button", { name: "↑ Upload document" }),
    ).toHaveCount(0);
    await expect(other.getByLabel("Search knowledge", {exact: true})).toHaveCount(0);
    await other
      .getByRole("link", { name: "guide-25.txt", exact: true })
      .click();
    await expect(
      other.getByRole("heading", { name: "guide-25.txt", exact: true }),
    ).toBeVisible();
    await expect(other.getByRole("button", {name:"Index document", exact:true})).toHaveCount(0);
    await expect(
      other.getByRole("button", { name: "Download original ↓" }),
    ).toHaveCount(0);
    await expect(
      other.getByRole("button", { name: "Delete document", exact: true }),
    ).toHaveCount(0);
    await expect(
      other.getByRole("list", { name: "Document chunks" }),
    ).toHaveCount(0);
    expect(
      (
        await write(
          page.request,
          `/workspaces/${workspace.id}/members/${user.id}`,
          { role: "support_agent" },
          "PATCH",
        )
      ).status(),
    ).toBe(200);
    await other.reload();
    await expect(
      other.getByRole("button", { name: "Download original ↓" }),
    ).toBeVisible();
    await expect(
      other.getByRole("button", { name: "Delete document", exact: true }),
    ).toHaveCount(0);
    await other
      .getByRole("link", { name: "← Knowledge base", exact: true })
      .click();
    await expect(
      other.getByRole("button", { name: "↑ Upload document" }),
    ).toBeVisible();
  } finally {
    await context.close();
  }
});
test("processing failure, retry, request errors and expired document session", async ({
  page,
  context,
}) => {
  const { workspace, base } = await setup(page);
  await page.getByRole("button", { name: "↑ Upload document" }).click();
  await page
    .getByLabel("Choose document file")
    .setInputFiles({
      name: "broken.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.7 malformed"),
    });
  await page
    .getByRole("button", { name: "Upload document", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "broken.pdf", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("status").filter({ hasText: "Processing needs attention" }),
  ).toContainText("damaged or unsupported");
  await page.getByRole("button", { name: "Retry processing" }).click();
  await expect(
    page.getByRole("button", { name: "Retry processing" }),
  ).toBeEnabled();
  await page
    .getByRole("link", { name: "← Knowledge base", exact: true })
    .click();
  await expect(page.getByRole("link", { name: "broken.pdf", exact: true })).toBeVisible();
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  await page.route("**/documents?*", async (route) => {
    await gate;
    await route.continue();
  });
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(page.getByRole("status", { name: "Loading documents" })).toBeVisible();
  const loaded = page.waitForResponse((response) => response.url().includes("/documents?") && response.ok());
  release();
  await loaded;
  await expect(page.getByRole("link", { name: "broken.pdf", exact: true })).toBeVisible();
  await page.unroute("**/documents?*");
  await page.route("**/documents?*", (route) => route.abort());
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(
    page.getByRole("region", { name: "Document results" }).getByRole("alert"),
  ).toContainText("couldn’t reach");
  await page.unroute("**/documents?*");
  await page.getByRole("button", { name: "Try again", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "broken.pdf", exact: true }),
  ).toBeVisible();
  await page.setViewportSize({ width: 320, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../../.cache/verification/knowledge-list-mobile.png",
    fullPage: true,
  });
  expect(
    (await page.request.get("/api/v1" + base + "?page=1&page=2")).status(),
  ).toBe(404);
  await context.clearCookies();
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(page).toHaveURL(/\/login\?expired=1$/);
  await page.goto(`/app/knowledge-base?workspace=${workspace.id}`);
  await expect(page).toHaveURL(/\/login$/);
});
