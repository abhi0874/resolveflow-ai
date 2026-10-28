import { test as base, expect } from "@playwright/test";

const test = base.extend<{ isolation: void }>({
  isolation: [async ({ context }, use) => {
    const blocked: string[] = [], errors: string[] = [];
    context.on("page", page => {
      page.on("pageerror", error => errors.push(error.name));
      page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
      page.on("requestfailed", request => { if (!request.failure()?.errorText.includes("ERR_ABORTED")) errors.push("Network failure: " + new URL(request.url()).pathname); });
    });
    await context.route("**/*", route => {
      const url = new URL(route.request().url());
      if (url.origin !== "http://127.0.0.1:3200" || url.pathname.startsWith("/api/")) {
        // Fail on attempted requests, even when aborting prevents network access.
        blocked.push(`${url.origin}${url.pathname}`);
        return route.abort("blockedbyclient");
      }
      return route.continue();
    });
    await use();
    expect(blocked, "Demo browsers must not attempt API or external requests").toEqual([]);
    expect(errors, "Demo pages must not raise uncaught exceptions").toEqual([]);
  }, { auto: true }],
});
test("public demo, local ticket edits, search, filters, creation, persistence and reset", async ({ page }) => {
  const apiRequests: string[] = []; page.on("request", request => { if (request.url().includes("/api/")) apiRequests.push(request.url()); });
  await page.goto("/"); await page.getByRole("link", { name: "Explore Live Demo" }).click();
  await expect(page.getByRole("heading", { name: "Every request. A considered response." })).toBeVisible();
  await expect(page.getByRole("article", { name: "Support tickets" }).locator("strong")).toHaveText("8");
  await page.getByRole("navigation", { name: "Demo navigation" }).getByRole("link", { name: "Ticket inbox" }).click();
  await page.getByLabel("Search tickets").fill("refund"); await expect(page.locator("tbody tr")).toHaveCount(1);
  await page.getByLabel("Filter priority").selectOption("urgent"); await expect(page.getByRole("heading", { name: "No matching demo tickets" })).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).click();
  await page.getByLabel("Filter status").selectOption("waiting_for_approval"); await expect(page.locator("tbody tr")).toHaveCount(2);
  await page.getByRole("link", { name: "Can I request a refund?", exact: true }).click();
  await page.getByLabel("Status", { exact: true }).selectOption("resolved");
  await page.getByLabel("Assigned to", { exact: true }).selectOption("Alex Morgan");
  await page.getByLabel("Add a synthetic internal note").fill("<script>window.demoInjected=true</script>");
  await page.getByRole("button", { name: "Add local note" }).click();
  await page.reload(); await expect(page.getByLabel("Status", { exact: true })).toHaveValue("resolved");
  await expect(page.getByLabel("Assigned to", { exact: true })).toHaveValue("Alex Morgan");
  await expect(page.locator(".demo-note").last()).toHaveText("<script>window.demoInjected=true</script>");
  expect(await page.evaluate(() => "demoInjected" in window)).toBe(false);
  await page.goto("/demo/tickets"); await page.getByRole("button", { name: "Create demo ticket", exact: true }).click();
  await page.getByLabel("Ticket title").fill("Synthetic temporary request"); await page.getByLabel("Customer request").fill("Example request for demo testing.");
  await page.getByRole("button", { name: "Save demo ticket" }).click(); await expect(page.locator("tbody tr")).toHaveCount(9);
  await page.goto("/demo/analytics"); await expect(page.getByRole("article", { name: "Tickets created" }).locator("strong")).toHaveText("9");
  await page.getByRole("button", { name: "Reset demo", exact: true }).click(); await page.getByRole("button", { name: "Confirm reset" }).click();
  await expect(page.getByRole("article", { name: "Tickets created" }).locator("strong")).toHaveText("8");
  expect(apiRequests).toEqual([]);
});
test("knowledge keyword search and exact citation navigation", async ({ page }) => {
  await page.goto("/demo/knowledge"); await page.getByLabel("Search documents").fill("30 minutes");
  await expect(page.getByRole("heading", { name: "Account Recovery Guide" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Refund Policy" })).toHaveCount(0);
  await page.getByRole("link", { name: /Account Recovery Guide/ }).click();
  await expect(page.locator("#recovery-1")).toContainText("Never share a password");
  await page.goto("/demo/workflows/billing"); await page.getByRole("link", { name: "Inspect source [refund-1]" }).click();
  await expect(page.locator("#refund-1")).toContainText("14 days");
});
test("replays are bounded, exact reviews persist and abstentions cannot be approved", async ({ page }) => {
  await page.goto("/demo/workflows/billing"); await expect(page.getByRole("button", { name: "Approve example" })).toBeDisabled();
  await page.getByRole("button", { name: "Replay example" }).click();
  await expect(page.getByText("Replay ready for human review", { exact: true })).toBeVisible();
  await page.getByLabel("I reviewed this exact example draft and its sources.").check();
  await page.getByRole("button", { name: "Approve example" }).click();
  await expect(page.getByText(/Recorded demo decision:/)).toContainText("approved");
  await page.reload(); await expect(page.getByText(/Recorded demo decision:/)).toContainText("approved");
  await page.goto("/demo/workflows/insufficient"); await page.getByRole("button", { name: "Show all stages" }).click();
  await page.getByLabel("I reviewed this exact example draft and its sources.").check();
  await expect(page.getByRole("button", { name: "Approve example" })).toBeDisabled();
  await page.getByRole("button", { name: "Request revision" }).click(); await expect(page.getByText(/Recorded demo decision:/)).toContainText("needs revision");
  await page.goto("/demo/workflows/account"); await page.getByRole("button", { name: "Next stage" }).click();
  await expect(page.getByText("Example stage 2 of 7 · Priority", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Show all stages" }).click(); await page.getByLabel("I reviewed this exact example draft and its sources.").check();
  await page.getByRole("button", { name: "Reject example" }).click(); await expect(page.getByText(/Recorded demo decision:/)).toContainText("rejected");
});
test("analytics filters, navigation, responsive layout and theme", async ({ page }) => {
  await page.goto("/demo/analytics"); await expect(page.getByRole("article", { name: "Tickets created" }).locator("strong")).toHaveText("8");
  await expect(page.locator(".recharts-surface").first()).toBeVisible();
  await page.getByLabel("From (UTC)").fill("2020-01-01"); await page.getByLabel("Through (UTC)").fill("2020-01-02"); await page.getByRole("button", { name: "Apply range" }).click();
  await expect(page.getByRole("heading", { name: "No activity in this range" })).toBeVisible();
  await page.goto("/demo"); await page.screenshot({ path: "../../.cache/verification/demo-desktop.png", fullPage: true });
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 }); await page.emulateMedia({ colorScheme: "dark", reducedMotion: "reduce" });
    for (const path of ["/demo", "/demo/tickets", "/demo/workflows/billing", "/demo/analytics", "/demo/knowledge", "/demo/architecture"]) {
      await page.goto(path); await expect(page.getByRole("navigation", { name: "Demo navigation" })).toBeVisible();
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
    }
  }
  await page.goto("/demo"); await page.screenshot({ path: "../../.cache/verification/demo-mobile.png", fullPage: true });
});
test("corrupt or blocked storage recovers and unknown records are safe", async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("resolveflow-demo-v1", '{"private":"invalid"}'));
  await page.goto("/demo"); await expect(page.getByText(/Saved demo data could not be restored/)).toBeVisible();
  await page.goto("/demo/tickets/private-workspace-id"); await expect(page.getByRole("heading", { name: "Demo ticket not found" })).toBeVisible();
});
test("demo deployment rejects full API access, real sessions, and all live generation attempts", async ({ request, page }) => {
  for (const path of ["auth/me", "workspaces", "workspaces/00000000-0000-0000-0000-000000000000/documents"]) {
    expect((await request.get(`/api/v1/${path}`, { headers: { Cookie: `resolveflow_session=${"a".repeat(43)}` } })).status()).toBe(404);
    expect((await request.post(`/api/v1/${path}`, { data: { title: "synthetic" } })).status()).toBe(404);
  }
  for (const data of [{}, { scenario: "billing" }, { scenario: "arbitrary", prompt: "unbounded", maxOutputTokens: 999999 }, { apiKey: "synthetic-canary-key" }]) {
    const response = await request.post("/api/demo/generate", { data }); expect(response.status()).toBe(403);
    expect((await response.json()).error.code).toBe("demo_live_disabled"); expect(await response.text()).not.toContain("synthetic-canary-key");
  }
  await page.goto("/app"); await expect(page).toHaveURL(/\/demo$/);
  await page.goto("/login"); await expect(page).toHaveURL(/\/demo$/);
  expect(await page.context().cookies()).toEqual([]);
});

test("release headers and backend-only routes remain safe", async ({ request, page }) => {
  for (const path of ["/", "/demo", "/demo/tickets", "/api/v1/auth/me"]) {
    const response = await request.get(path);
    const headers = response.headers();
    expect(headers["content-security-policy"]).toContain("connect-src 'self'");
    expect(headers["content-security-policy"]).toContain("frame-ancestors 'none'");
    expect(headers["content-security-policy"]).not.toContain("unsafe-eval");
    expect(headers["x-content-type-options"]).toBe("nosniff");
    expect(headers["x-frame-options"]).toBe("DENY");
    expect(headers["referrer-policy"]).toBe("same-origin");
    expect(headers["strict-transport-security"]).toContain("max-age=31536000");
    expect(headers["x-powered-by"]).toBeUndefined();
    expect(headers["set-cookie"]).toBeUndefined();
  }
  for (const path of ["/login?next=https://example.invalid", "/register", "/app", "/app/tickets", "/app/tickets/synthetic", "/app/knowledge-base", "/app/knowledge-base/synthetic", "/app/analytics"]) {
    // Suspense routes may stream a redirect in HTML rather than an HTTP 3xx.
    await page.goto(path);
    await expect(page).toHaveURL("http://127.0.0.1:3200/demo");
    await expect(page.getByRole("navigation", { name: "Demo navigation" })).toBeVisible();
  }
  for (const method of ["PATCH", "DELETE", "PUT"]) {
    const response = await request.fetch("/api/v1/workspaces/synthetic", { method });
    expect([404, 405]).toContain(response.status());
  }
});

test("all reachable landing and demo links resolve within the demonstration", async ({ page }) => {
  const pending = ["/", "/demo"], visited = new Set<string>();
  while (pending.length) {
    const path = pending.shift()!;
    if (visited.has(path)) continue;
    visited.add(path);
    expect(visited.size, "Navigation crawl must stay bounded").toBeLessThan(60);
    const response = await page.goto(path);
    expect(response?.status(), path).toBe(200);
    if (path.startsWith("/demo")) await expect(page.getByRole("navigation", { name: "Demo navigation" })).toBeVisible();
    const links = await page.locator("a[href]").evaluateAll(anchors => anchors.map(a => (a as HTMLAnchorElement).href));
    for (const href of links) {
      const url = new URL(href);
      expect(url.origin).toBe("http://127.0.0.1:3200");
      expect(url.pathname === "/" || url.pathname.startsWith("/demo")).toBe(true);
      if (url.pathname === new URL(page.url()).pathname && url.hash) {
        expect(await page.locator(`[id=${JSON.stringify(decodeURIComponent(url.hash.slice(1)))}]`).count(), href).toBe(1);
      }
      if (!visited.has(url.pathname)) pending.push(url.pathname);
    }
  }
  expect(visited.size).toBeGreaterThan(20);
});

test("demo keyboard access, touch targets, table scrolling and contrast", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/demo/tickets");
  await expect(page.getByRole("navigation", { name: "Demo navigation" })).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to demo content" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#demo-content")).toBeFocused();
  const table = page.getByRole("region", { name: "Support ticket table" });
  await expect(table).toHaveAccessibleDescription(/Scroll horizontally/);
  await table.focus();
  expect(await table.evaluate(el => getComputedStyle(el).outlineStyle)).toBe("solid");
  await page.keyboard.press("ArrowRight");
  await expect.poll(() => table.evaluate(el => el.scrollLeft)).toBeGreaterThan(0);
  await expect(page.locator("th[scope=col]")).toHaveCount(4);
  for (const theme of ["light", "dark"] as const) {
    await page.evaluate(value => { localStorage.setItem("resolveflow-theme", value); document.documentElement.dataset.theme = value; window.dispatchEvent(new Event("resolveflow-theme")); }, theme);
    const contrast = await page.evaluate(() => {
      const css = getComputedStyle(document.documentElement);
      function luminance(hex: string) { const raw = hex.trim().replace("#", ""); const normalized = raw.length === 3 ? raw.split("").map(c => c + c).join("") : raw; const c = normalized.match(/../g)!.map(v => parseInt(v, 16) / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4); return c[0] * .2126 + c[1] * .7152 + c[2] * .0722; }
      const ratios: number[] = [];
      for (const fg of ["--foreground", "--muted"]) for (const bg of ["--background", "--surface"]) { const a = luminance(css.getPropertyValue(fg)), b = luminance(css.getPropertyValue(bg)); ratios.push((Math.max(a,b)+.05)/(Math.min(a,b)+.05)); }
      return Math.min(...ratios);
    });
    expect(contrast).toBeGreaterThanOrEqual(4.5);
  }
  for (const width of [1440, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    for (const path of ["/demo", "/demo/tickets", "/demo/knowledge", "/demo/workflows/billing", "/demo/analytics", "/demo/architecture"]) {
      await page.goto(path);
      await expect(page.getByRole("navigation", { name: "Demo navigation" })).toBeVisible();
      expect(await page.locator("h1").count()).toBe(1);
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
      const small = await page.locator(".demo-page a:not(.skip-link), .demo-page button, .demo-page summary").evaluateAll(es => es.filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && (r.width < 43.9 || r.height < 43.9); }).map(el => el.textContent));
      expect(small, `${width}px ${path} targets`).toEqual([]);
    }
  }
});


test("critical demo screens pass automated WCAG accessibility checks", async ({ page }) => {
  await page.goto("/");
  for (const theme of ["light", "dark"] as const) {
    await page.evaluate(value => { localStorage.setItem("resolveflow-theme", value); document.documentElement.dataset.theme = value; window.dispatchEvent(new Event("resolveflow-theme")); }, theme);
    for (const path of ["/", "/demo", "/demo/tickets", "/demo/workflows/billing", "/demo/analytics", "/demo/architecture"]) {
      await page.goto(path);
      if (path !== "/") await expect(page.getByRole("navigation", { name: "Demo navigation" })).toBeVisible();
      await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
      const violations = await page.evaluate(async () => {
        const axe = (window as unknown as { axe: { run: (options: object) => Promise<{ violations: { id: string; nodes: { target: string[] }[] }[] }> } }).axe;
        const result = await axe.run({ runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] } });
        return result.violations.map(v => ({ id: v.id, targets: v.nodes.map(n => n.target) }));
      });
      expect(violations, `${theme} ${path}`).toEqual([]);
    }
  }
});

base("production CSP blocks external connections and inline event handlers", async ({ page, context }) => {
  const escaped: string[] = [];
  await context.route("https://example.invalid/**", route => { escaped.push(route.request().url()); return route.abort(); });
  await page.goto("/demo");
  await expect(page.getByRole("navigation", { name: "Demo navigation" })).toBeVisible();
  const outcome = await page.evaluate(async () => {
    const violations: string[] = [];
    document.addEventListener("securitypolicyviolation", e => violations.push(e.effectiveDirective));
    const button = document.createElement("button");
    button.setAttribute("onclick", "document.documentElement.dataset.cspInjected='yes'");
    document.body.append(button); button.click(); button.remove();
    let blocked = false;
    try { await fetch("https://example.invalid/csp-check"); } catch { blocked = true; }
    await new Promise(resolve => setTimeout(resolve, 50));
    return { blocked, injected: document.documentElement.dataset.cspInjected, violations };
  });
  expect(outcome.blocked).toBe(true);
  expect(outcome.injected).toBeUndefined();
  expect(outcome.violations).toContain("connect-src");
  expect(outcome.violations).toContain("script-src-attr");
  expect(escaped).toEqual([]);
});


test("engineering case study explains boundaries and supports keyboard navigation", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/demo");
  await page.getByRole("navigation", { name: "Demo navigation" }).getByRole("link", { name: "Under the hood" }).click();
  await expect(page.getByRole("heading", { name: "Under the hood", exact: true })).toBeVisible();
  await expect(page.getByText("Live Gemini inference is disabled.", { exact: true })).toBeVisible();
  await expect(page.getByRole("list", { name: "Background execution data flow" }).getByRole("listitem")).toHaveCount(5);
  await expect(page.locator(".engineering-stages > li")).toHaveCount(7);
  await expect(page.getByRole("heading", { name: "Recorded results, with their limits" })).toBeVisible();
  await expect(page.getByText("0.784580 macro F1", { exact: true })).toBeVisible();
  await expect(page.getByText("0.928571 Recall@5", { exact: true })).toBeVisible();
  await expect(page.getByText(/The complete Python backend is not currently hosted on Vercel/)).toBeVisible();
  const workflow = page.getByRole("link", { name: "Explore a workflow", exact: true });
  await workflow.focus(); await expect(workflow).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/demo\/workflows\/billing$/);
  await page.goBack();
  await page.getByRole("link", { name: "Back to landing page", exact: true }).click();
  await expect(page).toHaveURL("/");
});

test("reset dialog contains keyboard focus, cancels with Escape and restores its trigger", async ({ page }) => {
  await page.goto("/demo");
  const trigger = page.getByRole("button", { name: "Reset demo", exact: true });
  await trigger.click();
  const dialog = page.getByRole("dialog", { name: "Start fresh?" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Keep exploring" })).toBeFocused();
  for (let i = 0; i < 5; i++) {
    await page.keyboard.press("Tab");
    expect(await dialog.evaluate(el => el.contains(document.activeElement))).toBe(true);
  }
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(trigger).toBeFocused();
  await trigger.click();
  await page.getByRole("button", { name: "Keep exploring" }).click();
  await expect(trigger).toBeFocused();
  await expect(page.getByRole("article", { name: "Support tickets" }).locator("strong")).toHaveText("8");
});

test("reduced motion removes UI animation without disabling workflow controls", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.getByRole("link", { name: "Explore Live Demo" })).toBeVisible();
  expect(await page.locator(".hero-copy").evaluate(el => getComputedStyle(el).animationName)).toBe("none");
  await page.getByRole("link", { name: "Explore the engineering" }).click();
  await expect(page.getByRole("heading", { name: "Under the hood", exact: true })).toBeVisible();
  expect(await page.locator(".demo-heading").evaluate(el => getComputedStyle(el).animationName)).toBe("none");
  await page.getByRole("link", { name: "Explore a workflow", exact: true }).click();
  await page.getByRole("button", { name: "Next stage" }).click();
  await expect(page.getByText("Example stage 2 of 7 · Priority", { exact: true })).toBeVisible();
  const current = page.locator('.workflow-stages li[data-state="current"]');
  expect(await current.evaluate(el => getComputedStyle(el).transitionDuration)).toBe("0s");
  await page.getByRole("button", { name: "Show all stages" }).click();
  await expect(page.getByText("Replay ready for human review", { exact: true })).toBeVisible();
});


test("theme defaults dark and persists keyboard selections across routes, reloads and new tabs", async ({ page, context }) => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.getByRole("button", { name: "Dark theme" })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Light theme" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByRole("link", { name: "Explore Live Demo" }).click();
  await expect(page.getByRole("button", { name: "Light theme" })).toHaveAttribute("aria-pressed", "true");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  const other = await context.newPage();
  await other.goto("/demo/architecture");
  await expect(other.getByRole("button", { name: "Light theme" })).toHaveAttribute("aria-pressed", "true");
  await other.getByRole("button", { name: "Dark theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.setViewportSize({ width: 320, height: 844 });
  await expect(page.getByRole("group", { name: "Color theme" })).toBeVisible();
  await page.getByRole("button", { name: "Light theme" }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(320);
});

test("saved theme applies before body parsing and blocked storage remains usable", async ({ page, context }) => {
  await context.addInitScript(() => {
    try { localStorage.setItem("resolveflow-theme", "light"); } catch {}
    new MutationObserver(() => { if (document.body && !document.body.dataset.initialTheme) document.body.dataset.initialTheme = document.documentElement.dataset.theme; }).observe(document, { childList: true, subtree: true });
  });
  await page.goto("/");
  await expect(page.locator("body")).toHaveAttribute("data-initial-theme", "light");
  await page.addInitScript(() => { Object.defineProperty(window, "localStorage", { get() { throw new DOMException("Blocked", "SecurityError"); } }); });
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: "Light theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});
