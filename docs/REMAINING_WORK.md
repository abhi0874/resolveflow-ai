# Remaining work after Step 20

2026-10-25. These are recommendations, **not authorization to begin Step 21**.
The [readiness matrix](PRODUCTION_READINESS_MATRIX.md) separates local development,
the public synthetic demo and commercial SaaS. The original findings remain in
[the dated Step 18 audit](FINAL_TECHNICAL_AUDIT.md).

## Completed local foundations

Identity-bound invitations, account email verification/recovery, session invalidation,
local Mailpit delivery, development migrations through 0012, encrypted local backups
and populated isolated restores are implemented and tested. Step 20 preserves that
work in a reviewed local checkpoint and adds current architecture/portfolio materials.
The browser test harness now gives owned broker settings precedence over inherited
settings. Do not reimplement these foundations merely because older audit findings
describe their earlier absence.

## P0 — prerequisites for real-user commercial operation

| Work | Required acceptance evidence | Current boundary |
| --- | --- | --- |
| External identity delivery and rollout | Approved sender/transport, real controlled mailbox receipt, verified-only legacy-account rollout and production invitation issuance/acceptance | Local Mailpit works; external SMTP unverified; production invitation transport absent and issuance fails closed |
| Independent recovery | Separately recoverable encryption credential, independent encrypted bytes, restore on another host, source/config/model reprovisioning, ownership/monitoring and chosen RPO/RTO | Local encryption and isolated restore work; scheduler intentionally inactive; key-copy confirmation/off-host recovery pending |
| Production runtime boundary | Approved topology, runtime cannot perform unauthorized DDL, private DB/broker transport, supervised restarts/draining, rollback and capability checks | Local owner role/manual terminals; full backend not hosted |
| Real-data operating policy | Inventory and approved provider handling, retention/deletion/export across source/derived records/checkpoints/backups, incident ownership | Synthetic-only inference gates retained; no broad erasure or compliance claim |

None requires activating a paid service to begin local design/tests. Hosting/storage
or email providers must be chosen separately with explicit cost and access review.
Deferred backup activation does not block local development or portfolio preparation.

## P1 — focused engineering and measurement

| Work | Why it matters | Acceptance approach |
| --- | --- | --- |
| Trusted ingress and aggregate quotas | Proxy IP budgets can affect fairness; individual upload/AI bounds do not cap accumulated tenant storage | Reject spoofed forwarding headers, test two-user fairness and concurrent quota boundaries; measure before choosing production caps |
| Capability health and alerts | DB SELECT 1 is not model/checkpoint/worker readiness | Internal schema/model/queue-age/freshness checks, assigned thresholds and owned failure/recovery exercises |
| Representative ML/RAG evaluation | Small synthetic results and quote matching do not prove customer answer quality | New independently reviewed corpus, predeclared quality criteria, per-category errors, answer completeness and adversarial/no-answer cases; live calls need separate budgets/approval |
| Data lifecycle | Deleting a source does not erase all derived response/review/history content | Explicit retention and deletion semantics with traceable synthetic-marker tests and reviewed backup policy |
| Account controls and abuse | Recovery is implemented; broader session-management, privileged-account MFA and sustained-abuse evidence are not | Threat-driven scope, token/session race tests and verified identity UX; preserve fail-closed production policy |
| Full-mode CSP and accessibility | Demo CSP and Chrome/axe checks are bounded evidence | Compatible nonce/hash strategy, full-app hydration tests, real-device/Safari and screen-reader review |
| Dependency and release checks | Registry audit results change; current npm zero findings is not a blanket security guarantee | Preserve lockfiles, repeat scoped audits at release; independently assess Python dependencies and CI permissions without enabling unreviewed services |

## P2 — performance and product scope, only after measurement

Measure cold worker model-load/RSS, concurrent tenant fairness, exact-vector-query
scale and SQL analytics under realistic loads before adding caches, ANN indexes,
reranking or another service. Explore OCR, shared object storage and customer delivery
only as separately authorized product work. Customer sends need explicit exact-draft
authorization and retry/idempotency semantics; approval currently sends nothing.

## Portfolio next actions

The local case study, diagram, recruiter walkthrough, interview guide and evidence
sheet are ready for review. The existing public demo can be discussed with its
synthetic boundary intact. Source is private; publishing these materials, granting
reviewer access, pushing the local branch or triggering Vercel requires separate
approval. No customer adoption, revenue, uptime or unsupported improvement figures
should be added to a resume.

Step 20 ends at its local checkpoint. No further milestone, external SMTP, off-host
storage, backup schedule, deployment or live Gemini inference is activated.
