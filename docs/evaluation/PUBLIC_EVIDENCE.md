# ResolveFlow AI | Public evidence summary

This summary preserves aggregate results from completed synthetic benchmarks and recorded local and hosted verification. The three original evaluation reports linked below are already public. The local sources listed at the end are provenance identifiers. Their contents and per-ticket predictions are outside this package.

## Classifier evaluation

| Model | Evaluation set | Correct | Accuracy | Macro-F1 |
|---|---|---:|---:|---:|
| Configured local `baseline-v1` | Original held-out split | 44/56 | 78.57% | 0.7846 |
| Frozen `baseline-v1` | Matched synthetic challenge | 142/210 | 67.62% | 0.6585 |
| Inactive frozen `baseline-v2-candidate` | Same matched synthetic challenge | 183/210 | 87.14% | 0.8701 |

The original 280 synthetic tickets form 140 scenario groups. V1 was fitted on 168 training examples and evaluated on separate validation and test sets of 56 each. V2 combines word TF-IDF, frozen MiniLM embeddings and logistic regression. It was fitted on 224 original development examples. Both frozen artifacts were scored once on the same 210 synthetic tickets across 70 scenario groups with 30 tickets per category. The tickets and labels were authored and reviewed within the development process. Training set size as well as representation differs between V1 and V2, so the comparison measures the full candidate. Independent customer-data validation remains open. [Original V1 evaluation](https://github.com/abhi0874/resolveflow-ai/blob/d2af3ec4ab99cba381ef30e91c2274284733f8ab/docs/evaluation/classifier-v1-evaluation.json)

The paired result favors V2 by **41 correct predictions, or 19.52 percentage points**. Both models were correct on 134 cases, only V1 was correct on 8, only V2 was correct on 49, and neither was correct on 19. V2 offered suggestions on 118/210 tickets (56.19%) at the fixed 0.45 score threshold. Of those 118 suggestions, 113 were correct (95.76%). Accuracy over all 210 cases counts the top prediction even when a suggestion was withheld.

Rows below are true categories and columns are predicted categories. Accuracy is the diagonal sum divided by 210. Macro-F1 is the mean of the seven per-class F1 values, each calculated as twice the diagonal count divided by its row total plus its column total.

### Frozen V1

| True category | Access | Billing | General | Other | Product | Subscription | Technical |
|---|---:|---:|---:|---:|---:|---:|---:|
| Account Access | 17 | 6 | 1 | 0 | 0 | 5 | 1 |
| Billing | 0 | 24 | 0 | 1 | 2 | 2 | 1 |
| General Support | 1 | 0 | 21 | 1 | 2 | 3 | 2 |
| Other | 3 | 3 | 5 | 7 | 4 | 5 | 3 |
| Product Inquiry | 0 | 0 | 1 | 0 | 21 | 6 | 2 |
| Subscription Management | 0 | 3 | 0 | 0 | 0 | 26 | 1 |
| Technical Support | 0 | 2 | 1 | 1 | 0 | 0 | 26 |

### Inactive frozen V2

| True category | Access | Billing | General | Other | Product | Subscription | Technical |
|---|---:|---:|---:|---:|---:|---:|---:|
| Account Access | 24 | 0 | 2 | 0 | 1 | 3 | 0 |
| Billing | 0 | 29 | 0 | 0 | 0 | 1 | 0 |
| General Support | 0 | 1 | 23 | 4 | 2 | 0 | 0 |
| Other | 1 | 3 | 1 | 22 | 2 | 1 | 0 |
| Product Inquiry | 0 | 0 | 0 | 0 | 29 | 1 | 0 |
| Subscription Management | 0 | 1 | 0 | 1 | 1 | 27 | 0 |
| Technical Support | 0 | 1 | 0 | 0 | 0 | 0 | 29 |

### Research and timing context

Grouped development cross-validation for V2 recorded 95.54% accuracy and 0.9550 macro-F1 on 224 development examples. A later inactive V3 included character n-grams. It scored 41/42 (97.62%, macro-F1 0.9760) on short synthetic cases and 193/265 (72.83%, macro-F1 0.7144) on a separate stress set with 51 groups. These are different evaluations. The stress cases expose failures on typos, competing intents and insufficient context. The local application still uses V1.

The matched challenge recorded warm single-ticket median/p95 inference of 0.194/0.210 ms for V1 and 3.102/4.792 ms for V2. V2 timing includes CPU embeddings. Both exclude HTTP and database time. These timings describe this experiment and hardware.

## Retrieval evaluation

The benchmark ranked 14 fictional documents, each represented by one chunk, against 24 labeled queries. The table uses the 21 answerable queries. Both methods use the same corpus, labels and rank cutoffs. MiniLM uses 384-dimensional vectors and a cosine similarity floor of 0.30 in pgvector. The keyword TF-IDF baseline removes English stop words and retains positive scores.

| Measure | MiniLM + pgvector | Keyword TF-IDF |
|---|---:|---:|
| Hit@1 | 19/21 (90.48%) | 11/21 (52.38%) |
| Hit@5 | 20/21 (95.24%) | 19/21 (90.48%) |
| Recall@5 | 0.9286 | 0.8492 |
| MRR@5 | 0.9286 | 0.6762 |
| Unsupported queries with any results | 0/3 | 2/3 |

Hit@1 differs by 38.10 percentage points. Hit rate counts queries with at least one relevant result. Recall averages the fraction of each query's relevant sources retrieved. MRR averages the reciprocal rank of the first relevant result, with zero for misses. The saved semantic timing covers 24 local in-process HTTP requests, with 7.90 ms median and 8.52 ms p95. The small synthetic corpus and local setup limit claims about production relevance and latency. [Original retrieval report](https://github.com/abhi0874/resolveflow-ai/blob/d2af3ec4ab99cba381ef30e91c2274284733f8ab/docs/evaluation/retrieval-v1.json) · [Frozen corpus](https://github.com/abhi0874/resolveflow-ai/blob/d2af3ec4ab99cba381ef30e91c2274284733f8ab/data/synthetic/retrieval-v1/corpus.json) · [Benchmark method](https://github.com/abhi0874/resolveflow-ai/blob/d2af3ec4ab99cba381ef30e91c2274284733f8ab/apps/api/tests/test_retrieval_evaluation.py)

## RAG fixture evaluation

The 12 synthetic cases used real MiniLM/pgvector retrieval and deterministic fixture generation. All seven answerable cases retrieved a relevant source and produced valid exact-quote citations. All five expected abstentions occurred, with zero false abstentions among answerable cases. Three of seven answers contained every required term (42.9%). Quote checks establish source provenance. Answer quality and hallucination frequency require separate evaluation. Timing was 20.61 ms median and 31.53 ms p95 across 12 local in-process requests including retrieval, fixture generation and persistence. [Original fixture report](https://github.com/abhi0874/resolveflow-ai/blob/d2af3ec4ab99cba381ef30e91c2274284733f8ab/docs/evaluation/rag-v1.json)

The later authorized Gemini smoke used a single synthetic request with Gemini 3.6 Flash, minimal thinking, a 1,024-token cap, a 25-second timeout and zero retries. The provider stopped normally and passed JSON, schema and citation checks. Its recorded provider duration was 3,171.57 ms. These are separate measurements with different scopes. Saved local live mode and hosted live generation are disabled. Current key validity, broad live model quality and network performance remain unverified. [Historical live smoke record](https://github.com/abhi0874/resolveflow-ai/blob/d2af3ec4ab99cba381ef30e91c2274284733f8ab/docs/PROJECT_STATUS.md#controlled-live-gemini-test-after-debugging--verified)

## Recorded workflow, backup and release checks

| Area | Verified scope |
|---|---|
| Local workflow | An isolated RQ test restarted the broker after accepting a resume request and completed with the same approved draft ID. A separate interrupted-worker test recovered one persisted draft and one activity record. Delivery uses an outbox and at-least-once semantics. [Recovery test source](https://github.com/abhi0874/resolveflow-ai/blob/d2af3ec4ab99cba381ef30e91c2274284733f8ab/apps/api/tests/test_jobs.py) |
| Step 20 local application | 317 backend tests, 29 full-application browser tests and 16 demo tests passed against that milestone. The full-browser run exercised local Mailpit verification and password recovery. Runs used fixture generation. Full and demo builds passed. This is historical evidence for the local full-application line. |
| Local restore | An isolated restore from a copied encrypted restic repository matched 24 database table fingerprints and migration 0012. Off-host recovery and independent key custody remain open. |
| Public showcase | The redesign passed 29 checks locally, followed by 23 hosted browser/API scenarios and one local font/source check. Vercel built commit `d2af3ec`. The site uses synthetic data and precomputed drafts and can run independently of the local backend. [Hosted acceptance test source](https://github.com/abhi0874/resolveflow-ai/blob/d2af3ec4ab99cba381ef30e91c2274284733f8ab/apps/web/tests-demo/demo.spec.ts) · [Live showcase](https://resolveflow-ai-showcase.vercel.app/) |

## Provenance for local-only evidence

Paths below are repository-relative identifiers for the original records used in this summary. The SHA-256 values identify the input snapshots and allow a holder of those records to match them. The digests do not make those records public. The classifier matrices above were derived directly from the saved paired predictions and checked against the saved metrics. No model or integration test was rerun for this package.

| Original record | SHA-256 |
|---|---|
| `docs/evaluation/step29b/run/predictions.jsonl` | `f9ce0ccbd90721dd21461cbd9ad7451e6ab1c3d4613c660fb420221529687fdb` |
| `docs/evaluation/step29b/run/results.json` | `faf26d1977d60738853fe3a67c48b2ef664aaafb54caebd1286105397f6035d6` |
| `data/synthetic/ticket-challenge-v1/tickets.jsonl` | `7a26875ba60c8b43406caf6d55e5661e640f2d1930829ff9ce184ca7a17df3b7` |
| `docs/evaluation/step29a/nested.json` | `a00178d7beb6ca2527cd3c8279a9d353a9aa50b90079e07474fc2af7712defd7` |
| `docs/evaluation/step29e/evaluation-results.json` | `4b703c59b519452841323e4b9f69babe16a45d38d86afdfdc64f036a33538cd8` |
| `docs/evaluation/step29f/results.json` | `5f30680f4810c474f9bab6c095268625e6e507da2e74d220da7852973ce8cf1b` |
| `docs/evaluation/step20-verification.json` | `2f45e09102c21e9cdab0af40660569f6c32deb60af41c388f8fd9b1b54c13c3a` |
| `docs/handoff/step30q-verification.json` | `5d48c88de2dcd031fa26906413ba824d222d9bd8970f3060878c9e46c504d717` |

The historical live smoke is linked above. The hosted check counts come from the retained local publication run summary. Suggested resumes and project descriptions use only these scoped results.
