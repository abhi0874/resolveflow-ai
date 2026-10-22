# Retrieval evaluation — frozen synthetic v1

Measured 2026-10-20 on this Mac, using the actual local Sentence Transformer,
stored Step 6 chunks and PostgreSQL pgvector retrieval. Full configuration, dataset
hash, versions, predictions and timings are in
[evaluation/retrieval-v1.json](evaluation/retrieval-v1.json).

## Dataset and method

The committed [synthetic corpus](../data/synthetic/retrieval-v1/README.md) has 14
fictional support documents and 24 questions: 21 answerable (including two ambiguous)
and three with no supporting source. Each scored document produces one chunk, so
source IDs label the expected passages unambiguously. Topics include refunds,
cancellation, recovery, billing, technical help, access policy and product guides.
Questions include indirect phrasing, not only copied document keywords.

Model: `sentence-transformers/all-MiniLM-L6-v2`, Apache-2.0, revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, 384 dimensions. CPU, two numerical threads,
window batch size 16; exact PostgreSQL cosine search. Threshold 0.30 and K=1/3/5
were fixed before observing final results. No fine-tuning or threshold sweep occurred.
A second run added the separate larger-document timing and reproduced the same
ranking metrics. The final report preserves that second run's actual timings.

The evaluator uploads/extracts/indexes the corpus through the real authorized API
inside an ownership-checked disposable database. It then sends each query through
the same search service and actual pgvector SQL used by the application. TestClient
runs the HTTP stack in-process; timings include CSRF/session/auth/database operations,
but exclude a network hop and Next.js/browser rendering. No mocked vectors/results
are used for these metrics. Synthetic deterministic vector fixtures appear only in
separate failure/security tests and never in the application or evaluation.

Recall@K averages the fraction of labeled relevant sources returned per answerable
question. MRR@K averages reciprocal rank of the first relevant result (zero if absent).
Hit Rate@K is the fraction with any relevant result. No-answer questions are excluded
from those denominators and counted separately. Ambiguous queries can have several
relevant sources, so recall and hit rate differ.

## Actual results

| Method | K | Recall@K | MRR@K | Hit Rate@K |
| --- | ---: | ---: | ---: | ---: |
| MiniLM + pgvector | 1 | 0.8571 | 0.9048 | 0.9048 |
| MiniLM + pgvector | 3 | 0.9286 | 0.9286 | 0.9524 |
| MiniLM + pgvector | 5 | 0.9286 | 0.9286 | 0.9524 |
| Keyword TF-IDF | 1 | 0.5000 | 0.5238 | 0.5238 |
| Keyword TF-IDF | 3 | 0.8016 | 0.6667 | 0.8571 |
| Keyword TF-IDF | 5 | 0.8492 | 0.6762 | 0.9048 |

The keyword comparison uses English-stopword TF-IDF fit on the same 14 documents,
cosine ranking and scores >0. It is a simple lexical reference, not tuned BM25,
hybrid retrieval or reranking. Its different score scale means its cutoff is not
numerically comparable to MiniLM's 0.30. Both use the same ground truth and K.

At K=5 the semantic system retrieves a relevant source for **20/21** answerable
questions. All **3/3** no-answer questions return nothing; lexical search returns
results for 2/3. Three negatives are far too few to establish rejection reliability.
These are observed corpus results, not perfect accuracy or a production guarantee.

Specific misses expose limitations:

- “I need help with a charge.” returns no passage above 0.30 despite three labeled
  acceptable sources. A vague but valid request can be incorrectly rejected.
- The read-only teammate question ranks upload troubleshooting first and the
  access-policy answer second. Topic similarity does not establish answerability.
- “I am locked out.” returns password recovery but misses the also-relevant lost
  authenticator passage; ambiguity reduces recall even when the first result helps.

No parameters were adjusted to repair those final-set misses. Future tuning needs
a new held-out set and representative consented data, not repeated optimization
against this small known benchmark. Long/multilingual documents, scanned PDFs,
contradictory policies, spelling noise and domain-specific vocabulary remain largely
untested by this corpus. PDF page provenance is covered by document tests, while the
scored retrieval corpus is plain text. Window-mean aggregation and single-stage
retrieval can dilute details; there is no reranker, answer generator or grounding score.

## Performance measurements

| Workload | Observed result |
| --- | --- |
| Encode all 14 short documents in one provider batch | 32.40 ms |
| Index short documents through the in-process API (14) | median 15.62 ms; p95 18.03 ms; max 18.49 ms |
| Search through the in-process API (24 queries) | median 7.90 ms; p95 8.52 ms; max 12.27 ms |
| Separate representative handbook | 28,768 characters, 30 chunks; indexing 294.42 ms |
| Process RSS before/after scored evaluation | 685,293,568 / 711,360,512 bytes |
| Process RSS after larger handbook | 787,742,720 bytes |

RSS includes Python, model, test framework and other libraries; these are snapshots,
not isolated model allocation or measured peak memory. Model initialization's first
observed cold-import smoke check took 9.02 seconds; repeated imports benefit from
OS/package caches and that single observation is not a cold-start distribution.
The model remains loaded across requests. No MPS speed claim is made.

Hardware/environment: Apple Silicon macOS 27.2, Python 3.14.6, PostgreSQL 18.6,
pgvector extension 0.8.6; package versions are recorded in JSON. This is a small,
warm local workload, not a concurrent production load study or an improvement
relative to a previous implementation. Exact search is justified for this measured
size. Evaluate larger tenant-filtered workloads before choosing HNSW; approximate
retrieval must measure its own recall/latency tradeoff.

## Reproduce

From `apps/api`, with the private model downloaded and local PostgreSQL running:

```bash
export UV_CACHE_DIR=../../.cache/uv
uv sync --locked
uv run python scripts/download_embeddings.py
uv run python scripts/evaluate_retrieval.py --output ../../docs/evaluation/retrieval-v1.json
uv run python scripts/local_db.py test
```

The evaluation uses a newly created database marked for this run and cleans it
through the existing test fixture. It never inserts evaluation documents into the
development library. The 30-chunk timing document uses a separate test workspace
and does not contaminate scored rankings. Timings vary with machine load; compare
rankings and corpus/model hashes separately from latency.
