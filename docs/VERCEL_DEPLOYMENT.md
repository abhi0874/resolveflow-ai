# Vercel recruiter demo deployment

Step 15C completed: one production deployment is **READY** on the personal
`abhishesh1` Hobby workspace. Public demo:
https://resolveflow-ai-rosy.vercel.app/demo

Private source: https://github.com/abhi0874/resolveflow-ai, branch `main`.
Deployed commit: `be7efbcc0070d1e96b778011e7d6639b3293b407`.
Deployment: `dpl_ZjGM3VxtvSppKSeEoWrLWFk4xTk7`.
Only the standalone synthetic demo is hosted; no full backend or paid service was
provisioned. These documentation updates are local and unpushed, avoiding another
Git-triggered deployment.

## Verified deployment settings

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
Step 15C subsequently confirmed the hosted build and public HTTPS behavior with
these settings. Recheck support before a future runtime upgrade.

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

All demo assets, server rendering and interactions now run on Vercel/the visitor's browser without contacting the developer's laptop.
The visitor needs an internet connection. The full FastAPI/PostgreSQL/Valkey/LangGraph
system is not deployed by this configuration. Hosted browser checks blocked external origins and API requests and passed without
any attempted forbidden request. A physical MacBook-off test on a separate device
was not performed.

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

At the Step 14 audit Git had no commits or remote. Steps 15A–15B subsequently
created the reviewed history and private GitHub repository. Step 15C connected
that existing repository and completed the deployment described above.

## Step 15C hosted verification

Official CLI login completed securely after the connector could not access the
workspace. The target workspace plan was verified as active Hobby/no trial before
creation; no upgrade or paid feature was enabled. Project configuration includes
only the three nonsecret variables above. Outside-root source is disabled.

- Build and TypeScript completed successfully; Vercel reports READY.
- Homepage and `/demo`: HTTPS 200. Full API `/api/v1/auth/me`: 404.
- POST `/api/demo/generate`: 403, `demo_live_disabled`; no live provider request.
- HSTS, nosniff, DENY framing and same-origin referrer policy verified.
- Hosted browser smoke passed landing entry, tickets, search, status persistence,
  review, citations, analytics chart, reset and full-app redirects.
- Six demo views passed 390px and 320px layout checks with no overflow.
- No unexpected API/external requests or uncaught browser errors occurred.
- GitHub remains private. The deployment listing contains exactly one deployment.

[Vercel Authentication](https://vercel.com/docs/deployment-protection/methods-to-protect-deployments/vercel-authentication)
uses the standard `prod_deployment_urls_and_all_previews` setting. Generated
production deployment URLs and previews require authentication; the production
alias is public. No paid protection was added.

Existing nonfatal lint peer-range/optional install-hook warnings and the recorded
development-only audit findings remain. Vercel also warned about the package's
broad Node engines range; the project and deployment select 24.x. No application
or dependency change was necessary. Hosted checks are bounded smoke evidence,
not a load test, billing-ledger audit or continuous monitoring.

Future pushes to the linked production branch may trigger deployments. The two
completion documents remain local; no extra deployment was created for them.
Stop after Step 15C; do not proceed to Step 15D or enable live inference.
