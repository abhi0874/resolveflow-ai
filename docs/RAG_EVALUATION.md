# RAG evaluation — synthetic v1

Measured locally on 2026-10-20. Machine-readable results are in
[evaluation/rag-v1.json](evaluation/rag-v1.json). Scenarios are versioned in
`data/synthetic/rag-v1/scenarios.json` and reuse the 14 synthetic documents in
`data/synthetic/retrieval-v1/corpus.json`. Both file hashes are recorded.

This is a **pipeline/fixture evaluation, not Gemini answer-quality evidence**.
It runs actual uploads/extraction, local Sentence Transformers, pgvector,
authenticated HTTP routes, citation validation and persistent drafts in an
ownership-checked disposable database. Generation uses
`fixture/deterministic-v1`, which copies a bounded sentence from the best passage.
No Google request occurs.

## Reproduce

With the pinned local embedding model installed and PostgreSQL running, from
`apps/api`:

```bash
UV_CACHE_DIR=../../.cache/uv uv run python scripts/evaluate_rag.py --output ../../docs/evaluation/rag-v1.json
```

The evaluation sets isolated test request budgets to accommodate the dataset.
It never changes application data or invokes a paid service. Routine full backend
tests also run the evaluation without overwriting its checked-in result.

Configuration: `all-MiniLM-L6-v2` at pinned revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, CPU, 384-dimensional vectors,
exact cosine search, minimum similarity 0.30, top-k 4, 6,000 context characters,
1,024 output-token setting and prompt `grounded-support-v1`.

## Observed results

| Measurement | Observed result | Interpretation |
| --- | --- | --- |
| Answerable requests | 7 | Refund, cancellation, troubleshooting, recovery, uploads, invoices, support hours |
| Expected-source retrieval hit | 7/7 (100%) | At least one expected source among selected context |
| Citation validity | 7/7 cited drafts (100%) | Actual supplied chunk and exact source quotation |
| Extractive support proxy | 7/7 (100%) | Fixture output contains its copied quote; not semantic grading |
| Required-term completeness | 3/7 (42.9%) | Crude case-specific term coverage; partial answers remain |
| Expected abstentions | 5/5 (100%) | Android app, residency, unrelated recipe, account status, instruction injection |
| False abstentions on answerable cases | 0/7 | Does not imply correctness or production coverage |
| End-to-end in-process HTTP median / p95 | 20.61 / 31.53 ms | Includes CSRF, auth, retrieval, fixture generation and persistence |

Timing is local test-process timing, not browser/network latency and not Gemini
latency. Fixture provider durations are recorded separately. No paid/provider
latency, real model groundedness, human preference or production accuracy has
been measured.

The incomplete cases were cancellation (access end date omitted), connection
troubleshooting (status-page step omitted), password recovery (link expiry
omitted), and invoices (PDF selection omitted). Copying the first sentence
preserves a valid quote but often fails to answer all parts of a question.
This is deliberately recorded rather than presented as successful model quality.

The broader Step 8 [retrieval evaluation](RETRIEVAL_EVALUATION.md) also contains
ambiguous and missed queries; this smaller RAG set does not supersede its results.
Thresholds and fixtures were not tuned to erase those failures.

## Safety and regression evidence

Separate tests cover forged citations, fabricated numeric claims, completed-refund
claims, leaked identifiers, malformed JSON, missing credentials, SDK timeout and
400/401/403/404/429/503 responses without retries. Integration tests cover
permissions, tenant isolation, missing embeddings/evidence, request replay,
concurrent reservations, interrupted requests, budgets, review version conflicts,
source deletion/change and permission/ticket changes during a provider call.

Browser scenarios verify generation/loading, citation rendering, persistent
approval/rejection/revision, stale evidence, quota-error display, abstention,
Viewer restrictions and earlier auth/ticket/document/classification/search flows.
Exact final suite counts and validation outcomes are recorded in
[PROJECT_STATUS.md](PROJECT_STATUS.md).

## Remaining evaluation gate

Live Gemini remains pending a securely configured key, developer-confirmed free
tier and explicit live-test enablement. The one-call smoke script is described in
[GEMINI_INTEGRATION.md](GEMINI_INTEGRATION.md). Passing that smoke is only connectivity,
schema and citation evidence; a meaningful live quality study would additionally
need authorized bounded synthetic cases, human claim/completeness review, failure
analysis and actual token/latency observations. No broad quality claim follows
from deterministic fixtures or citation matching.
