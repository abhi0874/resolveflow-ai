# Recruiter experience redesign — 2026-11-13

> Current boundary: the final structural revision below is local and uncommitted.
> Earlier publication plans in this historical record are superseded; await visual
> approval and separate publication authorization.

This release starts from the approved standalone demo commit
`3717f6e3285de664834a5dc0eee2059cfe639fd1`, not the older ML research frontend.
The user authorized a complete frontend redesign, a protected Preview, then
publication to the existing Hobby project after acceptance passes.

## Design and behavior

- Graphite dark surfaces, ivory light surfaces, an ink navigation rail, warm lime
  primary actions and muted lavender evidence/review cards.
- Locally served variable Space Grotesk headings and Manrope interface text through
  `next/font/local` (font-display swap, preloading and fallback metrics). Both
  upstream fonts are SIL OFL 1.1; copyright/license files accompany the binaries.
  Sources: [Space Grotesk](https://github.com/google/fonts/tree/main/ofl/spacegrotesk)
  and [Manrope](https://github.com/google/fonts/tree/main/ofl/manrope).
- System theme on first visit; explicit Light/Dark/System preferences persist,
  follow system changes in System mode and synchronize across tabs. Storage
  denial keeps the interface usable. Early local script avoids a preference flash.
- Editorial landing with a bounded, animated workflow illustration; workspace
  overview with counts, inbox and a status chart computed from synthetic records.
  Shared styles cover tickets, documents, source citations, workflow stages,
  draft comparison, review, analytics and the technical case study.
- No new animation library. Finite opacity/transform entrances, hover/press states,
  chart growth and theme transitions; reduced motion removes animation while
  keeping controls and replay functional.
- Existing editing, filtering, session persistence/reset, keyword search, exact
  source links, bounded replay, review confirmation and abstention behavior remain.
  No backend, fixture/model result, provider or deployment security setting changed.

## Local acceptance

Node 24.22.1: production demo build, TypeScript and ESLint passed. **23/23** demo
checks passed, zero retries. Existing functional/security assertions retained;
obsolete exact-red/default-dark design expectations replaced with tests for the
new palette, equivalent contrast/navigation checks and explicit system preference.
Axe waits for finite entrance animations before inspecting final rendered contrast.

Seven screens × two themes × desktop/mobile = **28 screenshots** and WCAG 2.0/2.1
A/AA scans: zero automated violations, overflow, console errors or unexpected
network requests. Screens: landing, overview, tickets, knowledge, workflow/review,
analytics and engineering. Existing tests additionally check 320/390/768/1024/1440px
layouts, keyboard/skip links, table scrolling, modal focus, reduced motion, links,
CSP negative tests, forbidden API routes and disabled generation.

First-pass findings were corrected: shared Brand had a fragment-only home link,
light approach copy inherited an unsuitable fixed color, and accessibility capture
ran before finite entrance animations ended. Two source-only checks were initially
run from the wrong directory; the final run uses `apps/web` and passes both.

Local evidence: `.cache/redesign/` (ignored). `tests-final.log`, `results.json`,
`results.xml`, `visual-results.json`, build/lint/type logs and screenshot PNGs.
This is bounded Chromium QA, not full WCAG certification, physical-device testing,
commercial readiness or an uptime guarantee.

## Release controls

Existing Vercel `resolveflow-ai` project: Hobby, Next.js, root `apps/web`, Node 24.x,
`npm ci`, `npm run demo:build`; production branch `main`. Only three nonsecret
variables exist: demo mode, live AI false and telemetry opt-out. Protected Preview
and Toolbar Off remain unchanged. Gemini is never invoked by this release.

GitHub currently reports `abhi0874/resolveflow-ai` as **PUBLIC**, unlike older
private-repository handoff records. Visibility was not changed by this task.
Only reviewed frontend, font licenses, tests and documentation will be pushed.
No credentials, research changes, models, backup data or ignored build output belong
in the release. The old deployment `dpl_HryX1dAKZfXVQAGgrdY3Q1nfcawt` and commit
`3717f6e...` remain the rollback reference. Preview acceptance must pass before
updating the production branch. Record actual deployment results in the local
completion record; do not create an extra deployment merely to publish its ID.


## Final structural revision — local only, 2026-11-13

### Structural changes

| Area | Previous layout | Final composition |
| --- | --- | --- |
| Landing | Split hero and small illustration, feature cards | Centered editorial headline, subtle grid/glow, interactive wide inbox preview, alternating product chapters |
| Overview | General dashboard cards | Navigation rail, activity canvas with four compact counts, separate review queue/decisions/context column |
| Tickets | Filter form above a table, separate detail page | Conversation list, request/internal-note pane, intelligence/assignment pane; selected mobile routes switch panes |
| Knowledge | Search followed by document cards | Prominent keyword search, source filter, numbered results and source reader with expandable citation provenance |
| Workflows | Repeated cards and horizontal stages | Scenario runway, persistent vertical pipeline, stage-specific context, source evidence beside a focused draft review desk |
| Analytics | Shared full-application dashboard | Date-filter bar, metric strip, interactive activity canvas, distributions, review outcomes, explicit measurement notes |
| Engineering | Generic card arrangement | Chapter navigation, sequential architecture diagram, local/hosted boundaries, unchanged evaluation evidence and limitations |

The available brief provided the black/lime, ivory/lavender and restrained-gradient
visual direction in text. No reference bitmap was available in the attachment directory;
no pixel-match claim is made. Before screenshots of the previous design are retained
and compared directly with the actual final browser captures.

### Working interactions and safeguards

- Command/Ctrl+K opens search across pages, synthetic tickets and sources; arrow keys,
  Enter, Escape, no-result recovery, announced selection and focus return work.
- A mobile native navigation drawer contains keyboard focus and closes on destination
  selection. Nested search and ticket-creation dialogs use the same focus lifecycle.
- Dashboard period and chart-series controls recompute actual fixture counts; exact
  data tables remain available. Analytics retains explicit date cohorts/denominators,
  empty-state recovery and detailed unavailable operational measurements.
- Inbox filtering, selection, original assignees, status, escaped notes, synthetic ticket
  creation, persistence and reset remain connected to the unchanged demo data source.
- Source filtering and expandable citations use authored passages. The UI explicitly
  describes browser keyword search, not hosted semantic inference.
- Replay is a bounded authored sequence. Exact-draft acknowledgement is still required;
  unsupported/abstained examples cannot be approved. Decisions persist locally; no
  customer message or external action occurs.
- CSS-only bounded motion respects reduced-motion preferences. No new dependency,
  remote font, model, AI request, API connection or paid service was introduced.

### Verification and correction record

Final Node 24.22.1 demo build, TypeScript and ESLint: passed. Final Playwright run:
**29 passed / 0 failed / 0 skipped, retries 0, 29.0s**. The original functional and
security assertions remain. Obsolete table/heading/navigation selectors were adapted
to the authorized new structure, retaining equivalent count, keyboard, focus, contrast,
viewport and journey checks; security and abstention assertions were not relaxed.

Six focused interaction tests were added. Initial runs caught an omitted original
assignee, native-dialog initial-focus/wrapping behavior, and stale navigation assumptions
in tests. Shared fixture assignees were restored; modal focus management was corrected;
route transitions are now explicitly awaited. Visual review corrected inherited serif
heading accents, sidebar gaps and legacy anchor styles that distorted the new panes.
Initial failures and final passing evidence remain in the local report directory.

Nine screens × three viewports × two themes = **54 full screenshots and automated
accessibility scans**, with zero WCAG 2.0/2.1 A/AA violations, document overflow,
console/page errors or unexpected/failed network requests. Screens include both the
workflow library and review workspace, plus ticket list/detail. Dialog accessibility
is separately checked in both themes. Contact sheets and landing/overview/inbox
before-after comparisons were visually reviewed. The designs have different geometry,
content ordering and interaction structure from the previous release.

Evidence location: `.cache/structural-redesign/`. `accepted/visual-results.json` contains
the 54 sample results; `accepted/*.png` are full captures; `review-*.png` are contact
sheets; `comparison-*.png` show previous/new composition; `final/results.{json,xml}`
contains tests. `evidence-sha256.json` and `source-sha256.json` identify this local state.
`research-preservation.json` confirms 619 original research source hashes unchanged.

### Review and boundaries

Open http://127.0.0.1:3200/ while the local server is running. Use the Light/Dark/System
control; explore the inbox, source library, replay and review, then reset local changes.
The working tree intentionally contains this revision; no commit, push, merge or
Vercel operation was performed. Public deployment remains the existing release.
The local ignored dependency symlink is development setup, not a release file.

This review does not certify every assistive technology, Safari/Firefox or physical
device, and it does not verify a new hosted release. User visual approval is the next
boundary. Do not publish, deploy, or enable live inference automatically.
