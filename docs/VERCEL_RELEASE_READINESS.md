# Vercel release readiness — Step 14

Audited locally on 2026-10-22 (Asia/Kolkata). **VERIFIED LOCALLY; NOT YET VERIFIED
ON VERCEL.** Deployment preparation is complete with the residual risks below.
No repository publication, push, remote creation, Vercel linking, deployment,
account change, paid service or live Gemini call occurred.

## Deployment architecture and exact settings

Use the existing `apps/web` Next.js application. The landing page is prerendered;
the demo catch-all route uses Next.js server rendering and browser hydration.
This is not an `output: export` static site. Vercel supplies the Next.js runtime;
the browser holds the validated, bounded session journal. Ticket edits, authored
workflow replays and calculated analytics require no outbound API calls.

| Vercel setting | Required value |
| --- | --- |
| Plan | Hobby, only if this personal portfolio use is non-commercial and eligible |
| Framework preset | Next.js |
| Root Directory | `apps/web` (not the repository root) |
| Install Command | `npm ci` — include development dependencies needed to build |
| Build Command override | `npm run demo:build` |
| Output Directory | Framework default; leave override disabled |
| Node.js Version | `24.x` |
| Source outside Root Directory | Not required; leave inclusion disabled |
| Domain | Default Vercel HTTPS domain; no purchased domain |

The build script invokes the installed Next.js CLI with `build --webpack`, forcing
demo mode and disabled inference. Vercel's Next.js integration supplies serving;
do not configure the local port-3200 `demo:start` command as a hosting process.
No `vercel.json`, second frontend, Python install, migration, worker or storage
integration is required. `package.json`'s existing Node range includes 24; Vercel
currently resolves that range to its latest supported 24.x release. Recheck that
resolution before publishing because the range also permits newer local runtimes.

These settings were checked against official documentation on the audit date:
[framework support](https://vercel.com/docs/frameworks/full-stack/nextjs),
[monorepo roots](https://vercel.com/docs/monorepos),
[build/install/output settings](https://vercel.com/docs/builds/configure-a-build),
and [Node versions and range precedence](https://vercel.com/docs/functions/runtimes/node-js/node-js-versions).

## Environment allowlist

Set the first two variables for both Preview and Production, at build and runtime.
Changing the public mode requires a new build. The safe reference is
`apps/web/.env.demo.example`; no private environment file needs to be uploaded.

| Variable | Value | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_APP_MODE` | `demo` | Required public deployment mode |
| `DEMO_LIVE_AI_ENABLED` | `false` | Explicit disabled-inference setting; only false/unset is accepted |
| `NEXT_TELEMETRY_DISABLED` | `1` | Optional, recommended telemetry opt-out; demo build script already sets it |

Do **not** configure `GEMINI_API_KEY`, `AI_PROVIDER`, `RESOLVEFLOW_AI_MODEL`,
`API_INTERNAL_URL`, `NEXT_PUBLIC_API_BASE_URL`, database/broker URLs, session/auth
secrets, or any `NEXT_PUBLIC_*` credential. Do not copy `apps/api/.env` or private
data. No secret is needed. Public live generation cannot be enabled by a flag:
the reserved endpoint always returns 403 and never accesses keys or provider SDKs.
Future guarded inference requires separate implementation and approval as detailed
in [DEMO_SECURITY.md](DEMO_SECURITY.md).

## VERIFIED LOCALLY

| Check | Actual result |
| --- | --- |
| Demo production build | Passed on macOS ARM64, Node 24.22.1, Next.js 16.4.2, webpack |
| TypeScript | `npm --prefix apps/web run typecheck` passed |
| ESLint | `npm --prefix apps/web run lint` passed with zero warnings |
| Python lint/format | Ruff passed; 118 files already formatted |
| Demo suite | **13 passed in 10.8 seconds**, Chrome, one worker, zero retries |
| Navigation | Landing entry, bounded crawl of all reachable landing/demo links, valid same-page anchors and all demo sections passed |
| Interaction | Search/filter/edit/create/persist/reset, citations, workflow replay/review, computed analytics, empty/error states passed |
| Mobile | No horizontal overflow at 390px and 320px across six demo views; mobile screenshot inspected |
| Runtime isolation | Backend origins pointed at unreachable port 9; every browser flow fails on attempted API/external requests or uncaught page exceptions |
| Full-app routes | Login/register and all implemented protected page shapes reach `/demo`, including streamed redirects; external `next` query does not redirect off-origin |
| Internal endpoints | Full API reads/writes rejected before backend access; reserved live-generation POSTs return 403, including attempted parameter/key overrides |
| Output escaping | Synthetic script-like note remains text after reload; no script execution |
| Environment/data contracts | Invalid modes/live flags rejected; fixtures, citations, analytics, journal bounds, corrupt/blocked storage and review constraints pass |
| Headers | `nosniff`, frame `DENY`, same-origin referrer policy and production HSTS present; no X-Powered-By or session cookie on sampled demo responses |
| Runtime npm audit | **0 vulnerabilities** with `npm audit --omit=dev` |
| Full npm audit | **5 high entries in one development-only chain**, unresolved as described below |

The initial test run could not own port 3200 until the previously started,
verified project demo process and its remaining child were stopped. No unrelated
service was stopped. One new raw-HTTP redirect assertion failed because Next.js
can stream redirects in HTML; the final test verifies the actual browser URL and
rendered demo instead. All final assertions passed. The harmless Playwright
`NO_COLOR`/`FORCE_COLOR` environment warning remains.

Step 14 changed tests and documentation only; no application runtime, backend,
dependency or credential change was necessary. The Step 13 **269 backend / 26 full
application browser** results remain historical evidence, not reruns in this step.

### Secrets, source and bundle audit

- Git has **zero commits, zero tracked files and no configured remote**. There is
  no committed history in this checkout to remediate. Existing files remain
  untracked; no commit was created or history rewritten.
- The initial scan covered **263 Git-eligible files**, approximately 1.99 MB total.
  No file exceeded 5 MiB; largest was the 292,180-byte Python lockfile. The added
  readiness report is documentation, not a generated deployment artifact. A final
  scan of all **264** eligible files also found no checked credential matches; local
  Markdown links in the updated documentation resolved.
- High-signal Google/GitHub token and private-key pattern checks found no matches.
  Values of configured private key/secret/token/password variables of at least
  16 characters were read only in memory and checked for exact matches in candidate
  source and **136 generated server/static files**: no matches. No secret values
  were printed, copied, edited or uploaded.
- A synthetic `GEMINI_API_KEY` canary supplied during the build was absent from
  browser JavaScript. The audit does not claim arbitrary unknown secrets can be
  ruled out by pattern matching; inspect the staged diff again before a first push.
- Ignore rules were verified for actual API `.env`, frontend private environment
  files, `.local`, `.cache`, `.next`, dependencies, private data, models, uploads,
  backups and `.vercel`. Safe `.env*.example` templates and lockfiles remain eligible.
- Demo fixtures are authored TypeScript examples: eight tickets, three agents,
  five documents and five workflow scenarios. No real tenant source or export is
  imported. API/Python, local databases, private uploads and model caches do not
  occur in the generated dependency traces.
- **16 trace manifests** checked: largest file set **28,822,019 bytes**; deduplicated
  union **30,586,038 bytes**. Static assets **1,507,113 bytes**. No trace points
  outside `apps/web`, to `.env` files or to `braces`. These are local file-trace
  measurements, not a measured Vercel deployment/function archive.

### Residual security findings

The development-only chain is `eslint-config-next` → Next ESLint plugin →
`fast-glob` → `micromatch` → `braces`. The
[reviewed advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) reports
stack exhaustion for deeply nested patterns and no patched version. npm suggests
an incompatible downgrade to Next ESLint config 14.2.35; it was not applied.
Untrusted glob input must not reach lint tooling. Demo visitors do not invoke it,
and it is absent from runtime traces, but it remains a build/developer tooling
risk. Recheck advisories and review source/build changes before publication.

React text rendering and strict journal validation passed targeted XSS checks.
There is no Content-Security-Policy header yet; nonce-based CSP remains additional
defense-in-depth work, not a tested control. This focused audit is not a penetration
test or a production security certification. Do not enter private data in the demo.

## Hobby capacity and availability

Official [Hobby limits](https://vercel.com/docs/plans/hobby) currently include
100 GB fast data transfer, 10 GB fast origin transfer, one million CDN requests,
one million function invocations, four active CPU hours and 360 GB-hours provisioned
memory. Usage limits are finite and can pause service; no unlimited traffic or SLA
is promised. Hobby requires personal, non-commercial use. Confirm eligibility at
the publication gate; this audit does not inspect or change the user's Vercel account.

The [standard function limits](https://vercel.com/docs/functions/limitations) include
250 MB uncompressed Node.js bundles, 2 GB Hobby memory and a 300-second maximum
duration with Fluid compute. Local traces are comfortably smaller; actual hosted
bundling still needs verification. No long-running jobs or AI calls execute here.
Do not enable Pro, paid add-ons, storage, analytics integrations, trials, purchased
domains or large-function features for this demo. The full system's backend/ML
hosting requirements remain a separate unresolved scope.

## Reproduce the local release checks

Use Node 24 LTS. From the repository root, with any owned port-3200 demo stopped:

```bash
npm --prefix apps/web ci
GEMINI_API_KEY=resolveflow-server-only-test-canary-13 \
  API_INTERNAL_URL=http://127.0.0.1:9 \
  NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:9 \
  npm --prefix apps/web run demo:build
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
apps/api/.venv/bin/ruff check apps/api/src apps/api/tests apps/api/scripts
apps/api/.venv/bin/ruff format --check apps/api/src apps/api/tests apps/api/scripts
npm --prefix apps/web run test:demo
npm --prefix apps/web audit --omit=dev
npm --prefix apps/web audit
npm --prefix apps/web run demo:start
```

The canary is a deliberately fake test string; never substitute a real key.
The full audit currently exits nonzero for the documented development advisory.
`npm ci` is the locked installation command; the Step 14 checks used the already
installed locked dependencies, not a fresh Linux/Vercel installation. Build and
test full mode separately because both modes share `.next`.

## NOT YET VERIFIED ON VERCEL / remaining gates

No hosted URL, Linux build, Vercel function packaging, TLS/CDN behavior, real account
Hobby eligibility, platform quotas, public-origin navigation, MacBook-offline
acceptance or rollback has been tested. No deployment is claimed. Local demo
verification has no remaining functional failure; publication remains blocked on
explicit approval, a reviewed initial Git commit/remote and the hosted checks.

### Exact later deployment sequence — requires new authorization

1. Confirm eligible Hobby use and explicitly authorize repository destination,
   visibility and publication/deployment. Review the remaining lint advisory.
2. Review the complete initial staged source diff, templates and lockfiles, rerun
   secret/dependency checks, and create an initial commit. Add only the approved
   remote and push only after authorization. Never force-add ignored private files.
3. Import that repository into an approved Hobby project; select `apps/web`, Next.js,
   Node 24.x, `npm ci`, `npm run demo:build`, and default output. Keep outside-root
   source inclusion disabled. Configure only the environment allowlist above for
   Preview/Production. Do not import private local environment files.
4. After deployment approval, trigger the initial build and check its Node version,
   dependency install, output size and logs. Do not accept a fallback full-mode build.
   Git-linked future pushes can trigger deployments automatically; review that setting.
5. Test the HTTPS URL from a device/network independent of the MacBook: landing/demo,
   tickets, citations, replays, analytics, reset and mobile navigation. Verify no
   localhost/private-service requests; full API returns 404, live generation 403,
   full-app routes lead to demo, and expected security headers are present.
6. Record actual hosted evidence and inspect included usage. If acceptance fails,
   stop publication/promotion and disable the failed deployment; there is no previous
   deployment to roll back to on a first release. Never fix a capacity issue by billing
   or enabling live AI without separate approval.

**Stop after Step 14. Step 15/public deployment is not authorized.**
