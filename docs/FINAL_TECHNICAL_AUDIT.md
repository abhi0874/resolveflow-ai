# Final technical audit — Step 18

> Historical assessment retained. Step 20 current implementation, fresh verification
> and operating limits are recorded in [PORTFOLIO_EVIDENCE.md](PORTFOLIO_EVIDENCE.md),
> [SYSTEM_ARCHITECTURE_OVERVIEW.md](SYSTEM_ARCHITECTURE_OVERVIEW.md) and the
> [current readiness matrix](PRODUCTION_READINESS_MATRIX.md). Earlier pending-feature,
> deployment and advisory statements below are dated evidence, not current setup instructions.

Audit date: **2026-10-23, Asia/Kolkata**. Reviewed application revision:
`759e5f87751cb49c1dd117755dcbdc08b14e31af`, branch `main`.
The pre-existing local Step 17B status update is preserved. This audit changes
documentation only; it is not a release, penetration-test certification, or
permission to enable real-user inference.

## Assessment

ResolveFlow AI is a substantial implemented local application with genuine ML,
retrieval, persistent workflows and background execution. It is more than a UI
mock. Its public Vercel demonstration is deliberately a different runtime:
synthetic, browser-local and independent of those backend services.

- **Local full application:** verified for the tested synthetic journeys on this
  Mac, including actual PostgreSQL, local models, Valkey/RQ and process recovery.
  Routine generation remains disabled; complete automated journeys explicitly use
  the test-only deterministic provider. This is not unrestricted live AI operation.
- **Public recruiter demo:** suitable for sharing within its disclosed synthetic
  scope. It does not demonstrate hosted backend execution or live inference.
- **Commercial production SaaS:** **blocked**. Identity ownership, deployment and
  least-privilege operations, tested restoration, retention/privacy, abuse controls,
  monitoring and representative quality/capacity evidence remain release gates.

No critical exploitable defect was established by this bounded review. That is
not evidence of absence. In particular, the unverified-email membership path is a
high-severity conditional risk for a real multi-user release, detailed below.

Companion documents: [readiness matrix](PRODUCTION_READINESS_MATRIX.md),
[prioritized work](REMAINING_WORK.md), and
[portfolio technical summary](PORTFOLIO_TECHNICAL_SUMMARY.md).

## Method and evidence boundaries

Read the repository instructions, README, architecture, plan, status and the
requested provider, RAG, ML, graph, job, worker, analytics, portfolio and Vercel
documents. No `docs/SECURITY.md` exists. Inspected the corresponding source,
migrations, test harnesses and test assertions rather than accepting counts alone.
This is a cross-component source review, not an exhaustive proof of every branch.

Fresh checks are recorded below. Historical measurements are explicitly dated.
No Gemini request, production configuration change, deployment, Git commit/push,
repository visibility change or paid-service activation occurred. Tests created
only owned disposable databases, brokers, files and processes. Existing development
database/storage and credentials were preserved.

### Fresh local verification

| Check | Actual result | Evidence and scope |
| --- | --- | --- |
| Backend suite including database integration | **269 passed, 1 warning, 73.07 seconds; no skips** | `apps/api/scripts/local_db.py test`; `.cache/verification/step18-backend.txt` |
| Full Next.js production build | **Passed** | Node 24.22.1, full mode, webpack; `step18-full-build.txt` |
| Full-application browser suite | **26 passed, 2.0 minutes** | `apps/api/scripts/test_browser.py`; real Chrome, isolated API/DB/models/dispatcher/RQ/broker; `step18-full-browser.txt` |
| Local demo browser suite | **16 passed, 14.5 seconds** | Existing production demo build, backend/external calls forbidden; `step18-demo.txt` |
| Hosted demo browser audit | **11 passed, 1.6 minutes, zero retries in the completed run** | Existing Step 17B scenarios copied into ignored `step18-hosted/`; public production alias; `step18-hosted-verified.txt` |
| TypeScript | **Passed** | `next typegen && tsc --noEmit`; `step18-typecheck.txt` |
| ESLint | **Passed, zero warnings** | `eslint . --max-warnings=0`; `step18-eslint.txt` |
| Ruff lint / formatting | **Passed / 129 files already formatted** | Read-only `ruff check .` and `ruff format --check .` |
| Saved classifier re-evaluation | **Passed, exact saved evaluation reproduced** | `classifier.py evaluate --version baseline-v1`; `step18-classifier-evaluation.json` |
| Git path/history pattern review | **266 tracked paths, 285 reachable history blobs; no tested credential patterns or forbidden tracked runtime paths** | Google/GitHub/AWS credential patterns and private-key delimiters; no credential values printed |

The SDK warning concerns Python's deprecated `_UnionGenericAlias`, scheduled for
removal in Python 3.17; it did not fail the current Python 3.14 tests. It is an
upstream compatibility watch item, not a reason to weaken assertions.

The browser harness reported removal of its isolated database and storage;
ports 3100/8100 were no longer listening. The pre-existing owned PostgreSQL
process on 55433 remained running. No unrelated service was terminated.

The first hosted invocation reported 11 browser-launch failures before application
steps because the sandbox prevented Chrome from starting. The unchanged suite
was rerun with the required execution permissions and all 11 passed. This was an
environment failure, not silently skipped assertions. Hosted tests used anonymous
contexts and synthetic tab-local edits; their negative generation checks received
403 from the disabled route and made no Gemini request. Normal journeys attempted
no forbidden external/API request and had no unexpected browser errors. Tested
headers, redirects, citation navigation, local reviews, responsive/keyboard behavior,
axe checks and negative CSP enforcement passed. These are bounded observations,
not a production load test or exhaustive public-asset scan.

Relevant reproducible commands, with installed dependencies/models and owned
PostgreSQL already available:

```bash
# From apps/api; the helper enables the real isolated DB tests.
RESOLVEFLOW_AI_LIVE_ENABLED=false .venv/bin/python scripts/local_db.py test
.venv/bin/ruff check .
.venv/bin/ruff format --check .
RESOLVEFLOW_AI_LIVE_ENABLED=false .venv/bin/python scripts/classifier.py evaluate \
  --version baseline-v1 --output ../../.cache/verification/step18-classifier-evaluation.json

# From repository root; use Node 24.22.1 for the audited frontend environment.
NEXT_PUBLIC_APP_MODE=full NEXT_TELEMETRY_DISABLED=1 npm --prefix apps/web run build -- --webpack
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint

# From apps/api after the full build; owns and cleans up its test services.
NEXT_PUBLIC_APP_MODE=full RESOLVEFLOW_AI_LIVE_ENABLED=false .venv/bin/python scripts/test_browser.py

# Separately, from root. Full and demo builds share .next: never run concurrently.
npm --prefix apps/web run demo:build
npm --prefix apps/web run test:demo
```

The Step 18 demo tests used the existing Step 17A demo build before the full build.
The commands above show how to recreate it from source. No separate Vitest suite
is installed; frontend functional evidence here is Playwright, not a claimed
component-unit suite. Existing tests train temporary classifier fixtures where
necessary; the saved `baseline-v1` was only loaded/evaluated, never replaced.

### Coverage and what it establishes

All test paths below are under `apps/api/tests/` unless stated otherwise.

- `test_auth_workspaces.py`, `test_tickets.py`: sessions, expiry/rotation/logout,
  CSRF/Origin, role/tenant boundaries, last-owner concurrency, additive migrations,
  assignment/version conflicts and persisted activity.
- `test_documents.py`, `test_document_processing.py`: actual extraction, unsafe
  paths/inputs, scoped access, bounded processing, failure/retry/deletion behavior.
- `test_ml.py`, `test_classification_api.py`: real fitting, disjoint groups,
  train-only vocabulary, deterministic coefficients/evaluation, safe artifact
  loading and authorized acceptance. ML output does not silently change tickets.
- `test_embeddings.py`, `test_retrieval.py`, `test_retrieval_evaluation.py`:
  installed local model, actual vectors and PostgreSQL search, scoped/stale/deleted
  evidence and a synthetic evaluation. None skipped in this run.
- `test_ai_provider.py`, `test_gemini_diagnostics.py`: mocked SDK transport,
  configured schema/model/thinking/retry bounds, truncation/empty/malformed/missing
  fields/finish reasons and safe diagnostics. These tests are not live calls.
- `test_rag.py`, `test_rag_evaluation.py`: real retrieval with fixture generation,
  exact quote checks, budget/idempotency, changed-source/permission races and review.
- `test_workflows.py`, `test_workflow_units.py`: actual PostgreSQL checkpoints,
  fresh-process approval resume, stale approvals, cancelled execution, competing
  starts, schema mismatch and ambiguous generation failing closed.
- `test_jobs.py::test_real_rq_process_checkpoint_resume_and_broker_restart`
  replaces a disposable broker with empty state and resumes from PostgreSQL.
  `test_real_worker_interruption_and_checkpoint_recovery` kills only its test
  worker during retrieval and checks retained stages and one draft/activity.
  Recovery deadlines are advanced in the isolated fixture; this is not a measured
  production recovery-time objective or arbitrary-partition chaos study.
- `test_analytics.py`: authorization and SQL cohort semantics, missing-history
  handling, real synthetic aggregates and a representative local query exercise.
  No production analytics SLA is inferred.
- `apps/web/tests/*.spec.ts`: 26 real browser journeys covering the above user
  flows through the same-origin Next.js proxy. Fixtures only replace generation;
  authentication, database, extraction, ML, retrieval and workers execute locally.

## Component assessment

“Implemented and verified” below means the stated local scope and tests, never
commercial certification. Deployment gaps are assessed separately.

| Component | Classification | Specific implementation and evidence | Remaining boundary |
| --- | --- | --- | --- |
| 1. Next.js frontend | Implemented and verified | `apps/web/src/app/`, `components/`, `lib/session-api.ts`; 26 full and 16 demo browser tests; build/type/lint | Chrome-focused; real devices/screen readers not fully audited; shadcn/ui and Vitest remain planned, not shipped |
| 2. FastAPI backend | Implemented and verified | `main.py`, `api/v1/`, `core/errors.py`, `core/security.py`; 269 tests | No full-stack hosted runtime or production throughput evidence |
| 3. PostgreSQL | Implemented and verified | `db/`, migrations `0001`–`0010`, `test_database.py`, migration preservation tests | Backup restore/production roles and rollout remain unverified |
| 4. Authentication/authorization | Implemented but partially verified | `services/auth.py`, `services/authorization.py`, `api/v1/auth.py`; real session/CSRF/roles tests | No mailbox verification, password recovery or complete session-management flow; S1/S2 |
| 5. Workspace/tenant isolation | Implemented and verified | Scoped queries, permission checks, composite relationships, server-built checkpoint IDs; auth/ticket/RAG/graph/job/analytics negative tests | Application enforcement, not PostgreSQL RLS or exhaustive penetration testing |
| 6. Tickets | Implemented and verified | `services/tickets.py`, ticket routes/schemas; optimistic versions, assignment, notes/activity; `tickets.spec.ts` | No email/helpdesk connector or external customer delivery |
| 7. Knowledge processing | Implemented and verified | `documents/{validation,extraction,storage,service,chunking}.py`; actual PDF/text processing tests | Private local files, bounded synchronous extraction; no distributed storage, cumulative quota or comprehensive malware/OCR pipeline |
| 8. ML classification | Implemented and verified | `ml/{dataset,training,artifact,classifier,evaluation}.py`; training tests and saved-artifact re-evaluation | Tiny synthetic dataset, low suggestion coverage, uncalibrated scores |
| 9. Sentence Transformers | Implemented and verified | `retrieval/provider.py`; real offline model tests, pinned safetensors snapshot, CPU bounded batches | Hardware/parallel memory behavior not load-tested |
| 10. pgvector retrieval | Implemented and verified | `retrieval/service.py`, migration `0006`; real exact cosine SQL and tenant/source checks | Small corpus, no large-corpus/ANN performance validation |
| 11. Gemini adapter | Implemented but partially verified | `ai/providers.py`, `ai/gemini_response.py`; mocked SDK tests and historical one-call success | No new remote availability, quota or billing attestation; no broad live quality study |
| 12. RAG generation | Implemented but partially verified | `rag/{context,prompt,service}.py`; real retrieval/fixture evaluation and browser drafts | Pipeline verified; live answer relevance/completeness and adversarial generalization unestablished |
| 13. Citations | Implemented and verified | `rag/prompt.py::validate_response`, current source/hash checks and composite citation constraints; forged/stale citation tests | Mechanical validity and lexical checks do not prove entailment |
| 14. LangGraph | Implemented and verified | `workflows/graph.py`, `workers.py`, `storage.py`; genuine seven-node StateGraph and PostgresSaver | Bounded predetermined graph, not an autonomous tool-selecting agent swarm |
| 15. Human approval/recovery | Implemented and verified | Real `interrupt`, `Command` resume, saved exact response hash/revision and reauthorization; fresh-process/review tests | Completion is internal only; no customer send action |
| 16. Valkey/RQ | Implemented and verified | `jobs/transport.py`, dispatcher/worker scripts; real SpawnWorker tests | Long-lived service supervision, hosted TLS/ACL deployment untested |
| 17. Job durability | Implemented and verified | `jobs/{dispatch,worker,service}.py`, PG outbox/session locks/delivery tokens; broker loss, duplicate and killed-worker tests | At-least-once transport, no exactly-once external-action claim or database-disaster restore evidence |
| 18. Analytics/diagnostics | Implemented but partially verified | `analytics/{service,queries,resolution}.py`, `core/observability.py`, `scripts/jobs.py health`; actual SQL/browser tests | Analytics verified; operational alerting/SLOs/log retention/incident drills incomplete |

Backend paths without a prefix in this table are relative to
`apps/api/src/resolveflow/`; migration paths are under `apps/api/migrations/`.

## AI/ML evidence

### Classifier

The versioned 280-example corpus has seven balanced labels and 140 paired scenario
groups. `dataset.py` rejects duplicate/near-duplicate cross-group content and
inconsistent labels, then uses seeded group-stratified 168/56/56 train/validation/test
splits. `training.py` fits TF-IDF and logistic regression only on training rows.
Tests explicitly check no held-out-only vocabulary enters the artifact. This guards
the coded split, not unknown conceptual overlap in hand-authored scenarios.

`artifact.py` stores coefficients/vocabulary/IDF as bounded validated JSON rather
than executable pickle, pins library/model/preprocessing versions and refuses
overwriting a model version. Dataset hashes, split membership, configuration and
metrics are in [classifier-v1-training.json](evaluation/classifier-v1-training.json).

Fresh Step 18 re-evaluation of the existing artifact exactly matched saved results:

| Split | Accuracy | Macro F1 | Interpretation |
| --- | ---: | ---: | --- |
| Validation, 56 examples | 0.892857 | 0.885928 | Small synthetic development cohort |
| Test, 56 examples | 0.785714 | 0.784580 | 44 correct; only 28 held-out scenario groups |

At threshold 0.45 the model suggests 13/56 test categories (23.2% coverage),
abstaining on 43. No errors among those 13 is not evidence of perfect precision.
General Support, Other, Product Inquiry and Technical Support are weaker categories.
Scores are not calibrated business confidence. See [ML_EVALUATION.md](ML_EVALUATION.md).
Its historical 0.161 ms median/0.182 ms p95 benchmark measures warm local classifier
calls, not this audit's browser/API latency. No new benchmark or production SLA
is claimed.

### Embeddings and retrieval

The local `sentence-transformers/all-MiniLM-L6-v2` snapshot is pinned to revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. The adapter checks files/hashes, disables
remote code/downloads and loads safetensors locally. It produces normalized
384-dimensional vectors using bounded overlapping token windows and a versioned
pooling/embedding-space identifier. Embeddings are separate from generation.

`retrieval/service.py` joins documents/chunks/vectors with workspace, completion,
embedding-space and content-fingerprint predicates, then performs exact cosine
ranking and deduplication. Authorization is rechecked after query embedding.
The actual installed model/pgvector tests ran in Step 18.

The recorded [retrieval-v1.json](evaluation/retrieval-v1.json) experiment contains
14 documents, 24 queries, 21 answerable cases and 3 no-answer cases. At K=5:
semantic recall **0.928571**, MRR **0.928571**, hit rate **20/21 = 0.952381**;
the keyword baseline recall is **0.849206**, MRR **0.676190**, hit rate **19/21**.
All three negative queries returned no semantic results. Recall and hit rate differ
because some questions have multiple relevant sources. This is a small synthetic
comparison, not representative customer retrieval performance.

The recorded 7.90 ms median/8.52 ms p95 search timing is local in-process HTTP,
auth/CSRF and DB timing, not a network service SLA. The evaluation test reran for
functionality in Step 18 without replacing that report; it only requires nonzero
hit rate, so a passing suite alone does **not** prove exact metric non-regression.

### RAG, live communication and quality

RAG bounds and separates untrusted ticket/evidence text, deduplicates passages,
records source hashes and reserves generation under database budgets. Citation
validation requires supplied chunk IDs, exact source substrings, consistent joined
statement text, supported numeric tokens and basic lexical overlap. It rechecks
ticket/source/authorization before publishing and before approval.

The recorded [rag-v1.json](evaluation/rag-v1.json) is a **deterministic pipeline
evaluation**, not Gemini quality: 7/7 expected-source hits and valid cited drafts,
5/5 expected abstentions, but only **3/7 required-term completeness**. Extracting
a first sentence can yield a valid citation and still omit essential instructions.

The historical controlled live result is explicitly recorded in
[PROJECT_STATUS.md](PROJECT_STATUS.md#controlled-live-gemini-test-after-debugging--verified):
2026-10-20, one request, zero retries, `gemini-3.6-flash`, minimal thinking,
1,024-token cap, 25-second timeout. Result: `response_received`, finish `STOP`,
379 input/160 output tokens, thinking usage unreported, 3,171.57 ms provider
duration; JSON, Pydantic and citation/basic-grounding validation passed. A numeric
HTTP status was not captured and must not be invented.

This establishes **historical live communication, structured schema and synthetic
citation validation**. It establishes neither current remote availability nor
full live RAG quality. The earlier 512-token failure's precise cause remains unknown.
No Step 18 live request was made. Older provider/evaluation document statements
that live success is still pending are stale, not contradictory new test evidence.

`GeminiProvider` uses pinned `google-genai==2.31.0`, configured model,
`response_json_schema`, disabled automatic function calls, bounded timeout/output
and `HttpRetryOptions(attempts=1)`. The parser rejects non-STOP finish reasons,
empty/truncated/invalid JSON and schema errors; it excludes thought parts.
Safe diagnostic metadata contains categories/finish/usage rather than prompts,
keys, exception values or raw output. `AIProvider` remains SDK-independent; only
Gemini and the test fixture are implemented, not a catalog of interchangeable
production adapters.

Live defaults are off; enabling requires operator free-tier attestation, a key,
an allowlisted synthetic workspace and per-request synthetic confirmation. Default
daily generation limits are global/workspace/user **20/10/5**, concurrency **2**,
one request, zero retries, top-k **4**, ticket/context caps **4,000/6,000 characters**.
Atomic PostgreSQL reservations enforce cross-process generation budgets. Quota
errors remain terminal with bounded retry-after metadata; no fallback is enabled.
These gates do not query or enforce Google's billing plan and are not comprehensive
PII detection. Actual account tier/terms need operator confirmation before any
future separately authorized live use.

## Security findings

Severity describes plausible impact in the indicated deployment, not just a
scanner label. Priority/release gates are in [REMAINING_WORK.md](REMAINING_WORK.md).
No application fix is included in this audit.

| ID / severity | Evidence | Potential impact and recommendation |
| --- | --- | --- |
| **S1 High — conditional, full application** | `api/v1/auth.py::register` creates an active unverified email account; `api/v1/workspaces.py::add_member` selects that account by email, without proof of mailbox ownership. `schemas/auth.py` explicitly reports email unverified. | An attacker registering an intended invitee's unused email could receive access if an owner/admin later adds that email. This is a code-path finding with a conditional social/admin step, not an observed compromise or unauthenticated tenant bypass. Require verified ownership and identity-bound invitation acceptance before membership. Demo has no registration backend. |
| **S2 Medium — shared proxy abuse budget** | `services/auth.py::limited` keys IP buckets on `request.client.host`; Next proxy forwards no trusted client identity and local startup disables proxy headers. | Users behind one proxy share per-action 60/15-minute auth IP buckets (120 for anonymous CSRF), allowing nuisance lockout/poor fairness. Email buckets help but do not remove this. Define trusted ingress identity and independent account/tenant controls; reject spoofed forwarding headers. |
| **S3 Medium — cumulative resource abuse** | Upload size/extraction time/memory and AI/job concurrency are bounded, but `documents/service.py::upload` has no cumulative workspace byte/count quota; tenant creation/ticket writes do not provide a complete abuse policy. | Authenticated abuse can grow disk/DB or exhaust expensive processing despite individual request caps. Add aggregate quotas/admission controls and measure fairness; avoid presenting auth rate limits as whole-API protection. |
| **S4 Medium — retention/deletion incomplete** | Document deletion removes files/chunks/citation references, but `ResponseDraft.response_text`, reviews, activities and execution history remain; terminal checkpoint pruning is explicit. | Derived policy/customer content may survive deletion of its source. Define lifecycle/retention across records, files, checkpoints, logs and backups; implement auditable deletion/legal retention decisions before real data. No broad erasure guarantee exists. |
| **S5 Medium — inference trust boundary, mitigated** | `rag/context.py` pattern filters and `rag/prompt.py` quote/word/number checks are heuristics; output is rendered as text; human approval mandatory. | Negation, subtle injection or incomplete answers may satisfy mechanical checks. Keep exact-draft human review/no delivery, expand adversarial and relevance/completeness evaluation. Do not call citation validation a hallucination detector or PII guarantee. |
| **S6 Medium — production infrastructure prerequisites** | Local runtime DB role is database owner (not superuser); no deployed migration/runtime separation. `core/config.py` does not require DB/broker TLS. Local loopback authenticated broker is intentional. | Reusing laptop settings on public infrastructure could expose privileged transport/storage. Enforce trusted network boundaries, scoped runtime roles and verified TLS where traffic leaves the host. No currently exposed full backend was found. |
| **S7 Low — defense-in-depth CSP gap** | `apps/web/next.config.ts` adds CSP only in production demo mode; scripts/styles allow `unsafe-inline`. Inline handlers, external connects, frames and objects are blocked in demo tests. | Baseline policy limits origins but is not strict nonce-based XSS protection; full mode lacks this CSP. Evaluate a compatible full-app policy and nonce/hash strategy, preserving hydration and styles. No XSS exploit was established. |
| **S8 High upstream / development-only reachability** | Five npm audit entries in one lint dependency chain; details below. | Crafted glob patterns can crash development tooling. No affected runtime trace was found in Step 17A. Track upstream and isolate untrusted CI input; do not break Next.js compatibility to silence the audit. |
| **S9 Low — account enumeration and recovery gaps** | Duplicate registration returns 409, unknown/bad login 401; no mailbox reset flow or user session-revocation UI. | Registration can disclose account existence; users lack a complete compromised-account recovery path. Combine generic registration responses, verified recovery and session revocation with S1; assess privileged-account MFA under the deployment threat model. |

### Controls actually present

Passwords use Argon2id, server sessions use random tokens with hashed token storage,
expiry and rotation; production cookies use Secure/HttpOnly/host-only naming and
SameSite Lax. Mutations require CSRF, trusted Origin and allowed content types.
Permission checks include assignment restrictions, owner invariants and current
authorization after expensive work. UUID knowledge alone grants no tenant access.

Uploads use extension/content checks, bounded child extraction and private generated
storage keys with restrictive permissions and no-follow/regular-file checks.
Original filenames do not become filesystem paths. Tombstones stop reads during
failed deletion. This is not a malware scanner or a distributed object-store design.

Generation/reviews/checkpoints are tenant-scoped. Review binds an immutable draft
hash/version; changed sources/tickets invalidate approval. Workers read current
authorization and saved decisions rather than trusting resume payloads. Queue
serialization is JSON with an allowlisted task; checkpoint pickle fallback is off.

Application error responses/logs contain safe categories; request diagnostics use
route names/status/duration and correlation IDs rather than submitted content.
Sensitive responses are no-store. Infrastructure, terminal and dependency logs
still need deployment-level access/retention policy; application sanitization is
not a blanket claim about every operator's logging setup.

`.gitignore` excludes actual env files, private runtime/document/model directories,
credentials, databases, virtual environments, node_modules, build/test output and
logs; templates remain versioned. Fresh Step 18 history scanning found no tested
credential patterns in 285 reachable blobs. Step 17A also recorded exact configured
secret comparison. The current scan is pattern-based, not arbitrary secret/PII
detection; it did not read or print the API key. No unknown secret-free guarantee
is inferred from regex matches or from `.gitignore` alone.

### Development advisories

Reviewed the retained **2026-10-23 Step 17A** npm full/runtime audit reports (not a
new npm registry audit). Full: five high, zero other severities. Runtime: zero.
The dependency chain in `apps/web/package-lock.json` is:

| Package | Locked version | Relationship / runtime reachability |
| --- | --- | --- |
| `eslint-config-next` | 16.4.2 | Dev-only lint configuration |
| `@next/eslint-plugin-next` | 16.4.2 | Lint plugin inherits advisory |
| `fast-glob` | 3.3.1 | Lint glob expansion dependency |
| `micromatch` | 4.0.8 | Pattern dependency |
| `braces` | 3.0.3 | Vulnerable nested-pattern recursion |

The official [GHSA-vfj7-8cjw-p6xm advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm),
checked during this audit, lists affected versions through 3.0.3 and no patched
release. It describes stack exhaustion from deeply nested patterns. The audit's
suggested `eslint-config-next@14.2.35` is a breaking downgrade and was not applied.
Step 17A found these packages absent from all 16 Next production trace files.
There is no demonstrated request-to-package production path in the demo; build/CI
tools remain an exposure surface. “Runtime audit zero” does not mean the system is
vulnerability-free. No fresh comprehensive Python/transitive vulnerability audit
or external penetration test was performed in Step 18.

## Operations and commercial blockers

| Area | Implemented | Missing or unverified |
| --- | --- | --- |
| Hosting | Local API, Next, DB, owned broker, dispatcher/worker scripts; separate Vercel demo | Full-service target topology, persistent storage/compute capacity, TLS/network policy, reproducible hosted startup and rollback |
| Migrations | Alembic through `0010`; explicit PostgresSaver setup/version checks; additive preservation tests | Production-scale migration rehearsals, separate DDL/runtime roles, failure/rollback and backup coordination |
| Backups/restores | Durable local DB/checkpoints/files; outbox survives broker loss | No demonstrated independent DB + file + checkpoint backup/restore, off-host recovery, RPO/RTO or restore drill; local persistence is not backup |
| Files/models | Storage interface with private local adapter; verified pinned model snapshots | Shared durable file access or suitable object-store adapter for multiple hosts; encryption/credential/access policy and artifact distribution |
| Process management | Bounded RQ jobs, dispatcher reconciliation, safe lifecycle commands | Supervised service restart, deployment draining and OS reboot recovery exercises; manual terminals are not production supervision |
| Health/monitoring | `/health` liveness, `/ready` SELECT 1, safe diagnostics; `jobs.py health` checks workers/dispatcher/broker | Automated internal capability readiness, queue age/latency/error/capacity alerts, ownership/escalation, SLOs and incident exercises; do not expose private topology publicly |
| Resource/scaling | Per-request bounds, DB pools, atomic generation budgets and PG graph/job slots | Concurrent tenant load/fairness, accumulated storage budgets, DB saturation/partition behavior, cold worker ML load/memory; local semaphores alone do not establish cluster capacity |
| Recovery | Duplicate suppression, crash checkpoints, bounded processing retries and fail-closed ambiguous generation | Database loss, inconsistent file restore, disk-full, long partition/failover and production chaos drills |
| Privacy/lifecycle | Synthetic-only external generation gate, local files, safe app logs, explicit pruning | Real-data inventory, retention/deletion and access procedures, provider data-handling/region/contract review and incident policy; no legal-compliance certification |
| Release process | Lockfiles, explicit tests, reviewed private history, demonstrated demo deployment | No checked-in `.github` CI workflow; protected required checks/automated security gates not established by this audit |

Exact vector search and SQL aggregation are appropriate implemented baselines, not
measured large-tenant scaling solutions. Worker processes construct model dependencies
for execution, so cold-load/RSS costs must be measured before raising concurrency.
The API's SELECT 1 readiness can pass while models, checkpoints or workers are
unavailable; the separate worker health CLI exists but is not wired to alerts.

No conclusion about a commercial plan's present pricing/terms, regional legal
requirements or full provider data-processing suitability is made. Those need
explicit review for the intended users/data before a future launch. No purchase
is needed to implement and locally verify the proposed hardening work.

## Public presentation, repository access and documentation quality

The implemented demo architecture screen (`apps/web/src/components/demo/architecture.tsx`)
explicitly distinguishes authored classifications/drafts, keyword search, replayed
stages and browser session storage from real local ML/pgvector/LangGraph/RQ. It says
the full backend is not hosted in the demo and decisions send no messages. The
generation route is an unconditional 403 with no SDK or key lookup; the full API
proxy returns 404 in demo mode. No misleading live-model confidence is presented.

The source repository is **private**, confirmed by a fresh read-only GitHub metadata
request; default branch `main`. Recruiters without access can inspect the public
demo and browser-delivered frontend assets, not the Python source, private Git
history, tests, lockfiles or markdown reports. A private repository link alone is
not independently inspectable evidence for them.

Recommended portfolio strategy: retain private source for now, share the demo
alongside a separately reviewed case study/architecture diagram and short walkthrough,
and offer selected reviewer access where appropriate. Any public source release
needs a fresh history/secret/data/license review and explicit authorization; it is
not a prerequisite for a credible case study. Nothing was published in this step.

Strengths are the real local stack, failure-oriented tests, data-only classifier
artifacts, explicit score/fixture limitations and exact-draft authorization.
Limitations include synthetic-only evaluation, no commercial operations evidence,
no measured recruiter usability study and incomplete independent source access.

Documentation drift is a concrete maintainability finding: README and
PORTFOLIO_READINESS still describe Step 16 as undeployed, VERCEL_DEPLOYMENT names
the older release, AI_PROVIDERS/RAG_EVALUATION contain pending-live language, and
some step documents describe later implemented milestones as future work. Read
these as dated milestone records; this audit and the newest PROJECT_STATUS entry
are the current assessment. A later authorized documentation pass should clearly
separate history from current operating instructions. No broad rewrite was made.

## Unperformed work

No live Gemini study, new latency benchmark, commercial hosting, backup/restore
drill, production-scale load/partition test, real customer-data evaluation,
comprehensive penetration test, legal/privacy certification, physical MacBook-off
test, real-device/Safari or complete assistive-technology audit was performed.
Provider model/account availability and paid usage were not probed. The existing
five development advisories remain. These omissions are not passing checks.

The recommended next milestone is an explicitly authorized **full-application
security and recovery gate**: verified membership identity, isolated restoration,
runtime privilege boundaries and supervised health/abuse controls. Keep it local
and synthetic first; do not turn this audit into an implicit launch approval.
