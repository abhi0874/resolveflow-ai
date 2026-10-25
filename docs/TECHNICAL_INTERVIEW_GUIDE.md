# Technical interview guide

Answers grounded in the implemented ResolveFlow AI code, reviewed 2026-10-25.
Use the source paths to explain mechanisms and the limits alongside them.
Paths beginning with a module name are relative to `apps/api/src/resolveflow/`.

| Interview question | Implementation-grounded explanation and tradeoff |
| --- | --- |
| What does RAG add here? | `rag/service.py` retrieves authorized policy chunks, prepares bounded context, generates a structured draft and saves citations. It adds source context without retraining the generator. It cannot guarantee relevance, completeness or factual entailment. |
| What is an embedding? | `retrieval/provider.py` maps text to a normalized 384-dimensional vector using a pinned local MiniLM model. Similar vectors can represent related meanings. Similarity is not proof that a passage answers a question; embedding-space identity must match stored vectors. |
| How does vector search work? | `retrieval/service.py` calculates cosine distance through pgvector, filters by workspace/model/source freshness, deduplicates and ranks in SQL. Exact search is implemented; HNSW/ANN and reranking are not. Larger corpora need measured recall/latency tradeoffs before a change. |
| Why PostgreSQL and pgvector? | Relational records, tenant constraints and vectors share the existing persistence layer. This simplifies provenance joins and consistency. It does not make exact search scalable without workload evidence, nor replace access checks with a vector index. |
| Is classification really ML? | `ml/training.py` fits scikit-learn TF-IDF and logistic regression on training records; `ml/classifier.py` calls `predict_proba`. Priority is a separate rule-based stage. Neither hosted example categories nor priority rules should be presented as classifier predictions. |
| How is evaluation leakage controlled? | `ml/dataset.py` groups paired scenarios before splitting; vocabulary/IDF/model fitting uses training rows only. Frozen reports record hashes, split membership and parameters. Hand-authored conceptual overlap and a tiny synthetic corpus still limit generalization. |
| What does the score mean? | The classifier's uncalibrated score supports a thresholded suggestion; low scores and zero-vocabulary inputs abstain. Threshold 0.45 suggested only 13/56 held-out examples. Human acceptance is always required; do not call it calibrated certainty. |
| Why not load a pickle model? | `ml/artifact.py` validates bounded data-only JSON and reconstructs the supported estimator. This reduces arbitrary-code deserialization risk. It constrains portability to the validated model/library contract; it is not a generic artifact format. |
| Why LangGraph rather than a long request? | `workflows/graph.py` expresses seven typed stages and conditional failure exits; PostgreSQL persists progress and a real interrupt. RQ runs the graph outside the request. Persistence brings versioning, authorization and recovery responsibilities beyond ordinary function calls. |
| Are these autonomous agents? | They are specialized logical workers in a bounded acyclic graph. Classification, priority and retrieval use deterministic/local services; generation may invoke one provider. There is no model-chosen tool loop or collection of independently reasoning agents. |
| What survives a restart? | Application rows, drafts/reviews, workflow state and PostgreSQL checkpoints. `workflows/storage.py` builds tenant/execution thread IDs server-side, checks schema version and disables pickle fallback. Restart recovery is different from recovering a lost database. |
| How is human approval enforced? | Review persists the exact draft version/hash. Resume ignores client-supplied decisions, loads the saved review and checks current authorization, ticket revision and evidence. Changed sources invalidate approval. Internal completion sends no customer message. |
| How is prompt injection handled? | `rag/prompt.py` separates instructions from untrusted JSON, exposes no tools, validates schema/quotes and applies conservative patterns/claim checks. Plain-text rendering and human review constrain impact. Regex and lexical overlap cannot detect every injection or prove entailment. |
| How can the generator be replaced? | Implement the SDK-independent `AIProvider` contract, preserve output/error semantics, configure selection and rerun contract/quality tests. Embeddings have their own interface. Only Gemini and the test fixture are implemented; portability is architectural, not universal compatibility. |
| What bounds Gemini usage? | Configuration/free-tier/synthetic gates, shared database budgets, bounded inputs/context/output, 25-second default timeout and SDK attempts=1. Quota errors are terminal, with no paid fallback. An operator attestation is not an API-enforced billing cap. |
| How are API transactions managed? | Request-scoped SQLAlchemy sessions, explicit service commits and rollback-on-error; bounded pools and query timeouts. Ticket versions reject stale edits; workspace row locks serialize sensitive membership changes. Provider work releases locks, then publication rechecks mutable facts. |
| What makes jobs durable? | `jobs/service.py` commits execution/job acceptance; `dispatch.py` reconciles into RQ; `worker.py` uses delivery IDs and PostgreSQL ownership locks. A lost broker can be repopulated from the outbox. There is no cross-system atomic commit or universal exactly-once execution. |
| Can retry duplicate a draft? | Generation uses a stable execution/request identity and a unique reservation. Recovery reuses a completed draft; an ambiguous unfinished generation fails closed. Tests verify duplicate delivery does not duplicate saved drafts. Remote provider execution may still be uncertain after interruption. |
| How does authentication work? | Argon2id passwords; hashed opaque server-session tokens, expiry, rotation and logout; production Secure/HttpOnly/host-only cookies. CSRF tokens and trusted Origin checks protect mutations. No browser-held JWT, MFA or managed identity service is implemented. |
| How does password recovery revoke access? | `services/identity.py` locks the user/token, validates purpose/address/version/expiry, changes the password hash, increments credential version and deletes sessions. It invalidates other identity tokens and outstanding invitations, preserving membership roles. Local Mailpit proves only local delivery. |
| Where is multi-tenancy enforced? | API/services require current membership and role, resource queries include workspace predicates, composite relationships prevent foreign-tenant associations, and workers reauthorize. Database RLS is absent; privileged direct SQL remains a trusted boundary. |
| How are uploads protected? | `documents/` validates size/type/encoding, extracts in bounded child processes, uses generated private paths and retains source provenance. Journal/tombstone state supports interrupted operations. No OCR, comprehensive malware scanning or aggregate tenant storage quota is claimed. |
| What do analytics measure? | `analytics/` aggregates authorized workspace SQL with explicit UTC cohorts and denominators, distinguishing current queue state from creation cohorts. Missing history stays unavailable. It does not invent model-performance or business-impact metrics. |
| What does backup verification prove? | `backups/` captures a quiesced DB snapshot plus checksummed referenced files, encrypts with restic and validates isolated restores. Same-Mac backups do not protect against machine loss. Scheduling, independent key custody and off-host recovery remain deferred. |
| Why is the hosted demo different? | Vercel runs standalone Next.js with synthetic fixtures, browser session storage, keyword search and authored workflow replay. No FastAPI, PostgreSQL, ML, queue or live Gemini runs there. It demonstrates interaction design while local tests establish backend behavior. |

## Short answers for recruiter follow-ups

- **Why traditional ML for classification?** A bounded seven-label problem supports
  an inspectable TF-IDF/logistic-regression baseline with local inference, grouped
  evaluation and no per-ticket generation call. Synthetic coverage is limited;
  a more complex model would need a measured benefit on representative data.
- **What does the orchestrator do?** It routes typed state through seven specialized
  stages, terminates failed work, checkpoints progress and pauses for an authorized
  review. RQ runs it outside the HTTP request. Nodes are not seven separate LLMs.
- **How do you prevent hallucinations?** I reduce risk using bounded retrieved
  evidence, structured output, quotation/source checks, abstention and human review.
  I cannot guarantee prevention: citation validity is not semantic correctness.
- **What happens when Gemini fails?** The adapter returns a typed failure; generation
  records failure and the graph exits safely. There is no automatic paid fallback or
  unbounded retry. An ambiguous interrupted reservation is not silently regenerated.

## Scenarios worth explaining at a whiteboard

1. **A document changes during generation.** Trace reservation → unlocked provider
   call → current-source/hash checks → safe failure. Explain why a citation ID alone
   is insufficient and why approval must recheck evidence again later.
2. **A worker dies after draft persistence.** Trace stable draft ID → checkpoint
   recovery → reuse. Contrast the ambiguous reservation case, which fails closed.
3. **A broker loses all messages.** PostgreSQL still owns accepted work. The
   dispatcher republishes under delivery identities; worker locks and state checks
   reject stale messages. State the tested limits around partitions and capacity.
4. **A user loses membership during a long operation.** Trace server authorization
   and publication/review rechecks. Do not claim UI permission controls protect data.
5. **The laptop is lost.** Local restic encryption does not supply independent bytes
   or a recoverable key. Describe the unconfigured operational requirements honestly.

## Evidence and next improvements

Use [PORTFOLIO_EVIDENCE.md](PORTFOLIO_EVIDENCE.md) for fresh counts and dated metrics,
not a memorized historical test count. The full suite uses actual local services and
fixture generation; it is not a fresh Gemini quality study. Automated Chrome/axe checks
are not full accessibility certification or a penetration test.

Prioritize external identity/invitation delivery, independent recovery, least-privilege
runtime roles, supervision/alerts, trusted ingress and cumulative quotas, retention
and representative quality/load studies before a commercial launch. Do not claim
those are implemented merely because they appear in a roadmap.
