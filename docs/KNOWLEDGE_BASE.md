# Knowledge base and document management

Implemented in Step 6, 2026-10-19 (Asia/Kolkata). This module stores private source
files, extracts actual text and persists deterministic chunks. Step 8 adds local embeddings and semantic retrieval through the same stored chunks;
OCR, generated answers and automated messaging remain deferred.

## Architecture and local use

Open **Knowledge base** from the authenticated workspace navigation. The list is
at `/app/knowledge-base`; details use `/app/knowledge-base/[documentId]`. Workspace
selection is resolved from authorized memberships. Upload through file selection
or drag-and-drop, inspect processing status and text, download the original, or
confirm deletion when permitted. The document filter searches filenames; the separate semantic form searches indexed passages. Upload progress
uses actual XHR transfer events; extraction has an indeterminate status, not a
fabricated percentage. Failed processing remains visible with a safe explanation.

Next.js uses the existing same-origin session proxy. FastAPI document routes call
focused `documents/service.py`, `repository.py`, `validation.py`, `storage.py`,
`extraction.py`, `extract_child.py` and `chunking.py` modules. Pydantic contracts
and SQLAlchemy models live in the same domain package. Only the local adapter
knows filesystem paths. The `Storage` protocol supports save, read, delete and
exists using workspace UUID plus generated key; a future object-store adapter
must preserve those semantics and review the recovery protocol.

## Formats, validation and limits

| Format | Implemented behavior |
| --- | --- |
| PDF | `%PDF-` signature plus strict pypdf parsing; digitally generated text with one-based page references; encrypted, malformed and no-text files fail safely |
| TXT | Strict UTF-8, UTF-8 BOM or BOM-marked UTF-16; reject unsupported encodings/control content |
| Markdown (`.md`) | Same decoding as TXT; preserve source headings and structure as plain text; no HTML/Markdown execution or rendering |

Extension and inspected content must agree. Text uploads reject known PDF, ZIP,
executable and binary signatures. Empty uploads are rejected before persistence;
whitespace-only content fails extraction. Filenames are percent-decoded once,
Unicode-normalized and limited to 255 characters; separators and control
characters are rejected. Filenames never become filesystem paths. Client checks
improve feedback; the backend independently enforces all constraints.

Settings in `apps/api/.env.example` are server-only:

| Setting (`RESOLVEFLOW_` prefix) | Default | Accepted range / behavior |
| --- | --- | --- |
| `DOCUMENT_STORAGE_ROOT` | Repository `.local/documents` | Absolute private path, outside `apps/web/public` |
| `DOCUMENT_UPLOAD_MAX_BYTES` | 2,097,152 (2 MiB) | 1,024–5,242,880; proxy hard ceiling 5 MiB |
| `DOCUMENT_MAX_PAGES` | 100 | 1–200 |
| `DOCUMENT_MAX_CHARS` | 500,000 | 1,000–1,000,000 |
| `DOCUMENT_TIMEOUT_SECONDS` | 15 | 1–30 |
| `DOCUMENT_MEMORY_MB` | 256 | 64–512 |
| `DOCUMENT_CHUNK_SIZE` | 1,200 characters | 100–4,000 |
| `DOCUMENT_CHUNK_OVERLAP` | 150 characters | 0–1,000, strictly less than chunk size |

The storage adapter creates root/workspace directories with mode 0700 and files
with mode 0600. Existing root/workspace directories must already be private;
unsafe permissions are rejected, never silently changed. The operator controls
the trusted storage root and its ancestors. Generated 32-hex keys and UUID
workspace directories, directory-relative operations and no-follow opens prevent
user filename traversal and final-component symlink following. Writes flush,
fsync and atomically rename a tracked `.part` file. Downloads verify SHA-256.
The local adapter targets POSIX macOS/Linux; Windows support is not verified.

Extraction runs in a separate Python process with a minimal environment, no
application credentials, bounded input/output, page/character limits, CPU limit,
wall timeout and monitored RSS. Linux also enforces an address-space limit;
macOS uses RSS polling, which may briefly overshoot the configured limit.
A decompressed PDF content stream over 8 MiB is rejected. A semaphore permits at
most two simultaneous extractors per API process; saturation fails explicitly.
This is bounded synchronous processing, not a queue or an OS security sandbox.
`pypdf==6.21.1` and `psutil==7.2.2` are pinned in the lockfile with permissive
BSD-3-Clause licenses. Scanned image-only PDFs require future OCR; no text is
invented when extraction fails.

## Schema and deterministic chunks

Additive Alembic revision `0005` creates `documents` and `document_chunks` without
changing existing user/workspace/ticket data. Documents store UUID, workspace,
uploader, original filename, generated storage key, verified content type, byte
size, SHA-256, status, safe error code, chunk count and timestamps. Internal claim
token and versioned processing configuration support consistent retries. APIs
never return storage keys, raw paths, process details or claim tokens.

Chunks store UUID, document/workspace identity, zero-based chunk index, content,
exact character count, optional one-based PDF page, source metadata and creation
time. A composite document/workspace foreign key prevents mismatched tenant
associations and cascades chunk deletion. Unique document/index and
workspace/checksum constraints prevent duplicate chunks and content duplicates.
Indexes support workspace/date/status/size lists and ordered document chunks.

Normalization uses Unicode NFC, consistent newlines, trimmed trailing whitespace,
filtered controls and bounded blank lines. Paragraph or word boundaries are
preferred near the configured chunk end, with hard splitting for long tokens.
Overlap is measured in characters, stays within a page, and always makes forward
progress. Empty chunks are removed; at most 2,000 chunks are allowed. Metadata
includes filename, pipeline version and start/end offsets into the **normalized
page text**, not byte offsets in the original file. Chunk IDs use UUID5 of the
document ID, pipeline version, index and content hash. The document preserves its
chunk settings for retries. Identical input under that configuration yields stable
ordering and IDs. Step 8 adds a separate chunk_embeddings table without replacing chunks.

## API and role policy

All paths below are relative to `/api/v1/workspaces/{workspace_id}/documents`.
Every endpoint authenticates the session and checks workspace membership. Resource
queries include both document ID and workspace ID; out-of-scope IDs return 404.

| Method and suffix | Behavior |
| --- | --- |
| `GET /config` | Authorized UI upload formats and limits |
| `POST` collection | Raw file bytes; `Content-Type: application/octet-stream`; percent-encoded UTF-8 `X-Upload-Filename`; 201 document metadata |
| `GET` collection | Paged metadata; `search`, `status`, `sort=created_at\|file_size`, `direction=asc\|desc`, `page`, `page_size` |
| `GET /{id}` | Safe metadata and processing error message |
| `GET /{id}/chunks` | Ordered paged chunks for completed documents |
| `GET /{id}/download` | Authorized completed original as attachment, octet-stream, no-store, nosniff and sandbox CSP |
| `POST /{id}/retry` | JSON `{}`; retry failed processing, completed is a no-op, active/deleting returns 409 |
| `DELETE /{id}` | JSON `{}`; 204 after file and record cleanup; 503 retains a retryable deletion tombstone |

Uploads intentionally use bounded raw bytes, **not multipart**. All mutations,
including upload, require the existing exact trusted Origin, current session CSRF
token and Fetch Metadata checks. Only the exact upload collection POST accepts
binary bodies and the larger limit; other mutations retain JSON and 16 KiB limits.
Next.js forwards only allowlisted paths/headers/queries to the fixed backend and
uses a 60-second document request timeout. Duplicate/unknown query parameters are
rejected. Pagination defaults to 25, max 100, with total/page/pages metadata;
SQL ordering adds UUID as a deterministic tie-breaker. Offset pages can still
shift when documents change between requests; this is not snapshot pagination.

| Action | Owner | Admin | Support Agent | Viewer |
| --- | --- | --- | --- | --- |
| List and inspect metadata/config | Yes | Yes | Yes | Yes |
| Upload and retry | Yes | Yes | Yes | No |
| Inspect chunks / download | Yes | Yes | Yes | No |
| Delete | Yes | Yes | No | No |

The Viewer policy is deliberately metadata-only. Central permissions are
`document:upload`, `document:content` and `document:delete`. Write authorization
shares the workspace lock with membership changes and rechecks current roles.
Long extraction holds only the individual document lock. Frontend visibility
reflects permissions but is not the security boundary.

## Lifecycle, idempotence and recovery

1. Authorize and validate before creating records or writing files.
2. Compute SHA-256 and commit a `pending` metadata journal **before** storage writes.
3. Save the private object; commit `processing` with an exclusive claim token.
4. Lock the document, read/verify bytes, extract and chunk within resource limits.
5. Commit all chunks and `completed` together, or persist `failed` with a safe code.

Content-identical uploads within the same workspace return the existing record,
including its original filename/uploader/status; they do not create a second file
or restart failed processing. Other workspaces receive independent objects.
A 201 metadata response may describe **failed** processing; clients must inspect
`processing_status`. Use retry for transient extraction failures. Retry uses the
stored original and original chunk settings. Active document locks/claims return
409 instead of allowing duplicate processing. Missing/corrupt originals require
deleting the failed record and uploading again.

Deletion first commits `deleting` and removes chunks, preventing further content
reads. It then removes both original and possible `.part`, and finally deletes
the document record. Filesystem failure leaves a tombstone with a safe error;
repeat DELETE or run recovery. A crash after file deletion but before DB commit
leaves the same tracked tombstone; missing files are safe on retry. A crash during
upload leaves tracked pending/processing metadata rather than an unreferenced
file. Partial files stay linked by the generated key until cleanup. This protocol
is recoverable, **not an atomic filesystem/database transaction**.

With the configured database and storage mounted, run from `apps/api`:

```bash
UV_CACHE_DIR=../../.cache/uv uv run python scripts/recover_documents.py
```

The explicit operator command handles up to 100 records older than the configured
processing timeout plus 60 seconds. It skips active locks, marks interrupted
pending/processing records failed for explicit retry, and retries deletion
cleanup. Repeat for larger backlogs. It never scans/deletes arbitrary files and
is not a scheduler or durable job system. Failed writes remain tracked even when
cleanup cannot complete. Back up/restore the database and private storage together;
restore reconciliation and automated maintenance remain production work.

## Verification and remaining boundaries

From the repository root, with local PostgreSQL running:

```bash
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run --locked ruff check .)
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run --locked ruff format --check .)
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run python scripts/local_db.py test)
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
NEXT_TELEMETRY_DISABLED=1 npm --prefix apps/web run build
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run python scripts/test_browser.py)
```

Backend fixtures and the browser harness use disposable, ownership-marked
PostgreSQL databases and temporary storage; they never clean development documents.
Tests exercise genuine PDF/TXT/Markdown extraction, deterministic chunks, limits,
malformed/encrypted/no-text PDFs, tenant/RBAC boundaries, CSRF, safe previews,
traversal/symlinks, migration preservation, retry/deduplication and recovery after
partial storage/database failures. Existing authentication and ticket regressions
remain included. Actual counts and final results are in PROJECT_STATUS.md.

The focused security review added checksum verification on download and refuses
nonprivate existing directories. Extracted content is escaped plain React text;
there is no `dangerouslySetInnerHTML` or Markdown HTML renderer. Originals remain
untrusted files even after successful extraction. Parsing is not sanitization,
antivirus or content-disarm. Further production work includes a hardened parser
sandbox, persistent object storage, durable workers/retries, tenant storage quotas,
upload rate controls, malware handling, observability, retention and tested
backup/restore. Per-process extraction bounds do not bound total multiworker or
multiuser resource use. Protected local POSIX storage is not suitable as durable
serverless storage. Public-production readiness is not claimed.

Step 8 consumes these stable chunks for local embeddings and exact pgvector retrieval.
Hybrid retrieval, reranking, LangGraph, Gemini and Redis workers remain deferred. Step 7
local ticket classification is implemented separately; see [ML_CLASSIFICATION.md](ML_CLASSIFICATION.md).


## Step 8 semantic indexing and retrieval

Completed extraction and completed indexing are separate states. Document lists and
details show Not indexed / Indexing / Indexed / Indexing failed. Owner/Admin/Agent
can index or reindex completed documents; Viewer cannot index or search private
content. Search returns actual source passages, with text escaped and links to the
existing workspace-scoped details page. Model identity is shown in indexing details.

`POST /documents/{id}/index` and `POST /knowledge-base/search` are relative to the
workspace API prefix. Indexing uses bounded synchronous batches, old-vector retention
on failure, and explicit stale-claim recovery through retry. Chunk deletion cascades
vectors before private-file cleanup, preserving the existing tombstone protocol.
See [SEMANTIC_SEARCH.md](SEMANTIC_SEARCH.md) for full API/settings/setup/recovery and
[RETRIEVAL_EVALUATION.md](RETRIEVAL_EVALUATION.md) for actual measurements. The old
Step 6 text above describes extraction/storage; semantic retrieval is now implemented.
Gemini, LangGraph and Redis workers remain future work.
