# ResolveFlow AI project handoff

ResolveFlow helps a support agent classify a ticket, retrieve policy evidence and review an exact response draft. Recruiters can explore tickets, citations, approvals and analytics in the [public showcase](https://resolveflow-ai-showcase.vercel.app/). Use the [GitHub repository](https://github.com/abhi0874/resolveflow-ai) for the full local implementation. Running or using the project must require no hosting subscription, paid model or billing account.

## What runs where

| Runtime | Source and data flow |
| --- | --- |
| Public demonstration | Next.js, React, TypeScript and Tailwind in `apps/web`. Browser-local synthetic edits and precomputed workflows. Demo mode rejects private API and model execution. It stores no persistent personal accounts. |
| Account application | Next.js full mode forwards same-origin API requests to Python/FastAPI. PostgreSQL holds identities, revocable sessions and workspace membership. FastAPI checks CSRF and workspace permissions. Private files are outside the web root. |
| ML and retrieval | scikit-learn word TF-IDF and Logistic Regression suggest one of seven categories. MiniLM encodes queries and document chunks. pgvector searches authorized workspace documents. Gemini generation is behind a server-side adapter. Routine execution uses fixtures. |
| Work and review | A PostgreSQL job outbox feeds RQ/Valkey. LangGraph persists checkpoints and pauses for a human decision on the exact draft revision. Approval is recorded internally. A dispatcher and worker are required for asynchronous jobs, including email. |

## Evaluation evidence

| Measurement | Result and scope |
| --- | --- |
| Active baseline-v1 | 44/56 (78.57%), macro-F1 0.7846 on the original synthetic held-out split. [Evaluation](evaluation/classifier-v1-evaluation.json) |
| Matched research comparison | On the same 210 synthetic tickets, frozen V1 scored 142/210 (67.62%), macro-F1 0.6585. Inactive V2 (word TF-IDF, MiniLM and Logistic Regression) scored 183/210 (87.14%), macro-F1 0.8701. Warm CPU inference median/p95 was 0.194/0.210 ms for V1 and 3.102/4.792 ms for V2, excluding HTTP and database work. [Counts, attribution and hashes](evaluation/PUBLIC_EVIDENCE.md) |
| Retrieval | MiniLM vs keyword TF-IDF on 21 answerable questions: Hit@1 19 vs 11, Hit@5 20 vs 19, MRR@5 0.9286 vs 0.6762. Three unsupported questions were assessed separately. [Retrieval evidence](evaluation/retrieval-v1.json) |
| RAG | Deterministic answers with real retrieval: 7/7 citation-valid, 5/5 expected abstentions, 3/7 complete against required terms. Citation validity alone does not establish answer quality. [Fixture evaluation](evaluation/rag-v1.json) |

No independently labeled customer benchmark or hosted inference latency is established. Later inactive experiments and local-only evidence hashes are indexed in the [public evidence ledger](evaluation/PUBLIC_EVIDENCE.md). Do not publish private binaries, notebooks, raw recovery evidence or credentials.

## Identity and recovery

Migrations 0011–0012 introduced invitations and verified email recovery. Revisions 0013–0017 add Google identities, profile settings, durable invitation delivery, account erasure and independent journal binding, respectively. The expansion revisions were exercised on fresh disposable databases. No application to persistent development or production databases was verified for 0013–0017.

Google uses PKCE, state, nonce and the provider subject. An email match alone cannot link accounts. Users can update their display name and picture, inspect sign-in methods, and verify changes to their email or password. Deletion requires fresh password or signed Google authentication-time evidence, typed confirmation and a one-use session-bound challenge. It revokes sessions and removes eligible personal records. ResolveFlow leaves the external Google account alone.

Sole owners of shared or populated workspaces must resolve ownership before deletion. Shared records survive. The system tracks invitation ownership before file delivery, checks hashes before cleanup and retains ambiguous files for private manual review. Encrypted backups can temporarily contain deleted data. The supported restore path stays quarantined while the independent journal, witness, trusted seal and file holds are reconciled. A reconciled copy still requires a separate release decision. [Recovery operations](BACKUP_OPERATIONS.md#account-deletion-recovery)

## Continuing from another assistant

Start with the [quick start](AI_QUICK_START.md), [release record](PROJECT_STATUS.md), [architecture](ARCHITECTURE.md) and [account expansion plan](ACCOUNT_EXPANSION_PLAN.md). The source development branch was `codex/step29a-ml` at `4930fb0` with unpublished research and other local changes. Use a fresh checkout of public main and preserve that separate worktree. Inspect current refs and deployments before quoting a current identity. Use [the starter prompt](NEW_ACCOUNT_STARTER_PROMPT.md) to transfer context without secrets.

The public portfolio and private local stack are the zero-cost operating model. Live hosted accounts, paid infrastructure, external SMTP, real Google claims, off-host restore and commercial operating controls have separate acceptance requirements. Optional model improvements or a separately verified free hosting proposal do not change the public demo. [Cost decision](ZERO_COST_HOSTING.md)
