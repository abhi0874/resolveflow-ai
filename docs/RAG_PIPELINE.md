# Response drafts and human review

Step 9 adds bounded synchronous RAG to the existing ticket detail page. Generation
uses local retrieval plus the configurable provider boundary. It does not install
LangGraph, Redis or workers and has no customer delivery, refund or account-action
capabilities.

## Request flow

1. Authenticate the server session and validate CSRF/Origin. Require document
   content permission and ticket write permission; support agents can generate
   or review only unassigned tickets or tickets assigned to them.
2. Load the tenant-scoped ticket, check its expected version and input size.
   Reserve an immutable generation ID under atomic concurrency/daily budgets.
3. Use the first 1,000 characters of title plus description for the existing local
   embedding and exact pgvector search. Preserve source IDs, scores and hashes.
   Do not regenerate document embeddings. Missing/stale embeddings cannot match.
4. Select up to four qualifying passages at the configured cosine threshold
   (default 0.30), deduplicated by the retrieval service. Exclude obvious instruction
   injection and sensitive patterns. Keep whole passages within the context budget.
5. Requests asking for personal payment/account status or explicit instruction
   overrides receive a local abstention. No usable evidence also yields an
   abstention without a generation call. Sensitive input fails safely.
6. Recheck current user/membership, ticket and sources, enforce cloud configuration,
   workspace allowlist and synthetic confirmation, then release database locks
   before the provider call.
7. Validate the structured output and cited evidence. Recheck authorization,
   ticket revision and every selected source after the call. Changes fail the
   generation without publishing response text.
8. Commit the draft and citations atomically. Review remains a separate,
   explicit human mutation.

The `grounded-support-v1` prompt separates trusted system instructions/output
requirements from JSON `CUSTOMER_REQUEST` and `RETRIEVED_EVIDENCE`. Both JSON
sections are untrusted data. No model tools exist.

## Output and evidence validation

The provider returns `response_text`, bounded statements with `chunk_id` and an
exact `supporting_quote`, `requires_human_review=true`, `insufficient_evidence`,
uncertainty notes and suggested next steps. Supported response text must equal
the statement texts joined by blank lines. Every statement must reference a
chunk actually supplied to this generation and quote text inside that chunk.
Source names, positions and page numbers come from authorized database records,
never the model.

Basic claim checks reject known completed-action assertions, sensitive identifiers,
instruction leakage, numbers absent from the quote, and low lexical overlap.
Untrusted model notes/next steps are replaced by bounded internal review guidance.
An insufficient-evidence result is replaced with a trusted abstention, preventing
claims from being smuggled inside that status.

These checks are conservative heuristics, not semantic entailment or comprehensive
prompt-injection detection. Valid IDs and exact quotes do not prove relevance or
truth; negation, misleading phrasing, multilingual attacks and subtle instructions
remain risks. Numeric paraphrases may be rejected. A human must inspect meaning,
policy applicability and completeness before approval. No automatic actions follow.

## Persistence and stale evidence

Migration `0007_response_drafts` adds:

- `response_drafts`: ticket/request IDs, ticket revision, provider/model/fixture
  identity, prompt version, selected source ID/hash/score manifest, generation
  state, validated response, review state, safe error, usage and measured duration.
- `draft_citations`: tenant-constrained chunk references, content hash, supporting
  quote and score, one row per response statement. Composite foreign keys prevent
  foreign-workspace references. Deleting chunks cascades these references.
- `draft_reviews`: one terminal decision per draft, actor, timestamp, reviewed
  revision and SHA-256 of the exact response text. Previous generations remain.

Existing tables/data are preserved. There is no API for editing generated text;
requesting revision records a decision and the user can generate a new draft.
Review's expected version prevents competing or repeated decisions. The API
maintains immutable text after generation; separate database runtime roles and
protection against privileged raw SQL writers remain future hardening.

Reads check current source content hashes, document processing status and ticket
revision. Missing/changed citations are omitted and marked stale. A saved citation
count detects deleted references. Approval is blocked if any cited source or the
ticket changed, evidence is insufficient, generation failed, or the draft was
already reviewed. Historical approval stays in the audit record but
`approval_current=false` when stale.

Failed/crashed requests retain an explicit failure state; there is no automatic
retry or hidden fixture fallback. Requests abandoned for two minutes are recovered
on the next generation request. That standalone request path is not a durable workflow engine; Step 10 composes
it inside the separate persistent graph described below.

## API

All routes share `/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}`.

| Method and suffix | Contract |
| --- | --- |
| `GET /response-config` | Safe model/fixture/readiness flags and input limit; no key |
| `POST /generate-response` | `{request_id: UUID, expected_ticket_version: positive integer, synthetic_confirmed: boolean}` |
| `GET /drafts?page=1&page_size=5` | Bounded paginated history |
| `GET /drafts/{draft_id}` | Validated text, current citations, status and review audit |
| `POST /drafts/{draft_id}/review` | `{expected_version: positive integer, action: approved|rejected|needs_revision}` |

Mutations require the existing trusted Origin and session CSRF token. Unauthenticated
requests receive 401; inaccessible workspaces/tickets/drafts receive 404; disallowed
roles receive 403; version/source conflicts receive 409; input/privacy checks use
422; budget/provider quota responses use 429; provider/model failures use safe 503.
Replaying a reserved request returns HTTP 200 with its persisted
`generation_status`, which may be `failed` or `generating`; this is not a claim
of generation success.

Owner/admin/support-agent readers with document content access can inspect drafts.
Viewer is denied all draft and configuration endpoints because generated text can
reveal private document content. Approving requires ticket editing permission and
the assignment rule above. Source retrieval, persistence, read and review queries
all retain workspace scope.

## UI and operational limits

The response assistant uses the real FastAPI backend through the same-origin
proxy. It shows explicit fixture labeling, loading/errors, bounded history,
plain-text responses/quotes, actual document links, provider/prompt/time metadata,
abstention/stale warnings and review controls. Approval labels explicitly say
internal approval; external action is never implied. A retry after uncertain
network failure reuses the request UUID. Proxy/client generation timeouts are
60 seconds.

No Markdown/HTML from the model is executed. The page supports keyboard controls,
system light/dark themes and narrow viewports. Browser tests use real auth,
PostgreSQL, document extraction, local embeddings and pgvector; only generation
is a labeled deterministic fixture. See [RAG_EVALUATION.md](RAG_EVALUATION.md),
[AI_PROVIDERS.md](AI_PROVIDERS.md) and [GEMINI_INTEGRATION.md](GEMINI_INTEGRATION.md).

## Step 10 integration

The new LangGraph workflow reuses this generation, reservation, citation and review
service. Shared `rag/context.py` provides the same input safety/abstention policy
and bounded deduplicated context selection for both entry points. Workflow retrieval
passes freshly authorized evidence into generation; it does not execute a second
semantic search or regenerate embeddings. The stable execution UUID becomes the
draft request ID. A saved draft is reused during recovery; an uncertain reservation
never causes a second provider request.

Migration 0008 adds nullable `draft_citations.statement_text`. Existing drafts remain
readable without a backfill; new drafts preserve exact validated statement boundaries
so multi-paragraph statements can be revalidated without guessing how to split text.
The workflow verification node reruns strict schema/citation/claim checks and the
human node checks the same saved review, revision, hash and current sources. There
is no second approval system. These checks still do not prove factual entailment.

The AI Workflow UI displays saved stages, evidence, recommendations and the existing
draft card. Rejection or a revision request closes that execution; deliberate new
generation needs a new review. Paused workflows survive process restart using actual
PostgreSQL LangGraph checkpoints. The original Response assistant remains usable.
Workflow proxy/client calls have a 120-second transport timeout; provider calls keep
their own shorter configured bound. See [AGENT_ORCHESTRATION.md](AGENT_ORCHESTRATION.md).
