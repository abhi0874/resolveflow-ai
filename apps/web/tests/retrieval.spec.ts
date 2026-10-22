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
test("real indexing, semantic search, source navigation, reindex and deleted exclusion", async ({page}) => {
  const {workspace, base} = await setup(page);
  const response = await upload(page.request, base, "refund-guide.txt", Buffer.from("Customers can request a refund within thirty days of their first purchase. Money returns to the original payment method. <script>window.retrievedScript=true</script>"));
  expect(response.status()).toBe(201);
  const doc = await response.json();
  await page.goto(`/app/knowledge-base/${doc.id}?workspace=${workspace.id}`);
  await expect(page.getByRole("heading", {name:"Not indexed", exact:true})).toBeVisible();
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  await page.route(`**/documents/${doc.id}/index`, async route => {await gate; await route.continue();});
  await page.getByRole("button", {name:"Index document", exact:true}).click();
  await expect(page.getByRole("button", {name:"Indexing…", exact:true})).toBeDisabled();
  release();
  await expect(page.getByRole("heading", {name:"Indexed", exact:true})).toBeVisible();
  await page.unroute(`**/documents/${doc.id}/index`);
  await page.getByRole("button", {name:"Reindex document"}).click();
  await expect(page.getByRole("heading", {name:"Indexed", exact:true})).toBeVisible();
  await page.getByRole("link", {name:"← Knowledge base"}).click();
  await page.getByLabel("Search knowledge", {exact:true}).fill("Can I get my money back after buying for the first time?");
  await page.getByRole("button", {name:"Search knowledge", exact:true}).click();
  const results = page.locator('.semantic-results');
  await expect(results).toContainText("refund-guide.txt");
  await expect(results).toContainText("<script>window.retrievedScript=true</script>");
  expect(await page.evaluate(() => 'retrievedScript' in window)).toBe(false);
  await expect(results).toContainText("Text source · Chunk 1");
  await page.screenshot({path:"../../.cache/verification/retrieval-light.png", fullPage:true});
  await page.emulateMedia({colorScheme:"dark"});
  await page.setViewportSize({width:390,height:844});
  await page.locator(".semantic-search").scrollIntoViewIfNeeded();
  await page.screenshot({path:"../../.cache/verification/retrieval-mobile-dark.png",fullPage:false});
  for (const width of [390,320]) {
    await page.setViewportSize({width,height:844});
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
  }
  await results.getByRole("link", {name:"View source document →"}).click();
  await expect(page.getByRole("heading", {name:"refund-guide.txt", exact:true})).toBeVisible();
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole("button", {name:"Delete document", exact:true}).click();
  await expect(page.getByRole("heading", {name:"Knowledge base.",exact:true})).toBeVisible();
  await page.getByLabel("Search knowledge", {exact:true}).fill("Can I get my money back?");
  await page.getByRole("button", {name:"Search knowledge",exact:true}).click();
  await expect(page.getByRole("heading", {name:"No relevant passages found."})).toBeVisible();
});

test("search loading, unavailable model, empty results, and changed access", async ({page}) => {
  const {workspace} = await setup(page);
  const search = `**/workspaces/${workspace.id}/knowledge-base/search`;
  await page.getByLabel("Search knowledge", {exact:true}).fill("Where is the account recovery guide?");
  let release!: () => void;
  const gate = new Promise<void>(resolve => {release=resolve;});
  await page.route(search, async route => {await gate; await route.fulfill({status:503,contentType:'application/json',body:'{}'});});
  await page.getByRole("button", {name:"Search knowledge",exact:true}).click();
  await expect(page.getByRole("button", {name:"Searching…"})).toBeDisabled();
  release();
  await expect(page.locator('.semantic-search').getByRole('alert')).toContainText('unavailable or busy');
  await page.unroute(search);
  await page.getByRole("button", {name:"Search knowledge",exact:true}).click();
  await expect(page.getByRole("heading", {name:"No relevant passages found."})).toBeVisible();
  await page.route(search, route => route.fulfill({status:401,contentType:'application/json',body:'{}'}));
  await page.getByRole("button", {name:"Search knowledge",exact:true}).click();
  await expect(page).toHaveURL(/\/login\?expired=1/);
});
