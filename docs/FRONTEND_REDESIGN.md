# Recruiter experience redesign — 2026-11-13

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
