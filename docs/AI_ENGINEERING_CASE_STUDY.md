# ResolveFlow AI: accountable support drafting

Step 20 engineering case study, 2026-10-25. This is a portfolio implementation using
synthetic evaluation data, not a report of customer adoption or commercial impact.

## Problem and product objectives

Support triage combines different decisions: categorizing a ticket, locating an
applicable policy, drafting a response and deciding whether that response should
be approved. A fluent answer alone does not establish correct evidence, current
permissions or authorization to act. ResolveFlow separates these decisions and
records the state needed to inspect and recover them.

The objectives are to make classification suggestions reviewable, retrieve actual
workspace evidence, constrain generation, preserve exact-draft human approval and
recover accepted background work. The implemented product manages tickets,
documents and internal review; it does not contact customers or execute account actions.

## Design decisions grounded in the implementation

Next.js provides the typed interface and same-origin API proxy. FastAPI services
own authorization and domain operations. PostgreSQL stores business data, vectors,
job outboxes and graph checkpoints. This avoids introducing another search database
or treating a broker as the durable source of truth. Dedicated RQ workers handle
long-running graph execution; the hosted demo needs only Next.js and browser state.

Provider-neutral contracts isolate generation and embeddings. Gemini's SDK belongs
inside its adapter; changing providers still requires a new adapter, configuration
and contract/quality evaluation. No claim is made that arbitrary models can be swapped
without testing. [Architecture overview](SYSTEM_ARCHITECTURE_OVERVIEW.md) maps the
actual modules and trust boundaries.

## Traditional ML classification

`ml/training.py` fits TF-IDF word features and logistic regression. The application
performs real scikit-learn inference, not keyword labeling or a fixed answer table.
Training is an explicit offline operation. Startup loads a selected immutable model;
missing or invalid artifacts fail safely without retraining or disabling ordinary
account/ticket functionality.

The model is stored as validated data-only JSON with vocabulary, IDF, coefficients,
classes and provenance. It does not deserialize arbitrary pickle/joblib objects.
Predictions report scores and uncertainty, with abstention below threshold or for
zero-vocabulary input. Scores are not calibrated probabilities of business correctness.
The user must explicitly accept a category through the authorized versioned ticket API.

## Dataset and evaluation methodology

The frozen `ticket-classification-v1` corpus has 280 synthetic examples across seven
balanced labels and 140 paired scenario groups. Group-stratified splits contain
168 training, 56 validation and 56 test records. Paired phrasings stay together;
vocabulary/IDF and coefficients are fitted only on training rows. This guards against
the tested leakage paths, not conceptual overlap in hand-authored scenarios.

The saved held-out result is 44/56 correct, accuracy 0.785714 and macro F1 0.784580.
At the predeclared 0.45 threshold, only 13/56 test cases receive a suggestion; 43
abstain. These are tiny synthetic results, not real-world accuracy. Step 20 reloaded
the existing baseline and reproduced its recorded evaluation without replacing or
retraining it. See [ML evaluation](ML_EVALUATION.md) and its JSON provenance reports.

## Embeddings, retrieval and evidence

The local pinned `all-MiniLM-L6-v2` adapter produces normalized 384-dimensional
vectors. Stored chunks retain their document identity, position/page metadata and
content fingerprints. Indexing checks model-space compatibility; partial replacement
fails inside a savepoint so the prior valid index is preserved.

Retrieval executes exact cosine ranking in pgvector with workspace, source-status,
model-space and hash filters in SQL. It returns real stored passage text and IDs,
not model-invented citations. Exact search is appropriate for the measured small
corpus; no large-scale ANN performance claim is made.

The frozen 14-document, 24-query experiment records Recall@5 and MRR@5 of 0.928571
on 21 answerable queries, with a hit on 20/21 and three no-answer cases abstaining.
The [retrieval report](RETRIEVAL_EVALUATION.md) also records the weaker keyword baseline
and specific misses. A vague billing request was incorrectly rejected; a teammate
access query ranked an irrelevant passage first. These misses motivate a separately
versioned evaluation, not tuning against the frozen test set.

## Gemini and RAG

The RAG service reserves generation under shared PostgreSQL budgets, selects bounded
passages, separates untrusted ticket/evidence JSON from instructions and invokes
`AIProvider`. The Gemini adapter uses the configured `gemini-3.6-flash` model,
structured JSON schema, minimal thinking, a 1,024-token default output cap, 25-second
timeout and zero automatic retries. Live/free-tier/synthetic-workspace gates remain
required. There is no paid or fixture fallback after a failed live call.

Validation rejects malformed or unsuccessful responses, missing fields, foreign
citations and quotations absent from supplied chunks. Basic numeric/lexical checks
and source freshness checks add constraints. None is a semantic entailment proof,
comprehensive prompt-injection detector or DLP system. Text is rendered escaped,
and human approval remains mandatory.

One explicitly approved historical synthetic call on 2026-10-20 returned finish
`STOP` and passed JSON, Pydantic and citation checks. That is transport/schema evidence,
not broad answer-quality evidence or present provider availability. Step 20 made no
live calls. The frozen deterministic RAG evaluation had seven valid cited answers
and five expected abstentions, but only three of seven answers covered all required
terms. Mechanical validation and answer completeness are different quality dimensions.

## Orchestration and specialized workers

The actual LangGraph `StateGraph` has seven stages: classification, rule-based
priority, retrieval, context selection, generation, verification and approval.
These logical workers call existing application services; they are not seven
independent language-model agents. Only generation may call Gemini. Failure edges
terminate execution and recursion is bounded; no autonomous tool-selection loop exists.

PostgreSQL checkpoints persist transitions and a real approval interrupt. The state
stores references, hashes and bounded summaries; application services remain the
source of truth for current document content and saved decisions. On resume, the
worker validates the exact response hash/revision, source/ticket freshness and current
permissions. A saved decision survives a failed resume request and can be resumed later.

## Background reliability and human control

An accepted execution and its job commit together before broker publication. A
dispatcher reconciles PostgreSQL into Valkey/RQ identifier messages. Session advisory
locks, delivery UUIDs and phase attempt limits reject competing/stale work. Recovery
reuses the stable draft reservation. If a process dies around an uncertain generation,
it fails closed instead of assuming another provider call is free or harmless.

Tests exercise broker replacement, killed test workers, checkpoint recovery and
repeat delivery without duplicate persisted drafts. This is at-least-once transport
with application idempotency, not a universal exactly-once guarantee. Approval is
an internal state change, never permission to send an altered or newly generated draft.

## Multi-tenant identity and data security

Server-side sessions use hashed opaque credentials and Argon2id passwords. Mutation
routes enforce CSRF and exact trusted origins. Central workspace permissions, scoped
queries, assignment restrictions and composite relationships protect private resources;
workers and expensive operations recheck authorization. Hiding a control is not access
control, and application isolation is not PostgreSQL RLS.

Local email verification and password recovery use expiring single-use hashed tokens,
credential versions, revocation and a durable email outbox. Mailpit exercises real
local SMTP delivery; external production delivery and production invitation transport
remain unverified/unimplemented operational gates. Production rejects local proof.
Private storage uses generated keys, bounded extraction and controlled filesystem access.

## Testing, operations and lessons

[Portfolio evidence](PORTFOLIO_EVIDENCE.md) records the fresh Step 20 test counts and
commands separately from historical ML/retrieval/live-provider measurements. Tests
run against marked disposable PostgreSQL databases, owned brokers, real local models,
Mailpit and deterministic generation. Full and demo builds are verified separately.

Encrypted local backups and isolated populated restores are implemented. Automatic
scheduling is intentionally deferred; no off-host recovery or production RPO/RTO is
claimed. Other remaining gaps include trusted ingress fairness, aggregate quotas,
retention, stricter CSP, supervised services, independent backups, least-privilege
production roles and representative load/adversarial quality studies.

The main engineering lessons are concrete: a valid citation can still accompany an
incomplete answer; durable queue acceptance differs from successful execution;
a checkpoint is not a backup; current authorization matters again after slow work;
and a useful public demonstration need not pretend to host the complete backend.
Step 20 also fixed a browser-test environment precedence bug so inherited broker
settings cannot redirect its owned test traffic. These boundaries make the project's
claims inspectable without inventing customer outcomes or operational guarantees.
