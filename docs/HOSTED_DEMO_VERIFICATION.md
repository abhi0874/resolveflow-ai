# Hosted recruiter demo verification — Step 15D

Verification date: **2026-10-23, Asia/Kolkata**.
Verdict: **ready for recruiters as a clearly labeled synthetic demonstration**, with
nonblocking usability/documentation findings and cost-reporting limits below.
No functional release blocker found. No additional deployment is required by these results.

## Deployment and anonymous access

| Check | Actual result |
| --- | --- |
| Production URL | https://resolveflow-ai-rosy.vercel.app |
| Recruiter entry | https://resolveflow-ai-rosy.vercel.app/demo |
| Deployment | `dpl_ZjGM3VxtvSppKSeEoWrLWFk4xTk7` |
| Status/target | READY / production, freshly read from Vercel API |
| Source commit | `be7efbcc0070d1e96b778011e7d6639b3293b407` |
| Git source | GitHub `abhi0874/resolveflow-ai`, `main` |
| Repository visibility | GitHub API confirms private |
| Personal workspace | `abhishesh1`; active Hobby, no trial |
| Framework/root/runtime | Next.js / `apps/web` / Node 24.x |
| Public access | Fresh Chrome contexts, no saved cookies/storage/authentication; HTTPS works |
| Login requirement | No Vercel, GitHub or application login required at production alias |

Vercel API returned the actual production alias above. Protection configuration
remains `prod_deployment_urls_and_all_previews`; it was not changed. Generated
preview/deployment URLs are not the recommended recruiter entry URL.

## Method and results

Ran **eight hosted Playwright scenarios, all passed, zero retries**, against the
existing HTTPS deployment. An ignored copy of the existing browser scenarios was
adapted to the verified production origin; there was no local webServer configuration.
No application code changed. Tests used isolated browser-local synthetic state only.

| Recruiter interaction | Hosted evidence |
| --- | --- |
| Landing/navigation/Explore Demo | Public entry click reaches dashboard; bounded link crawl resolves more than 20 landing/demo paths with HTTP 200 and checks local fragment targets |
| Dashboard | Eight tickets and synthetic workspace render |
| Ticket inbox/search/filter | Refund search yields one row; combined filter shows empty state; clear restores results; approval-status filter yields two rows |
| Ticket details/editing | Change status and assignee, add escaped synthetic note, refresh preserves changes; create temporary ninth ticket |
| Knowledge/document search | Search “30 minutes” isolates recovery guide; open exact passage |
| Workflow examples | Replay reaches review; next-stage control advances; show-all works; all linked example pages resolve |
| Source citations | Refund citation navigates to exact passage containing 14-day policy |
| Human approval | Approval disabled until review; approved result survives refresh; abstention cannot be approved; revision/rejection record local decisions |
| Analytics | Eight initial tickets, nine after local creation; chart renders; date range without records shows empty state |
| Reset | Restores eight tickets; separate check confirms unrelated session-storage key survives |
| Architecture | Direct navigation and responsive rendering pass; clearly distinguishes hosted fixtures from full backend |
| Error/empty states | No matching tickets, empty analytics range, corrupt storage notice/recovery and safe unknown-ticket view pass |
| Direct entry/refresh | Deep links resolve in clean contexts; ticket/review reloads preserve same-tab state; full-app/login/register routes redirect to demo |

Separate hosted checks passed fresh-session isolation (new context retains original
fixtures after another context edits), refresh persistence, reset preserving other
storage keys, and touch taps on reset/navigation. Storage-denied behavior was not
separately injected in this step; corrupt-storage recovery was tested.

## Responsive and visual review

Checked six main demo views at **1440, 768, 390 and 320 CSS pixels**. Desktop default
1280px screenshot also inspected. Light desktop, dark responsive views and reduced
motion were covered. Document width matched viewport at each tested size.
Visually inspected desktop dashboard, tablet analytics, mobile tickets and workflow.
Typography, cards, navigation, chart rendering and vertically arranged workflow
stages remained usable. No full-page horizontal overflow or broken layout observed.

Nonblocking observations, with reproduction and proposed fixes only:

1. At 390px, several text links have small element rectangles: ticket-title links
   about 15px high, source citation 15px, “How it works” 19px. Native checkbox is
   13px but has an associated clickable text label. This is a touch-comfort finding,
   not a definitive WCAG failure: spacing/inline exceptions and label targets need
   separate assessment. Proposed follow-up: increase non-inline link padding/hit
   areas while retaining spacing and accessible labels. No CSS changed.
2. At 390px, `/demo/tickets` shows a horizontally scrollable table, with some columns
   initially offscreen. Measured container 348px, content 562px, successful 214px
   horizontal scroll. All columns remain reachable, but the scroll affordance is
   subtle. Proposed follow-up: add a small scroll hint or mobile card presentation.
3. Tablet analytics trend charts fit but are narrow in the two-column layout.
   A single-column breakpoint could improve readability; no clipping failure found.

Local screenshots (ignored evidence, not committed/uploaded):

- [Desktop dashboard](../.cache/verification/step15d/desktop.png)
- [Tablet analytics](../.cache/verification/step15d/768-_demo_analytics.png)
- [Mobile ticket table](../.cache/verification/step15d/390-_demo_tickets.png)
- [Mobile workflow](../.cache/verification/step15d/390-_demo_workflows_billing.png)
- [Mobile table after scroll](../.cache/verification/step15d/mobile-table-scrolled.png)

## Network, errors and MacBook independence

Browser fixtures rejected and recorded every attempted external-origin or `/api/`
request. All scenarios passed with none attempted. No uncaught exceptions, console
errors, unexpected HTTP errors or non-navigation network failures were recorded.
Navigation-cancelled `ERR_ABORTED` requests were excluded from failure assertions;
expected API rejections were checked separately through the HTTP test fixture.
No broken page/fragment links or missing assets were found in the bounded crawl.

A separate unblocked public-asset observation saw **61 unique responses**, scanning
**1,098,273 text bytes** across visited pages/assets. Its only browser request origin
was `https://resolveflow-ai-rosy.vercel.app`; browser cookie list was empty.
No localhost/127.0.0.1 calls, FastAPI, PostgreSQL, Redis/Valkey, Python workers,
LangGraph runtime or local-model dependencies appeared in the tested browser flows.
No local infrastructure was started or stopped. This verifies backend independence
of these journeys; **a physical MacBook-off test on an independent device/network
was not performed**. Internet and JavaScript remain required.

## Security review

- Public HTML/JS/CSS/component responses scanned for Google/GitHub token formats,
  private-key headers and credential-bearing PostgreSQL/Redis URLs: **zero matches**.
  No credential values were printed or retrieved for comparison.
- Project environment has only the three expected nonsecret settings:
  `NEXT_PUBLIC_APP_MODE=demo`, `DEMO_LIVE_AI_ENABLED=false`,
  `NEXT_TELEMETRY_DISABLED=1`. No Gemini/database/Redis/session secret is configured
  for this project. Outside-root source inclusion remains disabled.
- Reviewed authored fixture source and public examples: fictional Northstar Studio,
  eight tickets, five policy passages and five authored workflows. No private
  document/upload appeared in the inspected public content. No customer export is
  imported by this fixture module.
- Full API reads/writes for auth/workspace/document paths return 404, including a
  synthetic session-like cookie. Unsupported mutation probes return 404/405.
- Reserved live generation endpoint returns 403 `demo_live_disabled` for all four
  bounded synthetic payloads; no Gemini request was executed. These are rejection
  checks, not live inference tests. No unrestricted provider proxy found.
- Auth/full-app routes redirect into demo; no account creation or real session used.
- HSTS, nosniff, DENY framing and same-origin referrer policy passed; no X-Powered-By
  or Set-Cookie on checked public responses. Synthetic HTML-looking note remains
  escaped text and does not execute.

This is a bounded observable review, not proof that arbitrary unknown credentials
cannot exist anywhere, a full deployment archive audit, or a penetration-test
certification. CSP remains absent as previously documented. Prior five high
**development-only lint-chain** audit entries remain recorded; no fresh dependency
audit or package changes were performed in this verification-only step.

## Hosting cost findings

Fresh workspace response confirms billing **plan=hobby, status=active**, trial null
and invoiceItems null. Project uses basic build/standard function resources and
elastic build concurrency is disabled. Integration configuration listing returned
an empty list. No connected database/storage/AI integration or relevant secret is
present in the inspected project configuration, and browser journeys use none.
Project includes platform analytics identifiers, which alone do not prove a paid
subscription or instrumentation; no analytics request appeared in the browser scan.

The read-only billing-charge query for 2026-10-22 through 2026-10-24 returned
**404 “Costs not found”**. Therefore exact accrued charges, quota consumption and
remaining allowance were unavailable; a zero-dollar invoice is **not** claimed.
No paid add-on was evidenced for this project, no Pro/trial was active, and no
service/billing/environment/protection mutation was made. Account-wide unrelated
resources and any off-platform subscriptions were not audited. Hobby quotas and
personal/non-commercial eligibility remain applicable constraints.

## Remaining limitations and release decision

No functional recruiter blocker found; no redeployment required. Minor touch-target,
scroll-discovery and tablet-chart readability improvements are proposals only.
Older README, recruiter-demo and Step 14 readiness text still describe the historical
pre-deployment state; current status and this report supersede those statements.
A future authorized documentation cleanup can remove that ambiguity. Do not interpret
historical “not deployed” wording as current hosted status.

Real Safari/iOS/Android hardware, screen-reader/complete accessibility audit, load,
long-term uptime, detailed usage costs and physical MacBook-off acceptance were not
tested. The public demonstration is precomputed synthetic data, not live Gemini or
the full durable backend. No new deployment, commit, push, paid service, secret upload
or production-data mutation occurred. Stop after Step 15D.

## Step 16 local follow-up (not hosted evidence)

The touch-target and table discoverability observations above describe deployed
commit `be7efbc`. Local Step 16 changes enlarge targets, add a labeled keyboard-
scrollable table region/hint, improve tablet chart width and correct historical
wording. See [PORTFOLIO_READINESS.md](PORTFOLIO_READINESS.md) for local results.
No Step 16 deployment or new hosted verification was performed. Do not treat local
checks as evidence that production already contains these improvements.
