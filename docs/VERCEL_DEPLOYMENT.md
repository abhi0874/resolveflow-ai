# Vercel deployment preparation — not deployed

Steps 13–14 prepare and locally verify only the self-contained Next.js demo. Public deployment, project
linking, account changes and publication require a later explicit instruction.
No Vercel project, domain, database or paid service was provisioned.

## Build settings for later approved deployment

| Setting | Value |
| --- | --- |
| Framework | Next.js |
| Repository root directory setting | `apps/web` |
| Install command | `npm ci` |
| Build command | `npm run demo:build` |
| Output directory | Next.js default; do not override |
| Node.js | 24.x LTS |
| Public mode | `NEXT_PUBLIC_APP_MODE=demo` at build and runtime |
| Live inference | `DEMO_LIVE_AI_ENABLED=false` |
| Optional telemetry opt-out | `NEXT_TELEMETRY_DISABLED=1` |
| Include source outside root | Leave disabled; no outside-root build dependency |
| Domain | Default Vercel HTTPS domain; no custom domain needed |

The monorepo stays intact; Vercel needs only `apps/web` and its package-lock.json.
No Python dependency installation, migration, worker, filesystem upload directory or
backend URL belongs in this demo deployment. `next.config.ts` retains security headers.
No Vercel-specific dependency or configuration file is required for framework detection.
The existing engines range includes Node 24; local production build and demo browser
verification used the official checksum-verified Node 24.22.1 runtime.

Official references checked during preparation:
[Vercel Next.js support](https://vercel.com/docs/frameworks/full-stack/nextjs),
[monorepo root configuration](https://vercel.com/docs/monorepos),
[Node runtime versions](https://vercel.com/docs/functions/runtimes/node-js/node-js-versions).
Recheck platform/runtime support at the later deployment gate. This local compatibility
check does not claim a successful Vercel build or a publicly tested URL.

## Environment and secrets

Use `.env.demo.example` as a safe reference, not as a replacement for existing private
files. The demo needs no secret. Do not copy `apps/api/.env`, production session
credentials, Gemini keys, database URLs or broker credentials into Vercel.
`NEXT_PUBLIC_APP_MODE` contains only a public enum. It is compiled into browser/server
builds; changing it requires rebuilding. The start script also sets the same mode.
The real application's provider/model settings remain in the API project.

## Cost and availability boundary

Vercel's [Hobby plan](https://vercel.com/docs/plans/hobby) is restricted to eligible
personal, non-commercial use. Confirm the portfolio qualifies before publication.
Included quotas are finite; exceeding them can pause service. There is no promise
of unlimited free traffic, commercial eligibility or an availability SLA. Do not enable
billing, upgrades, marketplace integrations, analytics add-ons or custom domains.

After a later approved deployment, all demo assets, server rendering and interactions
will run on Vercel/the visitor's browser without contacting the developer's laptop.
The visitor needs an internet connection. The full FastAPI/PostgreSQL/Valkey/LangGraph
system is not deployed by this configuration. A MacBook-offline hosted acceptance
check can only occur after deployment; it is not falsely claimed here.

## Local release check

```bash
npm --prefix apps/web ci
npm --prefix apps/web run demo:build
npm --prefix apps/web run test:demo
npm --prefix apps/web run demo:start
```

Visit `/demo`, browse tickets, change status, inspect citations, review an example,
check analytics and reset. Tests make the backend unreachable to the demo. Check
`/api/v1/auth/me` returns 404 and `POST /api/demo/generate` returns 403. Do not run a
live AI test. Stop the local server with Ctrl-C. No deployment command is part of
Steps 13–14. The reviewed source and lockfile are the portable artifact; `.next` is a
local generated build, not a portable deployment archive.


## Step 14 release evidence and approval gate

The settings above were rechecked against official Vercel documentation on
2026-10-22, including [build configuration](https://vercel.com/docs/builds/configure-a-build).
Set demo mode and disabled live inference in both Preview and Production. Do not
set `API_INTERNAL_URL` or `NEXT_PUBLIC_API_BASE_URL`: no backend belongs in this
project. Vercel serves Next.js directly; the loopback `demo:start` script is local only.

The [release readiness report](VERCEL_RELEASE_READINESS.md) contains the exact
publication sequence, environment allowlist, bundle measurements, audit findings
and **13 passing local demo checks**. Local production build, TypeScript, ESLint
and Ruff also passed. The runtime dependency audit is clean; five high entries in
one development-only lint chain remain unresolved, with no patched version listed.
No runtime/dependency/configuration change was needed for compatibility.

At the Step 14 audit Git had no commits or remote. Step 15A records the reviewed
initial local commit; approved repository publication and explicit deployment
authorization remain prerequisites. No remote is configured. Do not run
Vercel linking/import/deployment commands during Step 14. Actual platform build,
function packaging, public HTTPS behavior, quota/eligibility and MacBook-offline
acceptance remain **NOT YET VERIFIED ON VERCEL**. Stop before Step 15.
