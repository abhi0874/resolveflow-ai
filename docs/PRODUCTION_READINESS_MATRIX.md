# Production readiness matrix

Current assessment: **Step 20, 2026-10-25 (Asia/Kolkata)**. This supersedes the Step 18
matrix; [FINAL_TECHNICAL_AUDIT.md](FINAL_TECHNICAL_AUDIT.md) remains a dated audit.
Source review and fresh local tests support the claims below. No deployment or
external-service activation occurred. No readiness percentage or launch date is implied.

| Area | A. Local full application | B. Public recruiter demo | C. Commercial production SaaS |
| --- | --- | --- | --- |
| Decision | Verified for tested local synthetic journeys | Existing synthetic portfolio deployment; fresh local demo regressions passed | **Not ready** |
| Deployment | Mac-hosted API, DB, files/models, broker and workers | Existing standalone Next.js Vercel deployment; Step 20 did not change it | Full backend topology not deployed or validated |
| Persistence | PostgreSQL, private files, real graph checkpoints and job outboxes | Tab-local synthetic session storage | Independent durable storage, retention and operational ownership required |
| Identity | Session/CSRF/RBAC, invitations and local Mailpit verification/recovery tested | No backend login, secret or customer database | External email acceptance/deliverability, invitation transport and rollout still open |
| ML / retrieval | Actual scikit-learn and local embeddings/pgvector | Authored categories and keyword search | Representative evaluation and capacity gates missing |
| Generation | Configurable Gemini adapter; routine live mode off, deterministic test provider | Precomputed drafts; live generation rejected | Real-data policy and broader separately authorized quality study needed |
| Approval | Exact revision/hash, current sources/permissions, durable review pause | Local example decisions only | No customer delivery connector or external action semantics |
| Recovery | Real local encrypted backups and isolated restores; scheduler intentionally inactive | Demo can reset its own synthetic state | Independent key custody, off-host restore, chosen/tested RPO/RTO missing |
| Fresh Step 20 evidence | 317 backend, 29 full browser tests; full build/type/lint; migration/checkpoint checks | 16 local demo tests and demo build | No production load, failover, external email or new hosted acceptance test |

## A. Local full application

Verified capabilities include registration/login/logout, shared auth rate limits,
tenant/role/assignment enforcement, single-use identity recovery, ticket histories,
private documents, classifier suggestions, actual semantic retrieval, fixture RAG,
LangGraph pause/resume, queue recovery and authorized analytics. Migration **0012**
matches code head; read-only Alembic metadata comparison found no schema drift.

The fresh browser harness runs actual API/database/model/broker/worker/Mailpit services.
A Step 20 fix ensures inherited broker/queue settings cannot override its disposable
resources. A run with a deliberately unreachable inherited broker URL passed all 29
scenarios. No development records or credentials were reset.

Limitations remain: Chrome-focused tests, synthetic evaluation, synchronous bounded
document ingestion, exact vector search without large-corpus scaling evidence,
manual service startup and no comprehensive screen-reader/real-device audit. The
public readiness endpoint checks DB connectivity, not all worker/model capabilities.
No new live Gemini request occurred; routine generation can correctly return
`ai_not_configured` when live inference is disabled.

There is no blocker to continued operator-controlled local development or portfolio
preparation. Deferred backup activation is an explicit user choice, not a Step 20 gate.

## B. Public recruiter demo

The existing deployment is [resolveflow-ai-rosy.vercel.app/demo](https://resolveflow-ai-rosy.vercel.app/demo).
Step 17B release `759e5f87751cb49c1dd117755dcbdc08b14e31af` is the recorded deployed
identity. This is historical deployment evidence; Step 20 ran local production builds
and browser checks, not a fresh hosted availability or account-configuration audit.
No push or deployment was performed.

The architecture screen accurately distinguishes authored examples from actual local
ML, vector retrieval and graph execution. Tests cover local edits/reset, source links,
review restrictions, analytics, navigation, narrow layouts, keyboard access, automated
accessibility checks, CSP and blocked API/live-generation paths. No Gemini key is needed.

Internet/JavaScript and browser storage behavior remain dependencies. Automated
accessibility tests are not certification; real devices and screen readers remain
unverified. The demo CSP is baseline protection and allows inline hydration/styles.
No SLA, billing guarantee, commercial hosting approval or physical MacBook-off test
is inferred. Source remains private; new portfolio documents remain local until
separately approved publication.

## C. Commercial production SaaS

The substantial implemented foundation does not establish real-user operating readiness.
Before a commercial release, the following need explicit scope and acceptance evidence:

- External account-email delivery, verified sender/transport/inbox behavior and a
  production invitation delivery path. Local proof is rejected in production;
  invitations currently fail closed there. MFA/session-management needs risk review.
- Independent encrypted backup bytes and independently recoverable key custody,
  off-host restore/cutover exercises, monitoring and agreed RPO/RTO. Local restore
  timings are not production recovery objectives. Scheduling remains deferred.
- Full API/worker/database/file/model hosting, service supervision and drain/restart
  procedures, runtime/migration role separation and private/TLS infrastructure.
- Trusted ingress attribution and fair auth budgets, cumulative storage/resource
  quotas, concurrent tenant capacity evidence and operator-owned alerts.
- Retention/deletion/privacy policy covering derived drafts, checkpoints and backups;
  representative adversarial retrieval/generation quality with human assessment.
- Stronger full-mode CSP and broader browser/accessibility/security testing.
  No external penetration test, full Python vulnerability audit or arbitrary-partition
  chaos certification was performed here.

## Dependency assessment

Fresh npm full and production-only audits on 2026-10-25 both returned **zero findings**
for the existing lockfile. No dependency upgrade/downgrade was applied. The earlier
five high entries concerned `braces@3.0.3` → `micromatch@4.0.8` → `fast-glob@3.3.1` →
`@next/eslint-plugin-next@16.4.2` → `eslint-config-next@16.4.2`, a development lint chain.
The historical report and its exposure analysis are preserved in the Step 18 audit.
A changed registry result is not proof that a code fix landed or that all dependencies
are secure. No breaking change was made solely to remove an advisory.

See [PORTFOLIO_EVIDENCE.md](PORTFOLIO_EVIDENCE.md) for reproducible evidence and
[REMAINING_WORK.md](REMAINING_WORK.md) for priorities. All operational expansion,
external delivery, live inference and publication still require separate authorization.
