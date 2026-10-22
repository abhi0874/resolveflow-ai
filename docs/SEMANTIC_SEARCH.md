# Local semantic search — Step 8

Implemented 2026-10-20. This retrieves real stored passages; it does not generate
answers. Gemini, LangGraph, Redis workers and deployment remain outside this step.

## Model and setup

The official [all-MiniLM-L6-v2 model](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
is Apache-2.0, English-oriented, and produces 384-dimensional embeddings for
sentences/short paragraphs. The immutable revision is
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. See the model card for its training sources
and limitations; licensing is not a guarantee of retrieval accuracy.

Pinned `sentence-transformers==6.1.0`, `torch==2.14.1`, `transformers==5.20.2` and
`pgvector==0.5.1` installed successfully with Python 3.14.6 on macOS arm64. PyTorch
provides a native cp314 macOS arm64 wheel. CPU inference is verified and the default.
The optional `mps` setting uses available Apple acceleration; unavailable MPS and
runtime MPS failures fall back to CPU. MPS performance is not benchmarked or claimed.
The [Sentence Transformers installation guide](https://www.sbert.net/docs/installation.html)
and [pgvector Python integration](https://github.com/pgvector/pgvector-python) describe
these dependencies and cosine-distance support.

From the repository root:

```bash
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv sync --locked)
(cd apps/api && UV_CACHE_DIR=../../.cache/uv HF_HUB_DISABLE_TELEMETRY=1 uv run python scripts/download_embeddings.py)
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run python scripts/local_db.py start)
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run alembic upgrade head)
```

Initial setup requires an Internet download of the public model (approximately
91 MB of safetensors plus tokenizer/config files) and package dependencies. No
account, payment or inference API is needed. The downloader requests only the
explicit files at the pinned official revision, writes a private staging directory,
records SHA-256 hashes and atomically publishes `.local/embeddings/minilm-v1`.
It verifies an existing snapshot rather than downloading on every run.

Runtime is offline (`local_files_only=True`, `trust_remote_code=False`, safetensors
only), verifies the manifest and expected module types/paths, and loads once per
API lifespan/process. Uploads cannot choose model paths or code. Model files are
separate from document storage and public assets; unsafe writable/symlinked model
paths are rejected. Hashes detect accidental changes, not a malicious privileged
operator changing both manifest and files. Trusted model-directory ownership and
ancestors remain operational requirements. There is no arbitrary model upload.
A missing/incompatible snapshot leaves ordinary application features available and
search/index requests return safe 503 errors.

## Interface, preparation and bounds

`retrieval/contracts.py` defines `EmbeddingProvider`: `embed_documents`, `embed_query`,
`get_dimensions`, `get_model_info`, and `health_check`. The concrete local adapter
has no database, document-storage or authorization dependencies. HTTP routes invoke
separate indexing/search services. Vendor objects never enter response contracts.

Text must be nonempty, NFC-normalized, without unsupported control characters;
whitespace is collapsed for inference. Chunks are bounded to 4,000 characters,
queries to 1,000. A batch contains 1–32 chunks. The model's 256-token context includes
two special tokens. Longer chunks use 254-token windows with 32-token overlap;
normalized window vectors are averaged and normalized again. Every window is
checked before encoding so it cannot silently exceed the model context after
round-tripping through the tokenizer. This aggregation can dilute specific facts;
source text remains the original stored chunk, not a generated paraphrase.

The model batches window encoding (default 16) and permits one concurrent inference
call per process. Saturation fails safely; there is no unbounded waiting queue.
Vectors must have exactly 384 finite float32 components and norm 0.999–1.001;
zero, NaN, infinite and wrong-dimensional vectors are rejected before persistence.

| Environment setting (`RESOLVEFLOW_` prefix) | Default / range |
| --- | --- |
| `EMBEDDING_MODEL_ROOT` | Absolute private repository `.local/embeddings/minilm-v1` |
| `EMBEDDING_DEVICE` | `cpu`; optional `mps` |
| `EMBEDDING_BATCH_SIZE` | 16; 1–32 |
| `INDEXING_MAX_CHUNKS` | 256; 1–2000 |
| `INDEXING_TIMEOUT_SECONDS` | 40; 5–45 |
| `SEARCH_MIN_SIMILARITY` | 0.30; 0–1 |

The indexing deadline is checked **between batches**, not a hard interrupt of a
native PyTorch call. A hung native inference requires process recovery. Requests
have 60-second document proxy/client timeouts; disconnect does not cancel database
work already executing. Default chunks and batching keep the verified local workload
small. Per-process bounds are not global tenant quotas or a public abuse-control SLA.

## Additive schema and lifecycle

Migration `0006` adds separate indexing status/error/claim/model fields to documents,
a composite unique chunk identity, and `chunk_embeddings`. Existing documents and
chunks remain intact and immediately eligible for explicit indexing. No re-upload,
database reset, historical migration edit or unrelated table change is needed.

Each chunk has at most one current embedding: chunk PK, workspace/document IDs,
`vector(384)`, full model-space identity, source-content SHA-256 and timestamps.
A composite FK to `(workspace_id,document_id,id)` on chunks enforces associations
and cascades deletion. PostgreSQL enforces vector dimensions, finite components
and the unit-norm check. A B-tree on workspace/model/document supports filtering.

The space identity contains model ID, immutable revision, dimension implied by the
fixed schema, and token-window/normalization policy. Search compares only vectors
matching the active provider's space. A same-dimensional model/policy change needs
an explicitly reviewed adapter/snapshot identity change plus reindexing. A different
dimension requires an additive schema migration and compatible adapter/evaluation;
changing only an environment variable is insufficient. There is no automatic model
substitution or mixing of spaces. A rolling deployment may temporarily serve only
the documents already reindexed for each process's space; coordinate model rollout.

`POST /api/v1/workspaces/{workspace_id}/documents/{document_id}/index` accepts
`{"force": false}` (or `{}`), with strict inputs. Owner/Admin/Support Agent may index;
Viewer is metadata-only and cannot index or search. Session, CSRF, trusted Origin,
workspace membership and completed nonempty extraction are required. Oversized
indexing workloads return 422; missing/foreign documents 404; busy/not-ready 409.

1. Lock/authorize the workspace and document; validate counts and provider.
2. Repeated indexing is a no-op when all current chunks have valid vectors in the
   correct space with matching content hashes. `force:true` requests replacement.
3. Commit an `indexing` status and exclusive claim. Then hold the individual
   document lock and process ordered chunks in bounded batches.
4. Upsert vectors within one savepoint/transaction. Readers continue seeing old
   committed vectors until all replacements are ready. Recheck current membership
   and active account before publication; role changes prevent publication.
5. Commit all vectors and `indexed` together. Inference/validation failures roll
   back every partial replacement and record `failed`; unchanged previous vectors
   remain searchable if their model/content still match. A failed attempt is not
   reported as successful indexing.

An interrupted transaction leaves old vectors and a committed claim. Explicit
index/reindex can reclaim a claim older than timeout +60 seconds, only after acquiring
the document lock; active locked workers return 409. A fresh claim also returns 409.
No scheduler, durable queue, automatic retry or progress percentage is claimed.
The synchronous claim consumer is a boundary for future authorized worker work;
a future worker must revalidate actor and tenant rather than trust serialized IDs.

Normal extraction/deletion removes chunks and therefore cascades vectors. Deletion
first commits the existing tombstone and chunk/vector removal, so a subsequent file
cleanup failure cannot leave deleted passages searchable. Retrying deletion completes
the established private-file lifecycle. Missing/changed vectors are repaired by
indexing; content hashes exclude externally altered stale chunks from retrieval.
Privileged raw SQL writers must maintain coherent chunk/document counts.

## Search API and results

`POST /api/v1/workspaces/{workspace_id}/knowledge-base/search`:

```json
{"query":"How can a customer get their money back?","top_k":5}
```

`top_k` is 1–20. Optional `min_similarity` is a finite 0–1 override; omission uses
the configured default. Unknown fields, blank/oversized queries and invalid bounds
are rejected. Authentication/CSRF and `document:content` permission run before
inference and membership is checked again before retrieval.

The SQL query scopes embeddings, chunks AND documents to the authorized workspace
and joins matching composite identities. It filters completed/non-deleting documents,
active model-space identity, valid norms and matching content hashes before ranking.
`pgvector.sqlalchemy.Vector.cosine_distance` runs in PostgreSQL. No unrestricted
global search or Python post-filtering of other tenants occurs. SQL parameters are
bound; no user SQL or document instruction is executed.

Similarity is `1 - cosine_distance`. It measures embedding relatedness, not a
probability, factual correctness, answerability or source trust. Thresholding can
return an empty list. Identical-content passages are deduplicated within the
workspace in SQL; ties use document UUID then chunk position. Near-duplicate overlap
is not semantically deduplicated. No result content is invented.

Responses contain query, active model metadata, threshold and results with actual
document ID/name, chunk ID/index, original content, nullable page number, source
metadata and similarity score. Text sources have null pages; PDF pages retain their
one-based extraction references. Results navigate to authorized document details;
deleted/lost-access documents use the existing unavailable page. The UI renders
escaped plain text and has loading, empty, unavailable, indexing/reindexing and
permission-aware controls. Filename filtering remains separate.

Exact nearest-neighbor search is the initial strategy. The measured library is tiny
and does not justify HNSW. Approximate indexes, filtered recall, larger-corpus load
and multi-tenant capacity need separate evaluation. There is no retrieval cache.

## Commands and verification

Run API/frontend using README commands. Index from document details, then search
from the workspace knowledge-base page. For a terminal client, from `apps/api`:

```bash
export UV_CACHE_DIR=../../.cache/uv
uv run python scripts/semantic_search.py index --workspace WORKSPACE_UUID --document DOCUMENT_UUID
uv run python scripts/semantic_search.py index --workspace WORKSPACE_UUID --document DOCUMENT_UUID --force
uv run python scripts/semantic_search.py search --workspace WORKSPACE_UUID --query 'How do refunds work?' --top-k 5
uv run python scripts/evaluate_retrieval.py --output ../../docs/evaluation/retrieval-v1.json
uv run pytest tests/test_embeddings.py
uv run python scripts/local_db.py test
uv run python scripts/test_browser.py
```

Replace UUID placeholders with actual authorized records. The terminal client prompts
for email/password without echoing the password, uses the same session/CSRF API on
localhost:8000 with localhost:3000 Origin, and logs out its own session afterward.
It does not bypass RBAC or access the database directly. Search output intentionally
shows the requested passages to the authenticated operator.

Evaluation/browser/backend integration runs use disposable ownership-marked local
PostgreSQL databases and temporary document storage; development records are preserved.
Unit fixtures are explicit and confined to tests. Real model tests use the local
snapshot and are explicitly skipped if it has not been downloaded; this checkout's
real model/pgvector tests did run. The application has no fake embedding fallback.
See [RETRIEVAL_EVALUATION.md](RETRIEVAL_EVALUATION.md) and
[PROJECT_STATUS.md](PROJECT_STATUS.md) for measured evidence and remaining limits.

Future deployment requires a suitable persistent model/inference service, hosted
pgvector, durable storage/jobs, quotas, monitoring and tested operations. A local
model loaded in a Mac process is not evidence of Vercel function suitability.
