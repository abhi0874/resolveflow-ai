# Project status

Updated: 2026-10-23 (Asia/Kolkata).

**Steps 1–17A are complete locally; the reviewed release is not pushed or deployed.** The standalone synthetic recruiter
demo is deployed on Vercel Hobby. GitHub remains private; the full backend and
live Gemini inference remain disabled for this deployment.

## Step 17A — local release security gate, 2026-10-23

- Reviewed all pending Step 15C–16 source/docs and preserved synthetic demo isolation.
  Added production-demo-only CSP in Next.js config; same-origin network/scripts,
  no plugins/frames/workers/base changes, no eval, inline event handlers blocked.
  Inline script/style compatibility remains necessary: this is not strict nonce CSP.
- Production build and **16 demo tests passed** with CSP active, including direct
  browser enforcement, existing UI/reset/review behavior, light/dark accessibility,
  keyboard/table scrolling, target sizes and four-width layouts. No normal-flow
  console/uncaught/network errors. TypeScript, ESLint and Ruff lint/format passed.
- Fresh full npm audit: five high dev-only lint-chain entries; runtime audit zero.
  No compatible patched braces release; breaking downgrade rejected. All affected
  packages absent from 16 production traces. No dependency changes.
- Credential patterns: no findings in 266 candidate files; exact configured-secret
  comparison found none in candidates or 282 history blobs. Ignore cases passed;
  credentials/private data were not printed, staged or modified.
- Release identifier: Step 17A, subject `chore: polish recruiter demo and harden release`,
  parent `be7efbc`. The resulting hash is reported after commit and can be resolved
  with the command in PORTFOLIO_READINESS.md; a commit cannot include its own hash.
- Local release only: no push, remote configuration change, deployment, paid service
  or Gemini request. Live site remains on `be7efbc`. Vercel CSP verification waits
  for a separately approved deployment. Ready to push only after that authorization.

## Step 16 — local UI polish and portfolio review, 2026-10-23

- Enlarged demo links/buttons/disclosures and landing header targets; improved
  checkbox target, keyboard skip/focus behavior, table region/column semantics
  and visible scroll instructions. Tablet demo analytics uses wider stacked charts.
- Overview suggests a concise workflow-first tour. Architecture and documentation
  distinguish live Vercel synthetic demo from the implemented local full backend.
- Local production build, TypeScript and ESLint passed; Ruff lint/format passed
  (118 files). **15 demo checks passed**, including all existing interactions and
  new keyboard, target-dimension, four-width layout, contrast and axe-core checks.
  Five key pages in light/dark had zero tested WCAG A/AA violations. Local mobile
  and tablet screenshots inspected. No screen-reader/real-device certification.
- New keyboard test was synchronized with hydration and contrast helper corrected
  for shorthand hex colors; assertions were preserved. No app regression remained.
- No dependency, credential, backend, provider, worker or production configuration
  change. Gemini disabled, no live calls. No commit, push or Vercel deployment.
- Ready for reviewed commit and separately authorized redeployment. Hosted commit
  remains `be7efbc`; local evidence does not certify production has this polish.
  Prior local documentation edits remain preserved. See
  [PORTFOLIO_READINESS.md](PORTFOLIO_READINESS.md) for files, evidence and limits.

## Step 15D — independent hosted verification, 2026-10-23

- Existing production alias https://resolveflow-ai-rosy.vercel.app/demo independently
  verified anonymously in fresh Chrome contexts. Vercel reports READY for exact
  `be7efbcc0070d1e96b778011e7d6639b3293b407`; GitHub remains private.
- Eight hosted browser scenarios passed (zero retries), covering actual edits,
  search/filter, documents, workflow replay/review safeguards, citations, analytics,
  reset, error states, redirects and bounded navigation crawl. Separate touch,
  fresh-session isolation and selective-reset checks passed.
- Desktop/tablet/mobile checks at 1440/768/390/320px passed page-width assertions.
  No console errors, uncaught exceptions, unexpected API/external requests or
  non-navigation network failures were found. Backend independence verified for
  tested flows; physical MacBook-off acceptance remains unperformed.
- Public asset scan observed 61 responses / 1,098,273 text bytes with no tested
  credential-pattern matches. Full API rejected, live generation disabled; no
  Gemini requests. Security review is bounded, not an exhaustive certification.
- Active Hobby/no trial reconfirmed; integration list empty. Billing charge API
  returned 404 “Costs not found”, so exact cost/usage totals are unverified.
- Ready for recruiters with nonblocking small text-link touch targets, subtle mobile
  table scrolling, narrow tablet charts and historical documentation wording.
  No code fix or redeployment required by these results. Existing dev-only audit
  findings and absent CSP remain documented limitations.
- Created [HOSTED_DEMO_VERIFICATION.md](HOSTED_DEMO_VERIFICATION.md), including
  evidence, reproduction details and proposed improvements. Documentation remains
  local and uncommitted/unpushed; previous Step 15C edits are preserved.
  No deployment/configuration/protection changes or paid services were made.

## Step 15C — hosted recruiter demo verified

- Public demo: https://resolveflow-ai-rosy.vercel.app/demo
- Project `resolveflow-ai` in the personal `abhishesh1` workspace; authenticated
  owner and workspace active Hobby plan/no trial verified before creation.
  The connector scope error was resolved by user-completed official CLI login.
  No authentication credential was printed or added to source control.
- One production deployment: `dpl_ZjGM3VxtvSppKSeEoWrLWFk4xTk7`, **READY**.
  Built private GitHub `abhi0874/resolveflow-ai`, branch `main`, exact commit
  `be7efbcc0070d1e96b778011e7d6639b3293b407`. Deployment listing confirms one
  deployment. GitHub API recheck confirms private visibility and default main.
- Verified settings: Next.js, root `apps/web`, Node 24.x, `npm ci`,
  `npm run demo:build`, default output, outside-root source disabled.
  Exactly three configured variables: `NEXT_PUBLIC_APP_MODE=demo`,
  `DEMO_LIVE_AI_ENABLED=false`, `NEXT_TELEMETRY_DISABLED=1`.
  No Gemini key, database credential or backend URL was configured in Vercel.
- Hosted build succeeded, including TypeScript. Nonfatal npm lint peer-range and
  optional install-hook warnings remain; no dependency changes were needed.
  The broad package Node engines range also produced an upgrade warning;
  the deployed project/runtime selection is explicitly 24.x.
- Public HTTPS checks: homepage and `/demo` 200; `/api/v1/auth/me` 404;
  POST `/api/demo/generate` 403 with `demo_live_disabled`. Responses include
  HSTS, nosniff, DENY framing and same-origin referrer policy.
- Hosted Playwright smoke passed: landing entry, synthetic tickets, search,
  status persistence, review, citation navigation, analytics chart, reset,
  full-app redirects, and six demo views at both 390px and 320px without overflow.
  External-origin and API requests were blocked during this browser test:
  zero attempted forbidden requests and zero uncaught browser errors.
  This establishes no local-backend dependency in the tested journeys;
  a separate physical MacBook-off/independent-device test was not performed.
- Standard Vercel Authentication protects generated production deployment URLs
  and previews; the production alias is public for recruiters. No paid protection,
  upgrade, marketplace purchase, custom domain or backend infrastructure was enabled.
  No Gemini request was made. Hobby quotas remain finite; no billing-ledger audit
  or continuous production monitoring is claimed.
- Only the status and deployment documentation changed locally. They are not
  included in the deployed commit and remain unpushed to avoid another Git-triggered
  build. No runtime code changed; no local regression suite was rerun.

Stop after Step 15C. Step 15D and any further deployment or live AI use require
separate authorization. See [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md).

## Step 15B — private GitHub publication, 2026-10-22

- Repository: https://github.com/abhi0874/resolveflow-ai
- Visibility: **PRIVATE**, confirmed by GitHub API (`private=true`,
  `visibility=private`). Owner `abhi0874` is the authenticated personal User account,
  not an organization. The name was checked before creation and returned 404;
  a new empty private repository was created without README or duplicate history.
- Branch: `main`, tracking `origin/main`. Remote:
  `https://github.com/abhi0874/resolveflow-ai.git`.
- Initial pushed code commit: `5d6d203666abcdd64afbdf069f22295755ba2036`.
  GitHub's branch endpoint confirmed that exact SHA after the first push.
  This status entry is a subsequent documentation-only commit on the same branch;
  its resulting SHA is reported in the completion message and is available with
  `git rev-parse origin/main`. No force-push or history rewrite is used.
- Before upload: clean working tree, expected commit, no existing remote, and
  all 264 file versions in reachable history scanned again for credential patterns,
  exact configured private secrets and forbidden paths. No findings. Only safe
  environment templates are tracked; local secrets, services/data, uploads, models,
  virtualenvs, dependencies and generated outputs remain excluded and preserved.
- After upload: recursive GitHub tree was not truncated; all **264 file paths,
  modes and blob hashes matched the reviewed local commit**. Working tree was clean.
  This proves the uploaded tree is the audited tree, not a claim that heuristic
  scanning can identify every possible unknown secret.
- Access verification: collaborator list contained only `abhi0874` with admin
  role; zero pending invitations. No collaborators, public visibility, paid
  features, Actions purchases or infrastructure were enabled.
- GitHub CLI was installed. Sandboxed authentication initially failed, but a
  normal network/keychain-access check confirmed the existing personal account;
  no interactive login or token disclosure was needed. Git used the existing CLI
  credential helper only for the push command, without global credential changes.
- Live demo inference remains disabled and needs no Gemini key. No application
  code/configuration changed, so prior Step 14 tests were not rerun. The documented
  development-only lint advisory remains open; no breaking dependency changes.

The documentation update is reviewed, committed and pushed after the initial code
upload; final verification checks GitHub main against local HEAD and confirms a
clean worktree and private visibility. The final commit cannot contain its own SHA;
the explicit SHA above identifies the verified initial code snapshot, while the
completion report identifies the final pushed documentation revision.

Ready for a separately authorized Vercel integration step. Hobby eligibility,
hosted build/function behavior and independent-device acceptance remain unverified.
Stop after Step 15B: do not connect Vercel, deploy, enable billing or activate live AI.

## Step 15A — local Git publication preparation, 2026-10-22

Repository review:

- Existing branch `main` preserved. At review start: no commits, no tracked/index
  entries, no reflog entries and no configured remote. There was no reachable
  committed credential history to remediate. No existing history was overwritten.
- Reviewed all **264 intended project files** (about 2.01 MB): source, migrations,
  tests, safe templates, lockfiles, documentation, synthetic evaluation datasets
  and infrastructure scripts. No binary files, symlinks or files above 5 MiB
  were included. Local services, development records and private keys are preserved.
- Verified **21 exclusion cases** covering private `.env` files, credential
  directories/key files, local databases, model caches, node_modules, virtualenvs,
  build outputs, logs, uploads, private data and deployment metadata. Existing
  `.gitignore` was sufficient; safe `.env*.example` templates remain included.
- Scanned all candidate contents for Google/GitHub/AWS/Slack credential patterns,
  private-key headers and exact configured private secrets/passwords of at least
  16 characters (including URL passwords). No matches. Literal password-like
  assignments are synthetic test values; environment templates use placeholders.
  Secret values were never printed. These targeted checks are not proof against
  every possible unknown credential; repeat review before publication.
- Demo fixtures and evaluation corpus provenance remain synthetic. No tenant export,
  upload, database dump, generated model or private environment enters this snapshot.

Dependency review (local evidence only):

| Package | Locked version | Exposure |
| --- | --- | --- |
| `eslint-config-next` | 16.4.2 | Development lint configuration |
| `@next/eslint-plugin-next` | 16.4.2 | Development lint plugin |
| `fast-glob` | 3.3.1 | Transitive lint file discovery |
| `micromatch` | 4.0.8 | Transitive lint glob matching |
| `braces` | 3.0.3 | Underlying nested-pattern stack-exhaustion advisory |

All five are marked development-only in the lockfile and absent from all **16**
existing production trace manifests. Demo requests do not invoke the lint pipeline;
untrusted source/glob input during development/build remains the exposure. Reviewed
same-day Step 14 saved audit: runtime **0**, full **5 high entries in one chain**.
The recorded advisory has no patched version; npm's suggested Next lint configuration
14.2.35 downgrade is incompatible. No dependency was changed to silence the audit.
No new registry/advisory/network query was made in this local-only step; the result
is a review of the recorded audit, not a freshly fetched advisory assessment.

Confirmed configuration:

- Next.js; Vercel root `apps/web`; Node `24.x`; install `npm ci`; build
  `npm run demo:build`; framework-default output.
- `NEXT_PUBLIC_APP_MODE=demo`, `DEMO_LIVE_AI_ENABLED=false`; telemetry opt-out optional.
  The build script forces demo/disabled inference. The reserved generation route
  returns 403 without key access or outbound requests. No `GEMINI_API_KEY` needed.
- Step 14's build, 13 demo tests, TypeScript/ESLint and Ruff results remain valid
  historical evidence; no runtime code changed or application tests rerun in 15A.

Commit and publication boundary:

- User supplied the commit email; use it with the locally detected author name
  for this commit only. Do not change global Git identity. Review the exact index
  contents against the audited files before committing.
- Exact Git index verified against all 264 reviewed files; staged whitespace check
  passed. This initial local commit contains only those files. The final response
  reports the resulting commit ID after Git completes. No GitHub repository, remote,
  push, Vercel connection, paid service or
  live Gemini request is authorized. Private publication needs a separate explicit
  instruction naming the intended account/repository. Stop after Step 15A.

## Step 14 — Vercel release preparation, 2026-10-22

Completed:

- Verified official Vercel Next.js/monorepo/build/Node/Hobby documentation: root
  `apps/web`, install `npm ci`, build `npm run demo:build`, default output, Node 24.x,
  demo mode and disabled inference. No new runtime dependency/config was needed.
- Added browser assertions for attempted API/external requests and uncaught errors
  across every demo flow; added complete reachable-link traversal, security header
  checks and browser redirects from implemented full-app routes.
- Corrected documentation that still implied the synthetic recruiter demo needed
  hosted Python/database/workers. The full application's architecture is preserved.
- Created [VERCEL_RELEASE_READINESS.md](VERCEL_RELEASE_READINESS.md) with environment
  allowlist, audit scope/findings, actual measurements, official references,
  remaining gates and exact later deployment instructions.

Actual verification:

- Demo production build passed under Node **24.22.1** with a fake secret canary and
  unreachable backend configuration. **13 demo tests passed in 10.8 seconds**,
  one Chrome worker, zero retries. Navigation, mobile 390px/320px, edits/reset,
  workflow examples, citations, analytics, error/empty states, escaping, storage,
  environment validation and blocked live/full API access passed.
- TypeScript and ESLint passed; Ruff passed and **118 files** passed format checks.
  Step 13's 269 backend/26 full browser results are historical, not rerun here:
  Step 14 changed only tests and documentation.
- Runtime npm audit: **0 vulnerabilities**. Full audit: **5 high entries in one
  development-only braces/glob/Next ESLint chain**; no patched version listed.
  No incompatible tooling downgrade was applied. The affected package is absent
  from traced server dependencies. See the report for remaining build-time risk.
- Initial 263 Git-eligible source files scanned; no checked credential pattern or
  configured private secret match found; final 264-file scan also passed. 136 generated static/server files also
  had no configured-secret match; browser bundles lacked the synthetic key canary.
  No keys were displayed or modified. Ignore rules cover credentials, local data,
  generated files and model caches. Git has **0 commits, 0 tracked files, no remote**.
- 16 dependency traces inspected: largest 28,822,019 bytes; unique union 30,586,038
  bytes; static assets 1,507,113 bytes. No private environment/backend files or
  dependencies outside `apps/web` appeared. Hosted artifact size is not yet measured.
- The initial test harness found the existing project demo occupying port 3200;
  only its verified parent/child processes were stopped. A raw-HTTP redirect test
  was corrected to follow Next.js streamed redirects in the browser. Final tests
  passed without weakening the redirect requirement. Unrelated services/data intact.

Remaining gates:

- **VERIFIED LOCALLY; NOT YET VERIFIED ON VERCEL.** Explicit authorization,
  reviewed initial Git commit/remote/publication, Hobby eligibility confirmation,
  hosted Linux build/function packaging, HTTPS/CDN checks and MacBook-offline
  acceptance remain outstanding. No hosted service or real AI inference is enabled.
- The development lint advisory remains open; CSP is not implemented. This focused
  audit is not a production security certification or guarantee of zero unknown secrets.
- Local demo restored at `http://127.0.0.1:3200/demo`; backend services are not required.
- Stop after Step 14. **Do not proceed to Step 15 or deploy without new approval.**

## Step 13 — recruiter demo preparation, 2026-10-22

Implemented:

- Public `/demo` with overview, searchable/filterable tickets, temporary ticket
  creation, assignment/status/notes/history, document keyword search and exact
  passage links. Reset clears only the validated bounded demo session journal.
- Eight authored tickets, three synthetic agents, five policy documents/passages
  and five workflow examples covering billing, technical issues, account recovery,
  insufficient evidence and human escalation. No private records were exported.
- Clearly labeled authored seven-stage replays, immutable input/draft, citation
  inspection and local human decisions; abstentions cannot be approved. These
  fixtures are not presented as captured Gemini output or live workers.
- Shared workflow stage component and Step 12 analytics dashboard through a typed
  data-source boundary. Demo metrics derive from synthetic records and local edits;
  unrecorded timings are unavailable. The actual SQL/provider/business logic stays intact.
- Validated `full`/`demo` deployment mode. Demo mode rejects the real API proxy before
  cookie/upstream access, and never grants real workspace authorization. Full mode
  retains existing session/CSRF/RBAC protections. Browser flags cannot alter server mode.
- Fail-closed reserved live-generation endpoint: all POSTs receive 403. No key access,
  SDK, outbound AI call or enableable public inference. Shared abuse controls are
  unavailable, so genuine public generation is intentionally deferred rather than
  exposing an unrestricted proxy. Existing configurable Python Gemini remains unchanged.
- Node 24-compatible Next.js build, explicit demo build/start/dev scripts, safe
  configuration template and Vercel root/build/environment/eligibility instructions.
  No hosted account/project/domain was created. Existing data and secrets preserved.

Verification:

- Full backend regression: **269 passed, one upstream SDK deprecation warning,
  66.98 seconds**. An initial run encountered a stopped project PostgreSQL server;
  starting only the owned port-55433 cluster resolved that environmental prerequisite.
- Full application browser regression: **26 passed, 2.1 minutes**, including real
  authentication, tickets, KB, classification, retrieval, RAG, durable human review
  and asynchronous queue state. Isolated databases/storage were removed by the harness.
- Final demo suite: **11 passed, 8.8 seconds** under Node 24, covering real browser
  navigation/search/filter/edit/create/reset, replays and decisions, citations,
  computed analytics, corrupted/blocked storage, input bounds, blocked full API
  reads/writes and disabled live inference. A synthetic server-only key canary was
  supplied at build time and verified absent from all browser JavaScript assets.
- Demo production build passed under checksum-verified local **Node 24.22.1**;
  full-mode production build also passed. TypeScript, ESLint, Ruff and Python
  formatting checks passed. No new npm dependency was required.
- Desktop light/mobile dark screenshots visually checked. Demo tests enforce no
  horizontal overflow at 390px/320px across overview, tickets, workflow, analytics,
  knowledge and architecture pages. An initial exact-label ticket-control test
  failed; explicit accessible names fixed it without weakening assertions.

Known boundaries and deployment gate:

- No public deployment has occurred. Local independence is tested with unreachable
  backend origins and blocked external/API browser requests. A hosted HTTPS and
  MacBook-offline acceptance test remains pending a separately approved deployment.
- Eligible personal, non-commercial Vercel Hobby use must be confirmed at publication;
  quotas are finite and future commercial hosting has no zero-cost guarantee.
- Demonstrations use fixed October 2026 example timestamps and tab-local session
  storage, not persistent multi-user data. No real model execution, semantic search,
  upload, queue processing or customer delivery occurs in demo mode.
- Public live AI is unsupported, not merely waiting for a key. The fail-closed endpoint
  has no quota parser or token-generation path; those existing controls remain tested
  in the full Python adapter. No model/provider fallback was introduced.

Run `npm --prefix apps/web run demo:build`, then `npm --prefix apps/web run demo:start`;
open http://127.0.0.1:3200/demo. See [RECRUITER_DEMO.md](RECRUITER_DEMO.md),
[DEMO_SECURITY.md](DEMO_SECURITY.md) and [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md).
Stop after Step 13; deployment, live inference and Step 14 need separate authorization.

## Step 12 — analytics and operational observability, 2026-10-21

Implemented:

- Owner/Admin-only `analytics:read`, a typed versioned overview endpoint, SQL-scoped
  aggregates and a read-only repeatable-read snapshot with authorization recheck.
  UTC creation cohorts default to 30 days and are capped at 366 days; each database
  statement has a 1.5-second timeout. No complete tables are loaded into Python.
- Actual ticket distributions/trends, validated resolution history with mean/median,
  workflow outcomes/stages, retained job phase metrics, review decisions and document
  processing/indexing/chunks. Zero denominators and missing history are unavailable,
  never fabricated zeroes. Current job state is separately labeled from date cohorts.
- Protected `/app/analytics`, date filtering, real charts/data tables, keyboard labels,
  light/dark responsive layouts, loading/error/retry/empty states and permission-aware
  navigation. Recharts 3.10.1 is pinned; unrelated screens remain intact.
- Server-generated correlation UUIDs, safe structured HTTP status/duration logs and
  persisted request-to-job correlation. Raw URL/query access logs are suppressed.
  Existing private operator health diagnostics remain separate from analytics.
- Additive migration **0010**: nullable job correlation UUID plus workspace/date
  indexes on drafts and executions. Applied to development; no schema drift.
- Fixed a checkpoint connection race exposed by regression tests: ownership probes
  now share the PostgresSaver cursor lock with background checkpoint pipelines.
  A real PostgreSQL concurrency regression preserves ownership validation.

Verification evidence:

- Full backend suite: **269 passed, one upstream Google SDK deprecation warning
  (67.55 seconds)**. Includes tenant/RBAC, date boundaries, empty metrics, reopened
  tickets, malformed histories, denominator accuracy, real workflow/review/job/KB
  aggregation, correlation privacy and all previous functional regressions.
- Full isolated browser suite: **26 passed (2.1 minutes)**, including actual
  analytics values/charts/filtering, loading/error/retry, Viewer restrictions and
  previous authentication, tickets, KB, ML, search, RAG and background workflow flows.
  Exact no-horizontal-overflow checks pass at 390px and 320px; desktop light and
  mobile dark screenshots were visually inspected.
- TypeScript, ESLint, Ruff and Ruff formatting passed; production webpack build passed.
- Synthetic benchmark: 20,000 tickets and 40,000 activity records across two tenants;
  five overview requests over 10,000 scoped tickets had **49.51 ms median**. Resolution
  SQL EXPLAIN ANALYZE measured **44.668 ms**. This is warm local in-process HTTP, not
  a production SLA or an unmeasured improvement claim. Exact measurements are saved
  in [evaluation/analytics-step12.json](evaluation/analytics-step12.json).
- Development API restarted with live inference disabled. Database/broker healthy,
  one worker and healthy dispatcher; no queued jobs or transport messages. API health
  and readiness return 200, anonymous auth returns 401, login returns 200 and protected
  analytics redirects anonymous users (307). Alembic reports 0010 head and no drift.
- Tests use isolated disposable PostgreSQL/Valkey resources and synthetic inference.
  Existing development records, ML artifacts and private Gemini credentials are
  preserved. No live provider call, external service or deployment occurred.

Definitions and limits: [ANALYTICS.md](ANALYTICS.md), [OBSERVABILITY.md](OBSERVABILITY.md).
Resolution metrics require consistent recorded histories; no legacy backfill is
invented. Job attempts reset per phase, so lifetime retry counts/compute duration
remain unavailable. Console logs are not durable audit storage. Historical state
snapshots, deleted upload history, production SLOs and external monitoring remain
future work. No Step 12 implementation blocker remains.

## Step 11 — background workflow execution, 2026-10-21

Implemented:

- RQ 2.12.0 / redis-py 8.1.0, pinned in the Python lockfile; project-local Valkey
  9.1.2 built from checksum-verified official source, authenticated on loopback 56379.
  Native compilation uses a temporary path without spaces to avoid an upstream Lua
  linker path defect. No global service, Homebrew or Docker installation was needed.
- Additive Alembic 0009: persistent job/outbox records, cooperative cancellation
  request/actor/time. Existing development data and private Gemini settings retained.
- Transactional job acceptance, HTTP 202, duplicate request/resume suppression,
  identifier-only JSON transport, stale delivery tokens, bounded publication queue,
  global/workspace capacity, session ownership and recovery after worker/broker loss.
- Dedicated SpawnWorker processes call the real seven-node graph. PostgreSQL retry
  scheduling is bounded per phase; provider generation never automatically retries.
  Paused review releases workers; exact saved review resumes the existing checkpoint.
- UI queued/processing/review/terminal states, real stage progress, worker attempts,
  cancellation feedback, bounded polling and stop-on-review behavior. No fake percent.
- Private health/list/reconcile commands, safe correlated worker logs, isolated
  broker test helper, optional Docker-compatible broker configuration and operations
  runbooks. No exactly-once execution claim or production certification.

Verification evidence:

- Focused actual RQ tests pass: worker executes real LangGraph, broker replacement
  preserves accepted resume, and killing only an isolated worker's process tree after
  classification/priority checkpoints recovers retrieval in a fresh worker with one
  persisted draft and one ticket creation event. Tests also cover cancellation during
  provider generation, bounded retrieval/database retries, workspace capacity,
  revoked authorization, duplicate delivery and exact review/resume.
- Final full backend suite: **255 passed (56.98 seconds)**, including the worker
  configuration/allowlisted transport regression. No skipped test is reported.
- Full isolated browser suite: **23 passed (2.0 minutes)**, including the added real
  queued-state/202 acceptance and stop-polling-at-review check. Uses real PostgreSQL,
  authenticated Valkey, dispatcher, dedicated worker and deterministic mock AI.
  After the final RQ settings fix, all **5 workflow browser tests passed again
  (1.3 minutes)** with the final worker implementation.
- TypeScript, ESLint and webpack production build passed. Ruff lint/format checks
  pass. Existing Google SDK emits one Python 3.17 deprecation warning; tests do not
  call the live API.
- Normal API health/readiness 200, `/auth/me` 401 without authentication, frontend
  login 200 and same-origin CSRF request 200. `/api/v1/ready` is intentionally not in
  the Next.js proxy allowlist; database readiness is checked directly on port 8000.
- Development PostgreSQL 18.6 / pgvector 0.8.6 on 55433, Alembic **0009 (head)**,
  `alembic check` reports no drift, and checkpoint setup succeeds. Private broker,
  dispatcher and one worker remain healthy after an idle heartbeat interval.
  Normal development services are running; unrelated port 55432 was left alone.
- An idle health check caught RQ WorkerPool ignoring arbitrary constructor kwargs.
  A narrow SpawnWorker subclass now applies the 60-second heartbeat TTL, five-second
  job monitoring and safe logging controls directly, and disables RQ's scheduler.
  A regression checks these actual worker settings and task-function allowlisting.

Limits: Docker config has not been run (Docker is absent); hosted deployment,
production load/partition testing and backups/restore are future work. Local model
loading occurs in each spawned task, prioritizing isolation over throughput. Outbox
reconciliation waits through infrastructure downtime without dropping accepted work;
application execution attempts remain bounded. Normal development retains Gemini
with live inference off; complete generated-response smoke tests use isolated mocks.

See [BACKGROUND_JOBS.md](BACKGROUND_JOBS.md) for guarantees/limits and
[WORKER_OPERATIONS.md](WORKER_OPERATIONS.md) for exact installation, startup,
health, tests, recovery and safe stop commands.

## Local startup repair — verified, 2026-10-21

The PostgreSQL port conflict is **resolved**. ResolveFlow now persistently uses
**127.0.0.1:55433**. Port 55432 remains owned by the unrelated DocRAG PostgreSQL 16
process (PID 18444 when inspected), using that project's `.local/postgres` directory.
It was not stopped, reconfigured or modified.

Only ResolveFlow's port configuration changed: `scripts/local_db.py` and its status
message, safe `.env.example`, ignored `.local/database.json`, the existing cluster's
`data/local/postgresql18/postgresql.conf`, and the DATABASE_URL port in the private
`apps/api/.env`. The same data directory, database, roles and passwords are retained.
All other environment bytes, including Gemini credentials, were verified unchanged.
README, DATABASE.md and the architecture port reference now describe 55433. No new
product functionality or service was added.

Actual verification:

- Normal `scripts/local_db.py start` and `status` work without monkeypatches or
  transient port overrides. PostgreSQL **18.6**, pgvector **0.8.6**, owned data
  directory and application database `resolveflow_dev` on **55433** verified.
- Runtime Settings' database URL matches the project marker-derived URL. Alembic
  reports **0008 (head)**; `alembic check` reports **No new upgrade operations detected**.
  No reset, reinitialization or destructive migration was performed.
- The normal application's owner can access LangGraph's PostgreSQL checkpoint
  storage, and its schema version matches the installed checkpointer.
- FastAPI runs at **http://127.0.0.1:8000** with the saved Gemini provider and live
  inference disabled. Next.js development frontend runs at **http://127.0.0.1:3000**
  using the supported `--webpack` option and local `API_INTERNAL_URL`.
- Headless Chrome verified the normal homepage's **API connected** indicator,
  protected `/app` → `/login` redirect, frontend-proxied CSRF **200** with a token
  present (never printed), unauthenticated `/auth/me` **401**, backend health **200**,
  database readiness **200** / `database=ok`, and **zero browser runtime errors**.
- **245 backend tests passed in 42.97 seconds** through the standard
  `scripts/local_db.py test` command; one existing Google SDK deprecation warning.
- **22 browser tests passed in 54.1 seconds** through the standard
  `scripts/test_browser.py` command. This includes registration/login, authenticated
  access, real retrieval plus deterministic generation, durable approval pause,
  review/resume, rejection/revision, cancellation and failure handling. These use
  isolated databases on the same 55433 cluster and test servers on 3100/8100;
  they do not insert smoke records into the existing development database.
- The backend suite additionally verifies fresh-process checkpoint recovery and
  no duplicate generation. Ruff lint and formatting passed for the changed helper.
  No frontend source changed, so no redundant production rebuild was required;
  browser tests used the previously verified production build.
- Test servers, disposable databases and temporary test storage were cleaned up.
  The normal development PostgreSQL, FastAPI and Next.js services are **left running**.
  Existing development data is preserved; no unrelated service was touched.

Exact local commands (run only when these servers are not already running):

```bash
# Terminal 1: database and API
cd "/Users/abhisheshramadasshet/Documents/ChatGPT/ResolveFlow AI/apps/api"
export UV_CACHE_DIR=../../.cache/uv
uv run --locked python scripts/local_db.py start
uv run --locked alembic upgrade head
uv run --locked python scripts/workflows.py setup
RESOLVEFLOW_AI_LIVE_ENABLED=false uv run --locked uvicorn resolveflow.main:app --app-dir src --host 127.0.0.1 --port 8000 --no-proxy-headers
```

```bash
# Terminal 2: frontend
cd "/Users/abhisheshramadasshet/Documents/ChatGPT/ResolveFlow AI/apps/web"
API_INTERNAL_URL=http://127.0.0.1:8000 NEXT_TELEMETRY_DISABLED=1 npm run dev -- --webpack
```

Stop your own frontend/API terminals with Ctrl+C; stop only this project's database
with `uv run --locked python scripts/local_db.py stop` from `apps/api`. Data is retained.
No startup blocker remains from the database conflict. Live inference is still off;
normal generation remains subject to the existing explicit approval gates. All smoke
inference was synthetic and deterministic. **Zero live Gemini requests; Step 11 not started.**

## Step 10 — durable ticket workflows

Implemented a seven-node `StateGraph`: classification → priority → retrieval →
context → generation → verification → human approval. Conditional edges end failed
work; a real `interrupt()` persists the human pause and `Command(resume=True)`
resumes from saved review. Existing sklearn, pgvector, provider-independent RAG,
strict citation validation and exact-draft review services are reused. The priority
worker uses documented phrase rules and does not change ticket priority/category.

PostgreSQL-backed checkpoints use the supported pinned checkpointer, explicit setup,
restricted serialization and synchronous checkpoint durability. Tenant-scoped execution
ownership, immutable request identity, shared concurrency locks, invocation/daily caps,
safe errors, cancellation and terminal checkpoint pruning are implemented. Recovery
reuses an already committed draft; an ambiguous generation reservation never retries.
Current permissions, ticket version, sources and approval hash/revision are rechecked.
No client can supply graph state or decide approval via the resume body.

The ticket page now shows real saved workflow progress, stage timings, recommendations,
evidence, verification, draft/review controls, history and recovery/stop actions.
The standalone response assistant is preserved and shares the draft card. Model
text renders as plain text; no generated tools/code or hidden reasoning are exposed.

### Files and dependencies

- New backend `apps/api/src/resolveflow/workflows/` modules: contracts, models,
  priority, storage, workers, graph and service; new authenticated `api/v1/workflows.py`.
- Additive migration `0008_workflow_executions.py`, migration model registration,
  environment bounds, API router wiring and `scripts/workflows.py` setup/prune CLI.
- Existing RAG gains shared bounded `rag/context.py` and an internal prepared-evidence
  argument. New citation `statement_text` preserves exact validated boundaries,
  including multi-paragraph statements; legacy draft reads are preserved.
- Pinned `langgraph==1.2.16`, `langgraph-checkpoint-postgres==3.2.0` and reproducible
  transitive lockfile. No alternative provider or hosted tracing service configured.
- New web workflow panel/types and shared draft card; ticket details, proxy allowlist,
  transport bounds and responsive styles updated.
- New graph/unit/PostgreSQL workflow tests and Playwright workflow scenarios; existing
  OpenAPI/migration/viewer checks and isolated browser setup extended.
- README, ARCHITECTURE, PROJECT_PLAN, RAG_PIPELINE, AI_PROVIDERS, GEMINI_INTEGRATION
  and safe API environment template updated. Added AGENT_ORCHESTRATION.md and
  WORKFLOW_STATE.md, including graph diagram, state/privacy/API/recovery contracts.

### Verification evidence

- **245 backend tests passed in 38.41 seconds** with `pytest --run-db`, synthetic
  credentials, live/free-tier flags false and disposable PostgreSQL databases.
  Includes all existing regressions, real local embeddings/classifier fixtures,
  actual LangGraph/PostgresSaver persistence and real migration checks.
- Persistence tests cover a new API application instance **and a fresh Python process**
  resuming saved approval. A forbidden generator proves approval resume cannot invoke
  generation. Crash-after-commit and ambiguous-reservation tests prove recovery
  never makes a second generation attempt. Concurrency and terminal-state guards pass.
- Tenant/CSRF/viewer/state-tampering checks pass, along with stale ticket/source/hash
  approval rejection, classifier degradation, embedding failure, six provider error
  paths, abstention, schema/version rejection, cancellation and quota checks.
- **22 browser tests passed in 54.6 seconds** against isolated real API/PostgreSQL,
  actual local retrieval/classification and deterministic generation. Includes all
  18 earlier journeys plus four workflow journeys: saved stages/reload/resume,
  approve/reject/revision, abstention/stop/transport limits and an actual failed node.
- TypeScript and ESLint passed. Ruff passed; **108 Python files** satisfy formatting.
- Production build passed with `next build --webpack`. Default Turbopack hit this
  environment's local socket `Operation not permitted` failure, including a retry;
  the supported webpack build was used for the browser suite. No deployment occurred.
- Desktop/light and narrow/dark workflow screenshots were inspected; 390px and 320px
  no-horizontal-overflow assertions passed. After the final narrow-screen adjustment,
  all **4 workflow browser tests passed again in 8.6 seconds** against the rebuilt
  production frontend. Stage cards use one column on narrow screens.
- One existing Google SDK Python 3.14 deprecation warning remains. Browser startup
  emitted the existing color-environment warning; no test assertion was weakened.

Initial verification found and fixed the new history-query proxy allowlist omission,
updated exact OpenAPI route expectations and corrected a child-process test import
path. Verification also identified a valid multi-paragraph response edge case; exact
statement persistence fixes it without weakening citation/schema checks.

### Local setup and remaining limits (Step 10 historical snapshot)

The later startup repair above resolves the port conflict recorded here.

ResolveFlow's own development database was upgraded additively to **0008** and its
checkpoint schema initialized with the non-superuser application owner. No existing
key or saved database URL was changed. Another project's PostgreSQL already occupied
configured port **55432**, so this task started ResolveFlow's own existing cluster
on temporary **55433** for setup and isolated verification. The unrelated server
was left untouched. Temporary test servers/databases/storage were cleaned up; the
ResolveFlow temporary database process is stopped after final verification. Normal
local startup still requires resolving that existing port conflict, then using the
project's own database. Do not connect this application's migration/runtime to the
unrelated database on 55432.

Execution is bounded synchronous FastAPI work. Durable recovery requires an explicit
request; Redis jobs, automatic dispatch/restart, deployment, production load and
backup/restore exercises remain future scope. The deadline is checked between nodes
and does not preempt a native ML operation. The invocation cap includes initial run
and approval resume; exhausting it blocks further recovery. Deterministic verification
checks references and basic claims, not complete factual groundedness. Human review
remains mandatory. No end-to-end live Gemini workflow was executed in Step 10.

Runbook: [AGENT_ORCHESTRATION.md](AGENT_ORCHESTRATION.md).
State/recovery contract: [WORKFLOW_STATE.md](WORKFLOW_STATE.md).
**Stop after Step 10; await a new user scope before Step 11 or further live requests.**

The earlier milestone records below retain their original scope and evidence;
the Step 10 summary above supersedes earlier next-step restrictions.

## Controlled live Gemini test after debugging — VERIFIED

On 2026-10-20, the developer explicitly authorized exactly one additional live
synthetic smoke request using the existing configured key and the verified
configuration. Ran the existing `apps/api/scripts/gemini_smoke.py` and
`GeminiProvider` unchanged. **One live API request was sent; zero retries and no
additional API calls.** The script exited 0.

| Check | Observed result |
| --- | --- |
| Provider / model | `gemini` / `gemini-3.6-flash`; `fixture=false` |
| Thinking configuration | `minimal`; thought inclusion disabled |
| Generation cap / timeout | 1,024 tokens / 25 seconds |
| Provider operation status | `response_received`; validation stage `complete` |
| Numeric HTTP status | Not exposed by the existing smoke report; no numeric status claimed |
| Finish reason | `STOP` |
| Input tokens | 379 |
| Output tokens | 160 |
| Thinking tokens | Not reported (`null`), not assumed to be zero |
| Response text present | true |
| JSON parsing | passed |
| Pydantic schema validation | passed |
| Citation / grounding validation | passed |
| Insufficient evidence | false |
| Validation error categories | none |
| Provider duration | 3,171.57 ms |
| Customer data used | false; built-in synthetic question and policy only |

The response satisfied the existing `GeneratedResponse` schema, including the
required human-review flag, and passed the unchanged statement consistency,
citation and basic claim checks. This verifies the live adapter and synthetic
structured-generation/citation path for this configuration; it is not a broader
quality, production readiness or end-to-end UI evaluation. The original failed
512-token request's exact cause remains unknown; this success does not
retroactively establish its finish reason or thinking usage.

Local preflight confirmed that the selected credential matched the existing
server `.env` key, without displaying it. The request used the SDK's official
Gemini Developer API endpoint with `vertexai=False`; any optional base-URL
environment override was removed for the process. Free-tier billing status
relies on the developer's existing explicit confirmation for this key/project.
Local settings and the smoke response do not independently expose Google's
billing configuration; no billing/project lookup or service activation was made.

A preliminary command launch failed during `Settings()` validation because
string environment overrides for the fixed integer-literal call/retry limits
were rejected. It stopped before client creation and sent **zero API requests**.
Removed those redundant process overrides and used the existing validated fixed
limits of one call and zero retries for the single actual live invocation.
There was no retry of a live request and no application-code change.

Live/free-tier enablement applied only to the smoke process. After it exited,
read-only checks confirmed saved live inference and the saved free-tier flag
remain false, the same existing key is selected, and `.env` remains owner-only
(`0600`). No key or `.env` modification, raw response logging, validation
weakening, paid fallback, persistent enablement or customer action occurred.

Only `docs/PROJECT_STATUS.md` changed for this test. No regression suite was
rerun because no code changed; the previous 210 passing offline tests remain
historical evidence. **Live Gemini integration: VERIFIED for this bounded
synthetic smoke test.** Stopped after this request. Additional live requests
require new explicit approval. **Step 10 has not started.**

## Step 9 follow-up: offline Gemini failure investigation

Completed the authorized investigation without any new live Gemini requests.
The verified implementation defect was missing diagnostic context: provider
finish/text/JSON/schema failures and post-provider response/statement mismatch
could all yield the same `invalid_output`. Usage was discarded on provider
rejection. The single historical error cannot identify which branch ran.

The leading hypothesis is generation-budget exhaustion with the 512-token smoke
cap and implicit thinking: Google's official thinking documentation lists
medium as 3.6 Flash's default versus minimal for 3.5 Flash-Lite. Thinking shares
the cap. This is not verified historical token usage. Missing fields, incomplete
JSON, absent text, a non-success finish or post-schema response inconsistency
remain possible. Invalid citations normally produce a different error code.
The complete evidence table and official references are in
[GEMINI_INTEGRATION.md](GEMINI_INTEGRATION.md#offline-investigation-and-diagnostic-fix).

Implemented content-free diagnostics on provider results/errors and the smoke
report: configured model, operation status, normalized finish reason, available
input/output/thinking counts, text presence, JSON/schema outcomes and allowlisted
validation categories. The smoke report distinguishes provider rejection from
grounding rejection and preserves metadata in both cases. It never emits raw
responses, hidden reasoning, validation inputs/messages/locations, prompts or
credentials. Unknown SDK enum warnings are suppressed locally because they
interpolate upstream values; unknown reasons are normalized.

Added configurable `RESOLVEFLOW_GEMINI_THINKING_LEVEL=minimal` using the installed
SDK's `ThinkingConfig`, with thought inclusion disabled. The smoke script now
uses the existing `RESOLVEFLOW_AI_MAX_OUTPUT_TOKENS` setting (default 1,024,
maximum 2,048) instead of hardcoded 512. This is a bounded mitigation paired with
explicit thinking control; successful live generation is still unverified.
Model selection remains configurable, no fallback/retry was added, and the same
Pydantic schema generates the request schema and validates returned output.
All existing grounding, tenant, quota and exact human-review checks are preserved.
No SDK dependency or database migration changed.

Files changed in this follow-up:

- `apps/api/src/resolveflow/ai/contracts.py`
- `apps/api/src/resolveflow/ai/providers.py`
- `apps/api/src/resolveflow/ai/gemini_response.py` (new)
- `apps/api/src/resolveflow/core/config.py`
- `apps/api/scripts/gemini_smoke.py`
- `apps/api/.env.example`
- `apps/api/tests/test_ai_provider.py`
- `apps/api/tests/test_gemini_diagnostics.py` (new)
- `docs/GEMINI_INTEGRATION.md`
- `docs/AI_PROVIDERS.md`
- `docs/PROJECT_STATUS.md`

Verification: **210 backend tests passed in 26.63s**, using dummy credentials,
mocked Gemini HTTP transport and disposable local PostgreSQL databases.
Regression cases cover partial/truncated JSON, thinking exhaustion simulations,
empty/thought-only text, invalid JSON, required/extra/type/literal/length
validation failures, valid/split structured output, unsuccessful/missing/unknown
finish reasons, invalid citations, unsupported claims and response consistency.
Tests verify all opt-in gates, one request/no retry, schema identity, configurable
thinking, output bounds, secret/content omission, and existing API/RAG behavior.
Ruff lint and formatting passed across 94 files. The existing SDK Python
`_UnionGenericAlias` deprecation warning remains non-failing. No frontend change
was made, so browser checks were not rerun. The temporary database service was
stopped after verification.

Saved local settings were checked without displaying credentials: provider
`gemini`, model `gemini-3.6-flash`, minimal thinking, cap 1,024, live/free-tier flags
false. `apps/api/.env` remains Git-ignored and owner-only (`0600`); it was not
modified in this follow-up. The existing key needs no further handling.

Next single test recommendation, **only after new explicit approval**:
synthetic built-in smoke data, `gemini-3.6-flash`, minimal thinking, 1,024-token
cap, 25-second timeout, one call and zero retries. Reconfirm the same AI Studio
project remains free-tier; enable flags only for that approved process. Do not
automatically rerun on failure. Remaining uncertainty is the original failure's
exact cause and whether this configuration succeeds on the live service.
**Live inference remains disabled; Step 10 has not started.**

## Approved live smoke test — Gemini 3.6 Flash

After the developer configured the key, explicitly requested the live test and
confirmed the AI Studio project is on the free tier, ran the existing synthetic
smoke script once with process-only live/free-tier flags. The configured target
was `gemini-3.6-flash`, output limit 512 tokens, SDK timeout 25 seconds, zero retries.
No business records or customer data were loaded; no credential was displayed.

**Result: failed**, exit code 1, safe error `invalid_output`. No response passed
validation. The adapter uses this code for a non-STOP/missing finish reason,
missing/oversized response text, or invalid JSON/schema; the later grounding
validator also uses it for missing/mismatched statements. The safe result does not
identify which branch failed; truncation or a model incompatibility cannot be
claimed from this evidence. No raw provider output or usage was retained by this
failure path, so no token usage or latency measurement is claimed.

No second request or automatic retry was made. The temporary flags applied only
to that command; saved live inference remains disabled. Free-tier eligibility is
developer-confirmed, not independently inspected. Successful live structured-output
and citation validation remain unresolved. Any further live diagnostic request
requires explicit approval; Step 10 has not started.

## Post-Step-9 configuration: Gemini 3.6 Flash

At the user's explicit request, the default model is now `gemini-3.6-flash`.
`RESOLVEFLOW_AI_PROVIDER=gemini` is preserved, and `RESOLVEFLOW_AI_MODEL` remains
configurable. Updated the default, safe template, local ignored environment file,
model assertions, developer instructions and current documentation. Historical
Step 9 evidence below retains the original model used at that time.

Checked Google's official [model reference](https://ai.google.dev/gemini-api/docs/models/gemini-3.6-flash)
and [standard pricing](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.6-flash):
the identifier is listed with structured-output support and free-tier standard
input/output. Actual project eligibility, model access, quota and response quality
remain unverified. A key alone does not establish free-tier billing status.

The existing `google-genai==2.31.0` adapter already passes the configured model
string to `models.generate_content`; no SDK upgrade, provider-interface, RAG,
citation, database or frontend change was needed. The smoke script was inspected
and remains unchanged: it reads the same settings and requires explicit opt-in.
One-call/zero-retry limits, token/context/request budgets, quota handling,
synthetic-data restrictions and the absence of paid fallback remain intact.

Prepared `/Users/abhisheshramadasshet/Documents/ChatGPT/ResolveFlow AI/apps/api/.env`
without printing its contents or any key. Existing database settings and any
existing key were preserved. The file is Git-ignored and mode `0600` (owner read/write).
The developer must manually fill `GEMINI_API_KEY=` in a local editor, save it,
and leave `RESOLVEFLOW_AI_LIVE_ENABLED=false` and
`RESOLVEFLOW_AI_FREE_TIER_VERIFIED=false` during configuration. The exact variable
names and later approval gates are in GEMINI_INTEGRATION.md. No key belongs in chat,
shell history, `.env.example`, or frontend environment variables.

Verification: **169 backend tests passed in 27.74s** using dummy Gemini credentials
and live inference disabled. Official SDK HTTP transport is mocked; the expanded
request test verifies both `gemini-3.6-flash` and an environment override back to
`gemini-3.5-flash-lite`, with the same JSON schema, timeout and token limits.
Existing RAG/citation, authorization, persistence, quota and human-review tests
passed. Ruff lint/format passed. The existing upstream SDK Python deprecation
warning remains non-failing. No live API request, deployment or Step 10 work was
performed. The temporary verification database service was stopped afterward.

Remaining prerequisites: manual key setup, confirmation that the actual Google
AI Studio project/model is on the free tier, and explicit approval for a bounded
synthetic live test. Configuration completion does not establish live compatibility.

## Completed work

Step 1 inspected the initially empty repository, preserved its pre-existing Git
metadata, checked development tools, and created project documentation and ignore
rules. Step 2 preserves that vision and adds:

- `apps/web/`: Next.js App Router homepage, strict TypeScript, Tailwind/PostCSS,
  ESLint, shared layout/home/UI components, semantic design tokens, and system
  light/dark styling. The required headline and four feature highlights are
  present, explicitly labeled as planned capabilities.
- A development-only API health indicator with configurable public origin,
  response-shape validation, a four-second timeout, cancellation, manual retry,
  and a non-blocking unavailable state. It is excluded from production rendering.
- `apps/api/`: modular FastAPI app factories, Pydantic response schemas,
  environment-based settings, `/api/v1` routing, centralized safe errors, explicit
  local CORS, Swagger/ReDoc, and OpenAPI JSON.
- `GET /api/v1/health` and `GET /api/v1/info` with the requested response bodies.
- Ruff and 14 Pytest cases covering the two routes, docs/schema, error handling,
  CORS, method rejection, and settings validation.
- Exact direct dependency pins, npm/uv lockfiles, a local Python virtual
  environment, runtime version files, and secret-free environment templates.
- Updated README run/check/stop instructions, architecture, and implementation
  plan. The requested `apps/api/` path replaces the earlier proposed `backend/`.
- Next.js generated `apps/web/AGENTS.md`, retained as version-specific guidance.

No Git commit, push, branch change, external deployment, or hosted service
provisioning occurred. Step 3 adds the isolated local database described below.

## Step 3 completed work

- Installed the official Postgres.app 2.9.6 PostgreSQL 18.6 native bundle under
  `.local/native/`; bundled pgvector is 0.8.6. Homebrew and an existing PostgreSQL
  installation were absent. No system-wide install or administrator privileges.
- Created only this project's cluster on 127.0.0.1:55432 with SCRAM authentication,
  a separate admin role and non-superuser development database owner. Generated
  credentials and cluster data are ignored by Git; no accounts/tickets are seeded.
- Added validated `DATABASE_URL`, pool/connect/statement limits, lazy engine
  lifespan, request sessions, explicit commit/rollback, and safe database errors.
- Added User, Workspace, WorkspaceMembership, and Ticket ORM models with UUIDs,
  timezone-aware timestamps, named constraints, restricted FKs and justified indexes.
- Added Alembic `0001` (vector) and `0002` (four core tables), applied to development.
  Downgrade/reapply is tested only on a disposable database; vector is preserved
  on downgrade. There is no automatic migration or schema reset at startup.
- Preserved health/info/CORS and added PostgreSQL connectivity readiness with safe
  HTTP 503 failures. No new business endpoints or frontend changes in Step 3.
- Added 8 unit cases and 22 real PostgreSQL integration cases to the original 14
  tests. Random test databases have ownership markers and narrowly scoped cleanup.
- Added [DATABASE.md](DATABASE.md) and updated README, architecture and plan to
  reflect the user's database-only scope. No authentication, Redis, AI or Step 4.

### Step 3 verification evidence

| Check | Actual result |
| --- | --- |
| Native bundle | Original app notarization accepted; final copied bundle full signature check passed |
| PostgreSQL / pgvector | 18.6 / 0.8.6; connectivity and vector distance operator passed |
| Dependency compatibility | Python 3.14 arm64 binary packages installed; locked offline sync passed |
| Development migrations | Applied `0001` and `0002` as the development owner after admin extension setup; `alembic current`: `0002 (head)` |
| Schema consistency | `alembic check`: no new upgrade operations; test metadata comparison matches |
| Schema integrity | Four tables, UUID PKs, timestamps, FKs, indexes, uniqueness and raw SQL CHECK constraints verified |
| Ordinary test command | 22 passed, 22 database cases explicitly skipped |
| Full PostgreSQL suite | 44 passed, no skips or warnings |
| Rollback safety | Fresh separate test database downgraded to base and reapplied; extension preserved; development untouched |
| Session recovery | Failed request rolls back flushed work; next readiness succeeds |
| Live readiness | HTTP 200 with PostgreSQL running; HTTP 503 with safe JSON when stopped |
| Live liveness / recovery | Health stays HTTP 200 during outage; existing API pool recovers after DB restart |
| Ruff | Lint and formatting checks passed |
| Secrets | `.env`, local credentials, native bundle, and cluster data confirmed ignored; generated credential files mode 0600 |

Step 3 issues found and resolved: an initial bundle copy failed full signature
verification; a fresh copy from the verified original passed, with no security
checks disabled. Initial model/import/helper issues were corrected before
verification. One invalid-priority test value exceeded the column width, so it
was replaced by an invalid value within the width to specifically exercise the
CHECK constraint. Final checks pass. There are no unresolved Step 3 blockers.

## Step 4 completed work

- Verified Step 3 before changes: PostgreSQL connectivity, revision 0002, all 44
  previous tests passing. Preserved the public homepage and original models/history.
- Added Argon2id hashing, syntax-validated normalized email, registration/login/
  logout/me, generic failures, safe user responses and no email-verification claim.
- Added migration 0003 for hashed opaque sessions and shared PostgreSQL rate counters.
  Cookies are HttpOnly/host-only/SameSite=Lax; production forces Secure and __Host-.
  Login rotates credentials; server expiry and logout invalidation are authoritative.
- Added synchronizer CSRF tokens, exact-origin/JSON checks, Fetch Metadata rejection,
  bounded request bodies, noncached tenant responses and shared abuse limits.
- Added workspace creation/list/read/settings and existing-user membership management.
  Central Owner/Admin/Support Agent/Viewer permissions enforce tenant access.
  Workspace row locks preserve last-owner invariants under concurrent changes.
- Added responsive `/login`, `/register`, and server-protected `/app` with actual
  forms, workspace creation/selection, settings, team roles/removal and logout.
  The Next.js route handler forwards allowlisted first-party requests to FastAPI.
  Session credentials never enter localStorage or JSON API responses.
- Added isolated PostgreSQL tests, a production-build Playwright harness, maintenance
  command for expired auth rows, and the authentication/authorization runbooks.

### Step 4 verification evidence

| Check | Actual result |
| --- | --- |
| Backend regression and security suite | **57 passed** (22 unit + 35 PostgreSQL cases), no skips in full run |
| Browser suite | **4 passed** against real Next.js → FastAPI → disposable PostgreSQL |
| Registration/login | Real Argon2id hash verified; normalized duplicate rejected; wrong/unknown/inactive login rejected |
| Session behavior | Credential rotation, persistence across fresh app instance, expiration, logout replay rejection and production cookie flags passed |
| CSRF/input/abuse | Missing/foreign/null origin, mismatched token, cross-site metadata, wrong content type, malformed/oversized input and shared throttling rejected |
| Workspace/tenant/roles | Transactional owner creation, lists, reads/updates, membership uniqueness, cross-tenant denial and role limits passed |
| Ownership concurrency | Concurrent owner self-removals yield one 204 and one 409; one owner remains |
| Migration safety | 0003 upgrade/downgrade/reapply on disposable database retains a pre-existing workspace; original migration history preserved |
| Schema drift | Development at 0003; `alembic check` reports no new upgrade operations |
| Browser integration | Real account/session/workspace flow, switching, settings, members, viewer UI, logout and lost-session redirect passed |
| Frontend validation/errors | Browser email/password validation, confirmation mismatch, invalid login and unavailable-service feedback passed |
| Responsive/layout | Desktop and mobile screenshots inspected; 390px/320px overflow assertions passed |
| Frontend checks | TypeScript, ESLint and production build passed; `/app` and API proxy are dynamic |
| Backend quality | Ruff lint and formatting passed; locked offline Python sync passed |
| Dependencies | Runtime npm audit: zero vulnerabilities; development-only glob advisory remains below |
| Test cleanup/isolation | No test databases or synthetic development records remain; occupied test port rejected before database creation |
| Local preview | `/login` HTTP 200; live `/ready` HTTP 200; local browser handoff requested |

Initial browser assertions matched both the form error and Next.js route announcer;
scoping them to form alerts fixed the selectors without weakening text assertions.
Initial React lint findings were corrected by moving JSX rendering outside fetch
try/catch blocks and using router navigation for workspace changes. Final checks pass.
No feature-blocking Step 4 issues remain. See the limitations below before public use.

## Step 5 completed work

- Read the existing instructions, design/status, auth runbooks, models, routes,
  migrations and tests. Baseline: all 57 existing backend tests passed.
- Extended the original Ticket model; added migration 0004 for assignment/version,
  notes and activities with composite tenant FKs, checks and query/history indexes.
  Upgrade preserves existing records; no development reset or seed data.
- Added authenticated ticket create/list/detail/patch, eligible-assignee, internal-note
  and history routes with strict Pydantic inputs and safe response contracts.
- Implemented central role permissions: agents edit only unassigned/self-assigned
  tickets; Owner/Admin manage priority/assignment; Viewer reads only. Notes are
  internal, readable by members and writable only by support staff.
- Serialized ticket/member writes using the workspace lock, rejected stale versions,
  and committed changes with their activity events. Membership removal/Viewer
  demotion atomically unassigns tickets and records the responsible actor.
- Added bounded SQL search/filter/sort/pagination and paginated notes/activity.
  Extended the existing proxy with bounded, allowlisted GET query forwarding.
- Added protected inbox/detail pages, real create/edit/note forms, member assignment,
  filters, status/priority badges, read-only controls, responsive layouts, loading,
  empty/error states, pending guards and both existing themes.
- Updated architecture, README, database and authorization runbooks and created
  [TICKET_MANAGEMENT.md](TICKET_MANAGEMENT.md) with exact policies and limitations.

### Step 5 verification evidence

| Check | Actual result |
| --- | --- |
| Full backend suite | **67 passed**: 22 unit + 45 PostgreSQL cases |
| Default backend command | **22 passed, 45 explicitly skipped** without database opt-in |
| Browser suite | **7 passed**: four existing auth/workspace and three ticket scenarios |
| Ticket lifecycle | Creation, retrieval, edits, all relevant status/priority/assignment paths, persistence and notes passed |
| Search/pagination | Literal title/description search, filters, sort, stable tie order, empty/deep pages and history pagination passed |
| Security | Cross-tenant ticket/note/history denial, missing/invalid IDs, unauthenticated requests, CSRF, Viewer writes, Agent limits and invalid/inactive assignees passed |
| Concurrency/atomicity | Concurrent edits return one 200 and one 409; stale edits preserve data; synthetic activity failure rolls back the edit |
| Membership changes | Viewer demotion/removal clears assignments and preserves activity; next request observes revoked permissions |
| Migration compatibility | 0004 upgrade/downgrade/reapply on disposable DB preserves pre-existing ticket/workspace; FK tenant mismatch rejected |
| Development schema | Applied 0004; alembic check reports no new upgrade operations |
| Frontend integration | Real create/edit/assign/note, filtered inbox and 26-ticket pagination through Next.js → FastAPI → PostgreSQL |
| Browser resilience | Loading, failed request/retry, retained stale form, session expiration redirect and safe literal note rendering passed |
| Visual verification | Light/dark desktop and 390/320px mobile screenshots inspected; checked widths have no document overflow |
| Quality gates | Ruff lint/format, TypeScript, ESLint and production build passed |
| Isolation | Browser helper removed its marked test DB and owned servers; no synthetic development data inserted |

Resolved during implementation: corrected generated migration ordering so the
composite unique key exists before history FKs; included the new unique index in
the exact schema assertion. Browser tests initially had a delayed interception
cleanup race and an ambiguous alert selector matching Next's route announcer;
both were corrected without weakening the behavioral assertions.

No feature-blocking Step 5 issues remain. History is append-only through the API,
not tamper-proof against the database owner. Workspace locks, substring search,
COUNT/OFFSET pagination and unpaginated eligible-member lists need production-scale
measurement. Durable submission idempotency, audit retention and least-privilege
runtime roles remain future work. No AI/customer delivery is implied by a manual
waiting_for_approval status. No Step 6, hosted service, deployment or paid dependency
was introduced.

## Step 6 completed work

- Reverified the Step 5 baseline: all 67 backend tests passed before implementation.
- Added modular document routes, services/repository, validation, storage protocol,
  local private-file adapter, supervised extraction and deterministic chunking.
- Pinned permissively licensed pypdf 6.21.1 and psutil 7.2.2. PDF/TXT/Markdown
  processing is real; no provider keys, inferred text, embeddings or AI calls.
- Applied additive revision 0005 for documents and chunks. Composite tenant FKs,
  checksum uniqueness, source offsets/page references, indexes and UUID5 chunk IDs
  enforce consistency. Existing migrations and development records were preserved.
- Extended central RBAC and fixed same-origin proxy without weakening session,
  Origin, CSRF or ordinary 16 KiB mutation limits. Uploads have a separate default
  2 MiB limit. Viewer sees metadata only; Agent may upload/read content; only
  Owner/Admin delete. Downloads are attachments with checksum verification.
- Added generated-key private POSIX storage, filename/signature/encoding validation,
  parser CPU/time/RSS/page/character/stream limits and bounded concurrent extraction.
  Existing nonprivate storage directories are rejected without changing permissions.
- Added a DB journal before storage writes, exclusive processing claims, atomic
  chunk/status persistence, deletion tombstones and explicit recovery maintenance.
  Partial files and interrupted operations stay tracked; no fake background queue.
- Added protected knowledge list/detail routes, shared workspace navigation, actual
  drag/drop and file upload, transfer progress, preview pagination, search/status/
  date/size controls, downloads, retry and confirmed deletion. Previews escape
  document text. Responsive light/dark styling follows the existing design.
- Added isolated document unit/integration/browser coverage and temporary storage
  for the browser harness. Previous authentication/workspace/ticket assertions remain.
- Added KNOWLEDGE_BASE.md and updated README, architecture, plan and security/database
  runbooks. No paid resources, deployments, custom agents or Step 7 implementation.

### Step 6 verification evidence

| Check | Actual result |
| --- | --- |
| Complete backend suite | **101 passed** in 12.04s; isolated PostgreSQL databases and document storage |
| Unit-only command | **45 passed, 56 explicitly skipped** in 2.48s without database-test configuration |
| Backend quality | Ruff lint and formatting passed (56 Python files) |
| Reproducibility | `uv sync --locked --offline` passed; pinned dependency lock updated |
| Frontend quality | TypeScript and ESLint passed with zero warnings |
| Production build | Passed; knowledge list/detail routes included alongside existing routes |
| Real browser regressions | **10 passed** in 28.7s; production Next.js → FastAPI → disposable PostgreSQL and storage |
| Document functionality | Real PDF/TXT/Markdown bytes, extraction, page/offset metadata, stable chunks, persistence, listing/pagination/filtering, download and deletion verified |
| Security and failure paths | Tenant/RBAC/CSRF, traversal/symlinks, stored script text escaping, oversize/corrupt/encrypted/no-text input, actual child time/RSS termination, compressed stream cap, checksum tampering, retry/deduplication and partial storage/DB deletion recovery verified |
| Migration compatibility | 0005 upgrade/downgrade/reapply on disposable DB preserves existing ticket; development at `0005 (head)` |
| Schema consistency | `alembic check`: no new upgrade operations detected |
| Recovery command | Ran against development: `Recovered 0 tracked documents.` |
| Cleanup and preservation | Zero remaining test databases; zero synthetic development document/chunk rows; browser test servers and local PostgreSQL stopped with data preserved |
| Visual/responsive review | Inspected light desktop list and dark mobile detail; browser checks captured both themes and 390/320px layouts without horizontal overflow |

Issues found and resolved: the initial download duplicated the middleware's
nosniff header; the redundant route header was removed. Existing nested test clients
shared a mutable app lifespan and leaked database pools; independent app instances
now preserve the same test assertions without pool leaks. Marked databases left by
failed teardown were individually inventoried, checked for ownership/no active
sessions and removed. A crash fixture created a 0755 parent; the private-directory
check correctly refused it, and the fixture now uses the actual storage directory
creation path. Final suites pass with clean isolated cleanup.

No unresolved Step 6 implementation blocker. Production limitations are explicit:
POSIX-local storage, synchronous parsing, approximate macOS RSS enforcement,
per-process concurrency, no parser OS sandbox/antivirus, no tenant storage quota or
upload rate controls, no automatic durable recovery scheduler, and no tested
production backup/restore. Persistent object storage, durable workers and deployment
hardening remain future authorized work. The existing development-only npm advisory
and broader authentication/hosting limitations remain unchanged below.

## Step 7 completed work

- Reverified Step 6 before modifications: all 101 backend tests passed in 11.53s.
  Existing source, migration history, auth/workspace/ticket/document behavior and
  uncommitted user state were preserved. No database schema change was needed.
- Installed pinned scikit-learn 1.9.1, NumPy 2.5.4 and threadpoolctl 3.7.0 with
  compatible Python 3.14 arm64 wheels; transitive SciPy 1.18.1 is locked. Only free
  packages were added to the project virtual environment.
- Added 280 versioned synthetic English examples across seven labels, 40 per class,
  with 140 paired scenario groups. All training is offline from committed synthetic
  records; private tickets are never gathered for training.
- Added input normalization/limits, label and duplicate validation, near-copy
  rejection and deterministic group-stratified 168/56/56 train/validation/test split.
  Vocabulary/IDF are fitted only on train; no final-test tuning or fabricated metrics.
- Implemented actual TF-IDF/logistic-regression training, evaluation, immutable
  versioning and measured benchmarking. Saved trained baseline-v1 in ignored private
  artifact storage, plus committed reproducible JSON reports and split manifests.
- Added data-only JSON persistence with fixed estimator reconstruction, version/class/
  shape/value checks and controlled path permissions. No pickle/joblib loading or
  user model uploads. The model loads once per app lifespan with a startup inference.
- Added TicketClassifier predict/predict_batch/get_model_info/health_check interface,
  1–32 batch bound, two concurrent calls per process and safe unavailable errors.
  Probabilities are explicitly uncalibrated; threshold 0.45 and zero-feature abstention
  produce uncertainty rather than forcing a category. Human review always applies.
- Added session/CSRF/tenant/edit-authorized classification POST on actual stored
  tickets. It does not mutate data. UI acceptance uses existing expected_version
  PATCH, assignment rules and activity; dismissal makes no write. Viewer and agents
  assigned elsewhere cannot classify. Legacy/custom categories remain valid.
- Added a real classification panel with loading, errors, score/model version,
  uncertainty, acceptance/dismissal, stale protection and responsive light/dark style.
- Added ML unit, API and real browser coverage; all test models are trained in
  temporary directories alongside isolated test databases/storage. No production
  fixture masquerades as inference. Application tests are not accuracy evaluations.
- Added ML_CLASSIFICATION.md, ML_EVALUATION.md, dataset documentation and actual
  machine-readable training/evaluation/benchmark reports. Updated related runbooks.

### Step 7 verification evidence

| Check | Actual result |
| --- | --- |
| Full backend suite | **119 passed** in 13.44s; includes all prior 101 regressions and real ML/API tests |
| Unit-only command | **60 passed, 59 explicitly skipped** in 2.82s |
| ML-specific unit tests | **15 passed**: data validation/group separation, train-only vocabulary, deterministic retraining, immutable artifacts, exact reloaded evaluation, valid/invalid inputs, scores/abstention, safe unavailable models and capacity/failure handling |
| Browser suite | **13 passed** in 34.6s through production Next.js → FastAPI → isolated DB/model/storage |
| Approval/security | Nonmutating predictions/dismissal, authorized persistence/activity, Viewer/foreign tenant denial, agent assignment restrictions, CSRF, invalid IDs, unavailable models and stale acceptance verified |
| Reproducibility | Identical coefficients/IDF/vocabulary/metrics from repeated same-config training; saved artifact reload exactly reproduced validation/test results; locked offline dependency sync passed |
| Quality gates | Ruff lint/format (66 files), TypeScript, ESLint and production build passed |
| Visual review | Inspected light desktop and dark mobile classification cards; browser checked 390/320px without horizontal overflow |
| Held-out classification | 56 records / 28 scenarios: accuracy **0.7857**, macro precision **0.7946**, macro recall **0.7857**, macro F1 **0.7846** |
| Validation classification | 56 records: accuracy **0.8929**, macro F1 **0.8859** |
| Threshold behavior | Fixed 0.45: 13/56 test suggestions (23.2% coverage), 43 abstentions; small accepted subset had no observed errors, not a production precision guarantee |
| Local benchmark | 500 warm batch-one calls, one numerical thread: median **0.161 ms**, p95 **0.182 ms**, max **0.268 ms**; load plus startup check **3.400 ms**; excludes HTTP/DB |
| Schema and isolation | Development remains at 0005; no Alembic drift; zero remaining test databases and zero synthetic development ticket/document/chunk rows |

No feature-blocking Step 7 issue remains. Initial lint formatting was corrected;
all new functional, security and regression tests passed without weakened assertions.
No dependency/runtime incompatibility required a stack change. The JSON artifact
round-trip and reproducibility checks verify the fixed persistence implementation.

The result is a small synthetic English baseline, not a production-accurate model.
Only four held-out scenarios per class, subjective boundary labels, low suggestion
coverage and uncalibrated scores limit generalization. Calibration diagnostics are
descriptive, not a fitted reliability guarantee. No real-customer evaluation, drift
monitoring, global inference rate limits, production load/latency study, hosted ML
registry or model promotion automation is claimed. See ML_EVALUATION.md for error
analysis and ML_CLASSIFICATION.md for safe retraining/replacement instructions.

## Step 8 completed work

- Inspected the required documentation, authentication/RBAC, document lifecycle,
  chunks, migrations, classifier implementation and tests. Baseline: **119 passed**
  in 12.78s before Step 8 changes; previous classification was implemented, not assumed.
- Verified the official Apache-2.0 all-MiniLM-L6-v2 model, 384 dimensions, immutable
  revision, Python 3.14 Apple Silicon wheels and actual local CPU inference. Installed
  pinned Sentence Transformers 6.1.0, PyTorch 2.14.1, Transformers 5.20.2 and pgvector
  Python 0.5.1 with a reproducible uv lockfile. Explicit download populated a private
  local safetensors snapshot; runtime loads offline once per process.
- Added the provider-neutral embedding interface, validated finite unit vectors,
  query/chunk/batch bounds, bounded concurrency and token-window aggregation for
  longer chunks. No fake embedding or keyword-only application fallback exists.
- Added migration 0006 with separate document indexing metadata and one vector per
  chunk, composite tenant/source FKs, norm checks, model-space/content hashes and
  tenant/model indexes. Existing documents/chunks preserved; no re-upload required.
- Added authorized indexing/reindexing, idempotence checks, atomic savepoint replacement,
  old-vector preservation on partial failure, stale-claim retry and final role recheck.
  Existing chunk deletion cascades vectors before private-file cleanup; failed file
  deletion cannot keep tombstoned content in search.
- Added real pgvector cosine SQL with workspace restrictions inside the query,
  compatible model-space and source-freshness filters, stable ranking and exact-content
  deduplication. Search preserves document/chunk/page/source metadata and can abstain.
- Added the semantic search form, loading/error/empty/results states, escaped source
  passages/navigation, separate indexing status and role-controlled index/reindex.
  Viewer remains metadata-only. Existing filename filtering and document UI are retained.
- Added a frozen 14-document / 24-query synthetic evaluation, actual metrics and
  timings, simple keyword baseline, authenticated terminal client and setup/runbooks.
  No generated answers, agents, background workers, hosted services or Step 9 code.

### Step 8 verification evidence

| Check | Actual result |
| --- | --- |
| Full backend suite | **139 passed** in 18.20s; real local inference and actual pgvector retrieval included |
| Real model contract cases | 13 passed: load, batch/dimensions/unit norms, semantic similarity, determinism, long text, invalid inputs/vectors, unavailable/busy handling |
| Database/API checks | Index/reindex/idempotence, interrupted retry, missing/changed embeddings, model changes, failed replacement rollback, vector constraints, preserved chunks across migration rollback/reapply |
| Tenant/security checks | Overlapping content in two workspaces; no foreign IDs/names; Viewer denial; Agent allowance; CSRF/invalid inputs; composite FK isolation; safe unavailable errors |
| Deletion checks | Cascaded vectors, deleted-result exclusion, file-failure tombstone and retry; previous document regressions preserved |
| Browser regression | **15 passed** in 39.9s on the final run; production Next.js → API → disposable DB, real local embeddings and real classifier |
| Frontend quality | TypeScript, ESLint and production build passed |
| Default test command | **73 passed, 66 explicitly skipped** in 4.70s with the local model installed |
| Visual and role review | Light desktop and dark mobile inspected; 390/320px overflow checks passed; Viewer search/index controls absent |
| Test isolation | Zero remaining test databases; development tickets/documents/chunks/embeddings all remain zero |
| Python quality | Ruff lint/format and locked offline dependency sync passed |
| Migration | Development upgraded additively to **0006**; `alembic check`: no new upgrade operations |
| Retrieval quality | 21 answerable questions: Recall@5 **0.9286**, MRR@5 **0.9286**, Hit Rate@5 **0.9524**; 3/3 no-answer cases returned empty |
| Keyword comparison | Recall@5 **0.8492**, MRR@5 **0.6762**, Hit Rate@5 **0.9048**; two no-answer queries produced lexical matches |
| Measured local performance | Search median **7.90 ms**, p95 **8.52 ms** over 24 in-process HTTP requests; 30-chunk / 28,768-character indexing **294.42 ms** |
| Corpus integrity | Frozen dataset SHA-256 and pinned model identity recorded in `docs/evaluation/retrieval-v1.json`; no test-set tuning; rerun reproduced ranking metrics |

Initial test fixture errors used an unsupported email TLD and uppercase workspace
slug; corrected fixtures preserve validation behavior. The expected OpenAPI path
set was extended for the two new routes. Dependency lookup initially encountered
a Python certificate-store issue; the system TLS-verified client obtained metadata,
and standard dependency/model downloads completed without disabling verification.
An earlier approval review could not run due to an account usage limit; after the
user resumed, normal approval succeeded. No approval bypass was used.

Known limits: exact search is evaluated on a tiny English synthetic corpus, not
production data. A vague billing question abstained incorrectly; another access
question ranked an irrelevant passage first. No calibration, reranking, global
quotas, durable queue, public load study or production-readiness claim. Indexing
checks a deadline between batches; it cannot forcibly interrupt a hung native call.
RSS is sampled process memory, not a model-only peak. MPS fallback is implemented;
CPU is the verified device and no MPS benchmark is claimed. Model-space changes need
review/reindexing; different dimensions also require a schema migration. See
SEMANTIC_SEARCH.md and RETRIEVAL_EVALUATION.md for complete limits and exact commands.

## Step 9 completed local work and pending live gate

The user's Step 9 request authorizes bounded Gemini RAG response drafts and
internal human review. It explicitly excludes LangGraph, workers, messaging,
refunds, billing, analytics, subagents and deployment. Work stops at this boundary.

- Verified Google's exact `gemini-3.5-flash-lite` identifier, structured-output
  documentation and free-tier listing. Installed official `google-genai==2.31.0`
  with its reproducible lockfile. Account-specific eligibility remains unverified.
- Added typed provider-neutral contracts, a real SDK adapter, configurable model,
  safe normalized errors/usage, one outbound call and zero retries, per-call
  client cleanup, timeout and concurrency controls. Fixture mode is test-only,
  explicitly labeled and never a failure fallback.
- Reused real tenant-scoped embeddings/pgvector retrieval, with bounded query,
  top-k/context, source hash manifest, versioned untrusted-context prompt,
  structured generation and validated actual source quotations. Local abstention
  handles missing evidence, account status and obvious injection without a call.
- Added server-only live/free-tier/key gates, synthetic-workspace allowlist and
  per-request synthetic confirmation. Character/output limits, shared PostgreSQL
  daily/global/user/workspace budgets, atomic in-flight reservations, request
  idempotency and interrupted-request recovery bound resource use.
- Migration `0007` adds draft history, composite-tenant citation references and
  exact-revision review audit records. Permission/ticket/source changes during
  generation fail without publishing text. Later source deletion/change or ticket
  edits invalidate approvability and historical approval validity.
- Added secure generate/config/list/detail/review APIs and the existing ticket
  page's response assistant, with real backend calls, plain-text evidence,
  metadata, history, loading/failure/stale/abstention states and review controls.
  Viewer cannot read private document-derived drafts. Approval takes no external action.
- Added versioned synthetic RAG scenarios, reproducible evaluation, safe opt-in
  smoke command, and GEMINI_INTEGRATION.md, AI_PROVIDERS.md, RAG_PIPELINE.md and
  RAG_EVALUATION.md. Updated the README, architecture, database guide and plan.

### Step 9 verification evidence

| Check | Actual result |
| --- | --- |
| Full backend suite | **168 passed** in 28.86s, including real local retrieval, migrations, concurrent request replay/reservations, stale permissions/evidence, review and earlier regressions |
| Default Pytest | **83 passed, 85 explicitly skipped** in 4.63s; PostgreSQL integration opt-in |
| Browser regressions | **18 passed** in 48.3s against production Next.js, real auth/API/PostgreSQL, extraction and embeddings; generation explicitly uses a fixture |
| Provider transport | Official SDK serialized the configured model/schema/token/timeout options; mocked HTTP errors verified one attempt and safe quota/timeout/credential/model errors |
| Frontend quality | TypeScript, ESLint with zero warnings, and production build passed |
| Backend quality | Ruff lint and format passed (92 Python files); locked offline sync resolved 108 packages and checked 84 installed packages |
| RAG evaluation | 12 synthetic cases; 7/7 expected-source retrieval hits, 7/7 valid cited drafts, 5/5 expected abstentions, 0/7 false abstentions, **3/7 required-term completeness** |
| Local fixture latency | Median **20.61 ms**, p95 **31.53 ms** in-process HTTP including CSRF/auth/retrieval/persistence; not Gemini or network latency |
| Visual checks | Inspected desktop light and 390px mobile dark screenshots; browser assertions found no horizontal overflow at 390px or 320px |
| Migration | Development schema **0007**; `alembic check` found no new upgrade operations; downgrade/reapply tested only on disposable databases |
| Isolation/cleanup | No remaining disposable test databases; development ticket/document/chunk/vector/draft/citation/review counts remain zero |
| Smoke CLI gate | Standalone command without opt-in exits **2**, with a clear “Not run” message and no provider call; fixed and rechecked its local import path |
| Live Gemini | **Not run**: no securely configured key, no verified account free tier and no explicit live-test enablement |

The SDK emits an upstream Python `_UnionGenericAlias` deprecation warning; tests
pass and no dependency internals were patched. Prompt injection and sensitive-data
regexes are limited heuristics; citation matching and lexical checks cannot prove
semantic support. The fixture's incomplete answers are recorded, not hidden.
Remote cancellation, real Gemini quality/latency, production DLP, retention policy,
database runtime-role separation, durable workflow recovery and deployment remain
unverified or future work. Document deletion invalidates references but does not
erase retained generated-response/review history.

Live testing can proceed only after the developer securely configures the server
key, confirms the actual project/model free tier, and explicitly enables the
bounded synthetic smoke path described in GEMINI_INTEGRATION.md. These settings
were not enabled during this step. No Step 10 work was started.

## Verified environment and versions

| Tool or dependency | Observed / pinned version |
| --- | --- |
| Platform | Apple Silicon macOS / Darwin arm64 |
| Git | 2.54.0 (Apple Git-157); existing `main` with no commits |
| Node.js / npm | 26.5.0 / 11.17.0 |
| Python / uv | 3.14.6 / 0.11.26 |
| Next.js / React | 16.4.2 / 19.3.1 |
| TypeScript / ESLint | 6.0.3 / 10.13.0 |
| Tailwind CSS / PostCSS | 4.3.3 / 8.5.30 |
| FastAPI / Pydantic | 0.143.3 / 2.14.1 |
| Pydantic Settings / Uvicorn | 2.16.0 / 0.54.0 |
| Ruff / Pytest / httpx2 | 0.17.1 / 9.1.1 / 2.13.1 |
| PostgreSQL / pgvector | 18.6 / 0.8.6 |
| SQLAlchemy / Alembic / psycopg | 2.0.55 / 1.20.0 / 3.3.6 |
| Argon2-cffi / email-validator | 25.1.0 / 2.3.0 |
| scikit-learn / NumPy / SciPy / threadpoolctl | 1.9.1 / 2.5.4 / 1.18.1 / 3.7.0 |
| Sentence Transformers / PyTorch / Transformers / pgvector Python | 6.1.0 / 2.14.1 / 5.20.2 / 0.5.1 |
| Google GenAI SDK | 2.31.0; one approved synthetic live test verified |
| LangGraph / PostgreSQL checkpointer | 1.2.16 / 3.2.0; real persistence and recovery verified |
| Playwright | 1.64.1; installed Google Chrome used for isolated headless tests |

Apple Command Line Tools, Clang, Make, curl, ripgrep, pip3, Python venv, and SSL
were available during initialization. `python` is not on PATH; use `python3` or
`uv run`. Docker/Podman/Colima, PostgreSQL tools, Redis, and Homebrew were not on
PATH during the Step 1 check. None is required for Step 2, and none was installed.
Local native ML wheels are now verified through Step 10; hosted runtimes remain untested.

## Step 2 verification results (historical)

| Check | Actual result |
| --- | --- |
| Frontend dependency installation | Completed with exact direct versions and `package-lock.json` |
| Locked frontend reinstall | `npm ci --offline` succeeded using the project cache |
| Backend dependency installation | Completed in `apps/api/.venv` with `uv.lock` |
| Locked Python environment | `uv sync --locked --offline` succeeded |
| TypeScript | `npm run typecheck` passed |
| Frontend lint | `npm run lint` passed with zero warnings |
| Production build | `npm run build` passed; `/` and `/_not-found` prerendered |
| Production startup | `npm run start` succeeded; HTTP 200 with API stopped; required headline present and development panel absent |
| Backend lint / formatting | `ruff check .` and `ruff format --check .` passed |
| Backend automated tests | 14 passed, no warnings after test-client update |
| Development servers | Next.js and Uvicorn started on loopback ports 3000 and 8000 |
| HTTP endpoint checks | Homepage HTTP 200; live health and info JSON matched required responses |
| Browser → API → UI | Rendered `API connected` from the real local health endpoint |
| Backend offline | Stopped owned API process; browser retry rendered `API unavailable`; homepage remained usable |
| Backend recovery | Restarted API; browser retry returned to `API connected` |
| Responsive verification | Inspected desktop 1440px and narrow 390px/320px layouts; fixed decorative overflow; document width equals viewport at checked widths |
| Browser diagnostics | No warning/error entries returned by browser console capture during verification |
| Repository checks | 43 source/config/document files checked; local Markdown links, whitespace, secret ignores, and lockfile/template retention passed |

Browser checks were performed through the connected browser, not a committed
Playwright test suite. The visible system theme was dark; the light token set is
implemented but has not received a separate visual browser pass. The initial
frontend checks requested for this step are TypeScript, ESLint, and production
build validation; Vitest and a persistent Playwright suite remain planned.

## Failures found and resolved

- The first registry lookup was blocked by sandbox networking. Dependency
  downloads succeeded with approved network access; caches stayed in the project.
- The initially resolved TypeScript 7.0.2 was rejected by typescript-eslint.
  Pinned compatible stable TypeScript 6.0.3 and reran type/lint checks successfully.
- ESLint 9 is no longer supported; selected ESLint 10.13.0, supported by the
  installed Next.js 16.4 lint configuration. Removed two source lint warnings
  (anonymous config export and unnecessary effect ref).
- Starlette's test client warned that httpx was deprecated. Replaced it with the
  supported httpx2 test dependency; all 14 tests then passed without warnings.
- The sandbox denied local socket binding, affecting server startup and a
  Turbopack worker. Servers started with approved loopback access. A failed build
  worker state persisted in the generated cache; clearing `.next` and rebuilding
  with approved local execution produced a successful production build.
- Rotated decorative rings caused mobile horizontal overflow. Clipped their
  container and verified 390px and 320px document widths match their viewports.

## Known limitations and remaining work

- npm emits upstream peer-range warnings for some ESLint plugins whose metadata
  still lists ESLint 9. Next.js 16.4's bundled docs explicitly describe ESLint 10
  support and these warnings. Actual lint checks pass; no force/legacy-peer-deps
  setting or lint-rule suppression was added.
- npm also reports an unapproved optional `unrs-resolver` postinstall hook.
  Installed native packages were sufficient for all current checks; no blanket
  install-script approval was granted.
- Application authorization protects workspace/member, ticket and document routes. There is no
  database row-level security. Future resources must reuse the
  central access boundary and tenant-scoped queries. Health is process liveness
  and readiness checks database connectivity, not schema state.
  CORS is not access control. Documentation UIs use FastAPI's default CDN assets.
- The connection panel checks at mount/manual retry only. There is no continuous
  monitoring; production builds intentionally hide this local development panel.
- shadcn/ui, future classifier improvements and production security controls remain
  planned. Step 12 implements the workspace analytics dashboard. Step 10 implements
  durable LangGraph execution; Step 11 dispatches workflows to background workers.
  Broader live Gemini quality is unmeasured.
- Provider selection and server-only Gemini settings are implemented. The existing
  configured key passed one user-approved synthetic test after free-tier confirmation.
  Live inference remains off and any further API request requires explicit approval.
- Distinct production runtime/migration roles remain future hardening. Raw SQL
  writers must maintain `updated_at` explicitly.
- Email verification/recovery, MFA, authentication audit events, full CSP rollout, production
  load/penetration tests and restore exercises remain deferred.
- Through Next.js, users share the API proxy-IP rate budget. Limits persist across
  API workers, but public deployment needs trusted-ingress and capacity review.
- The full npm audit reports five high entries in one development-only glob chain
  (`braces` → micromatch → fast-glob → Next ESLint plugin/config). Runtime audit is
  clean. The proposed incompatible downgrade was not applied; see
  [AUTHENTICATION.md](AUTHENTICATION.md) for the advisory and exposure limits.
- Node/Python compatibility is verified for this foundation on this Mac. The standalone demo also passed its Step 15C Vercel build and hosted smoke checks.
- A sustainable free hosted API/data/worker/embedding arrangement for the full system
  remains unresolved. The standalone synthetic demo does not need that infrastructure;
  hosted checks found no laptop/backend dependency, but physical MacBook-off acceptance remains pending.
- GPT-6 Astra remains the requested primary development agent; this repository
  does not select or verify the active chat model. No subagents or agent TOML
  configuration were created.

## Next action

Stop after Step 17A. The reviewed local release is ready for a separately authorized
push and deployment. Live demo remains at https://resolveflow-ai-rosy.vercel.app/demo
on `be7efbc`. Do not proceed to Step 17B, modify Vercel or enable Gemini without
explicit permission. See PORTFOLIO_READINESS.md and DEMO_SECURITY.md for release
identification, verified CSP scope and remaining limitations.
