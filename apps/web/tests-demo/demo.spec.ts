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
  await expect(page.getByRole("heading", { name: "Your workspace. Understood." })).toBeVisible();
  await expect(page.getByRole("article", { name: "Support tickets" }).locator("strong")).toHaveText("8");
  await page.getByRole("navigation", { name: "Demo navigation" }).getByRole("link", { name: "Ticket inbox" }).click();
  await page.getByLabel("Search tickets").fill("refund"); await expect(page.locator(".conversation-list > li")).toHaveCount(1);
  await page.getByLabel("Filter priority").selectOption("urgent"); await expect(page.getByRole("heading", { name: "No matching demo tickets" })).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).click();
  await page.getByLabel("Filter status").selectOption("waiting_for_approval"); await expect(page.locator(".conversation-list > li")).toHaveCount(2);
  await page.getByRole("link", { name: "Can I request a refund?", exact: true }).click();
  await expect(page).toHaveURL(/\/demo\/tickets\/refund$/);
  await expect(page.getByLabel("Assigned to", { exact: true })).toHaveValue("Maya Chen");
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
  await page.getByRole("button", { name: "Save demo ticket" }).click(); await expect(page.locator(".conversation-list > li")).toHaveCount(9);
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
  await page.goto("/demo"); await page.screenshot({ path: "../../.cache/structural-redesign/journey-desktop.png", fullPage: true });
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 }); await page.emulateMedia({ colorScheme: "dark", reducedMotion: "reduce" });
    for (const path of ["/demo", "/demo/tickets", "/demo/workflows/billing", "/demo/analytics", "/demo/knowledge", "/demo/architecture"]) {
      await page.goto(path); await page.getByRole("button", { name: "Open navigation" }).click();
      await expect(page.getByRole("navigation", { name: "Demo navigation" })).toBeVisible();
      await page.getByRole("button", { name: "Close navigation" }).click();
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
    }
  }
  await page.goto("/demo"); await page.screenshot({ path: "../../.cache/structural-redesign/journey-mobile.png", fullPage: true });
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

test("demo keyboard access, touch targets, inbox pane navigation and contrast", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/demo/tickets");
  await expect(page.getByRole("button", { name: "Open navigation" })).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to demo content" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#demo-content")).toBeFocused();
  const conversation = page.getByRole("link", { name: "Can I request a refund?", exact: true });
  await conversation.focus();
  expect(await conversation.evaluate(el => getComputedStyle(el).outlineStyle)).toBe("solid");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("region", { name: "Selected conversation" })).toBeVisible();
  await expect(page.getByRole("complementary", { name: "Ticket intelligence" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Ticket list" })).not.toBeVisible();
  await page.getByRole("link", { name: "All conversations" }).click();
  await expect(page.getByRole("region", { name: "Ticket list" })).toBeVisible();
  await expect(page.locator(".conversation-list > li")).toHaveCount(8);
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
      if (width <= 760) {
        await page.getByRole("button", { name: "Open navigation" }).click();
        await expect(page.getByRole("navigation", { name: "Demo navigation" })).toBeVisible();
        await page.getByRole("button", { name: "Close navigation" }).click();
      } else await expect(page.getByRole("navigation", { name: "Demo navigation" })).toBeVisible();
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
      await page.evaluate(() => Promise.all(document.getAnimations().map(animation => animation.finished.catch(() => {}))));
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


test("theme follows the system and persists keyboard selections across routes, reloads and new tabs", async ({ page, context }) => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await expect(page.getByRole("button", { name: "System theme" })).toHaveAttribute("aria-pressed", "true");
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: "Light theme" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByRole("link", { name: "Explore Live Demo" }).click();
  await expect(page).toHaveURL(/\/demo$/);
  await expect(page.getByRole("heading", { name: "Your workspace. Understood." })).toBeVisible();
  await expect(page.getByRole("button", { name: "Light theme" })).toHaveAttribute("aria-pressed", "true");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  const other = await context.newPage();
  await other.goto("/demo/architecture");
  await expect(other.getByRole("button", { name: "Light theme" })).toHaveAttribute("aria-pressed", "true");
  await other.getByRole("button", { name: "Dark theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.setViewportSize({ width: 320, height: 844 });
  await page.getByRole("button", { name: "Open navigation" }).click();
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
  await page.emulateMedia({ colorScheme: "dark" });
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: "Light theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

test("new palette maintains accessible contrast, responsive navigation and disabled approval", async ({ page }) => {
  await page.goto("/");
  for (const theme of ["dark", "light"] as const) {
    await page.getByRole("button", { name: `${theme === "dark" ? "Dark" : "Light"} theme`, exact: true }).click();
    for (const width of [1440, 1024, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      for (const link of await page.locator(".main-nav a").all()) {
        const bounds = await link.boundingBox();
        expect(bounds).not.toBeNull();
        expect(bounds!.x).toBeGreaterThanOrEqual(0);
        expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width);
        expect(bounds!.height).toBeGreaterThanOrEqual(44);
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
    }
    const capability = page.getByRole("link", { name: "Capabilities", exact: true });
    await capability.focus(); await page.keyboard.press("Tab"); await page.keyboard.press("Shift+Tab");
    await expect(capability).toBeFocused();
    expect(await capability.evaluate(el => getComputedStyle(el).outlineStyle)).toBe("solid");
    await page.keyboard.press("Enter"); await expect(page).toHaveURL(/#capabilities$/);
    const contrast = await page.evaluate(() => {
      const css = getComputedStyle(document.documentElement);
      function lum(value: string) { const c = value.trim().replace("#", "").match(/../g)!.map(v=>parseInt(v,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4); return c[0]*.2126+c[1]*.7152+c[2]*.0722; }
      const pairs = [["--foreground","--surface"],["--muted","--background"],["--accent","--accent-soft"],["--secondary","--secondary-soft"],["--on-primary","--primary"]];
      return pairs.map(([fg,bg])=>{ const a=lum(css.getPropertyValue(fg)), b=lum(css.getPropertyValue(bg)); return (Math.max(a,b)+.05)/(Math.min(a,b)+.05); });
    });
    for (const ratio of contrast) expect(ratio).toBeGreaterThanOrEqual(4.5);
    const cta = page.getByRole("link", { name: "Explore Live Demo", exact: true });
    await expect(cta).toHaveCSS("color", "rgb(33, 41, 26)");
    await page.goto("/demo/workflows/billing");
    const approval = page.getByRole("button", { name: "Approve example", exact: true });
    await expect(approval).toBeDisabled(); await expect(approval).toHaveCSS("opacity", "1");
    expect(await approval.evaluate(el=>getComputedStyle(el).backgroundColor)).not.toBe("rgb(217, 237, 146)");
    await page.goto("/");
  }
});

test("design fonts are local and licensed; themes use explicit semantic tokens", async () => {
  const { readFileSync } = await import("node:fs");
  for (const font of ["SpaceGrotesk", "Manrope"]) {
    expect(readFileSync(`src/app/fonts/${font}-OFL.txt`, "utf8")).toContain("SIL OPEN FONT LICENSE Version 1.1");
    expect(readFileSync(`src/app/fonts/${font}-Variable.ttf`).length).toBeGreaterThan(10000);
  }
  const layout = readFileSync("src/app/layout.tsx", "utf8");
  expect(layout).toContain("next/font/local"); expect(layout).not.toContain("next/font/google");
  const css = readFileSync("src/app/design-system.css", "utf8");
  expect(css).toContain('--primary: #d9ed92'); expect(css).toContain('--background: #f5f4ee');
  expect(css).toContain('prefers-reduced-motion: reduce');
});

test("interactive product preview switches authored sources and destination", async ({ page }) => {
  await page.goto("/");
  const examples = page.getByRole("group", { name: "Product preview examples" });
  await examples.getByRole("button", { name: /Password reset link expired/ }).click();
  await expect(examples.getByRole("button", { name: /Password reset link expired/ })).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".showcase-source")).toContainText("Account Recovery Guide");
  await expect(page.locator(".showcase-source")).toContainText("Never share a password");
  await page.getByRole("link", { name: "Inspect this workflow" }).click();
  await expect(page).toHaveURL(/\/demo\/workflows\/account$/);
  await expect(page.getByRole("button", { name: "Approve example" })).toBeDisabled();
});

test("command search supports keyboard selection, empty results and focus return", async ({ page }) => {
  await page.goto("/demo");
  const trigger = page.getByRole("button", { name: "Search workspace" });
  await trigger.focus(); await page.keyboard.press("Control+k");
  const dialog = page.getByRole("dialog", { name: "Where would you like to go?" });
  await expect(dialog).toBeVisible();
  const input = dialog.getByLabel("Search pages, tickets and sources");
  await expect(input).toBeFocused(); await input.fill("no-match-xyz");
  await expect(dialog.getByRole("status")).toContainText("No matches");
  await input.fill("refund"); await page.keyboard.press("ArrowDown");
  await expect(dialog.locator('[data-active=true]')).toContainText("Refund Policy");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/demo\/knowledge\/refund$/);
  await expect(dialog).toHaveCount(0);
  await page.getByRole("button", { name: "Search workspace" }).click();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Search workspace" })).toBeFocused();
});

test("overview chart series, date window and exact values match synthetic records", async ({ page }) => {
  await page.goto("/demo");
  const chart = page.getByRole("region", { name: "The rhythm of support" });
  await expect(chart.locator(".chart-summary > strong")).toHaveText("8");
  await chart.getByRole("button", { name: "Resolutions", exact: true }).click();
  await expect(chart.getByRole("button", { name: "Resolutions", exact: true })).toHaveAttribute("aria-pressed", "true");
  await chart.getByText("View exact chart data", { exact: true }).click();
  const sum = await chart.locator("tbody td").evaluateAll(cells => cells.reduce((n,c) => n + Number(c.textContent), 0));
  expect(sum).toBe(3);
  await expect(chart.locator(".chart-summary > strong")).toHaveText(String(sum));
  await page.getByLabel("Overview period").selectOption("week");
  await expect(chart.locator("tbody tr")).toHaveCount(7);
  await chart.getByRole("button", { name: "Requests", exact: true }).click();
  const requests = await chart.locator("tbody td").evaluateAll(cells => cells.reduce((n,c) => n + Number(c.textContent), 0));
  await expect(chart.locator(".chart-summary > strong")).toHaveText(String(requests));
  expect(requests).toBeLessThan(8);
  await expect(page.getByRole("article", { name: "Support tickets" }).locator("strong")).toHaveText("8");
});

test("mobile drawer traps focus, searches and navigates without obscuring destinations", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/demo");
  const trigger = page.getByRole("button", { name: "Open navigation" });
  await trigger.click();
  const drawer = page.getByRole("dialog", { name: "Your workspace" });
  await expect(drawer).toBeVisible();
  for (let i=0;i<18;i++) { await page.keyboard.press("Tab"); expect(await drawer.evaluate(el=>el.contains(document.activeElement))).toBe(true); }
  await page.keyboard.press("Escape"); await expect(trigger).toBeFocused();
  await trigger.click(); await drawer.getByRole("button", { name: "Search workspace" }).click();
  const search = page.getByRole("dialog", { name: "Where would you like to go?" });
  await search.getByLabel("Search pages, tickets and sources").fill("analytics");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/demo\/analytics$/);
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Support intelligence" })).toBeVisible();
  await trigger.click(); await drawer.getByRole("link", { name: "Ticket inbox" }).click();
  await expect(page.getByRole("region", { name: "Ticket list" })).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("source filters, citation expansion and no-results recovery remain truthful", async ({ page }) => {
  await page.goto("/demo/knowledge");
  await page.getByRole("button", { name: "Used in examples", exact: true }).click();
  await expect(page.getByRole("region", { name: "Source results" }).getByRole("listitem")).toHaveCount(4);
  await page.getByText("Inspect this citation", { exact: true }).click();
  await expect(page.getByText(/Exact passage identifier: refund-1/)).toBeVisible();
  await page.getByLabel("Search documents").fill("nothing-matches-xyz");
  await expect(page.getByRole("heading", { name: "No matching documents" })).toBeVisible();
  await page.getByRole("button", { name: "Clear source filters" }).click();
  await expect(page.getByRole("region", { name: "Source results" }).getByRole("listitem")).toHaveCount(5);
});

test("search, creation and navigation dialogs pass accessibility checks in both themes", async ({ page }) => {
  for (const theme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: theme });
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/demo/tickets");
    for (const opener of ["Search workspace", "Create demo ticket"]) {
      await page.getByRole("button", { name: opener, exact: true }).click();
      await expect(page.getByRole("dialog")).toBeVisible();
      await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
      const violations = await page.evaluate(async () => {
        const axe = (window as unknown as { axe: { run: (options: object) => Promise<{ violations: { id: string }[] }> } }).axe;
        return (await axe.run({ runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] } })).violations.map(v=>v.id);
      });
      expect(violations, `${theme} ${opener}`).toEqual([]);
      await page.keyboard.press("Escape");
    }
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByRole("button", { name: "Open navigation" }).click();
    await expect(page.getByRole("dialog", { name: "Your workspace" })).toBeVisible();
    const violations = await page.evaluate(async () => {
      const axe = (window as unknown as { axe: { run: (options: object) => Promise<{ violations: { id: string }[] }> } }).axe;
      return (await axe.run({ runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] } })).violations.map(v=>v.id);
    });
    expect(violations, `${theme} drawer`).toEqual([]);
    await page.keyboard.press("Escape");
  }
});
