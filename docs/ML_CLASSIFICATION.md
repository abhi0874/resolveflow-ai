# ML ticket classification

Step 7 implements a real local scikit-learn TF-IDF + logistic-regression baseline.
It recommends a ticket category and requires manual acceptance through the existing
version-checked ticket update. No Gemini, LLM reasoning, embeddings, RAG, LangGraph,
Redis, automatic training, hosted registry or paid inference is involved.

## Architecture and categories

`apps/api/src/resolveflow/ml/` separates contracts, dataset validation/splitting,
training, evaluation, artifact persistence and inference. `TicketClassifier` exposes
`predict`, `predict_batch`, `get_model_info` and `health_check`; it depends on no
HTTP or database APIs. `LocalTicketClassifier` implements the interface. The
FastAPI app loads one immutable model per lifespan/process, tests an inference at
startup and reuses it; inference never trains or reloads per request.

The centralized category enum and mapping version `support-categories-v1` define:
Billing, Technical Support, Account Access, Subscription Management, Product
Inquiry, General Support and Other. The existing ticket category is nullable
free text, not a conflicting enum. Suggestions use these exact human-readable
values; manual/custom/legacy categories remain unchanged and valid. No database
migration is needed. The UI displays returned labels without a duplicate mapping.

`TicketText` validates title <=200 and description <=8,000 characters, rejects
non-string/control/wholly-empty input, normalizes Unicode NFC and collapses
whitespace. Both fields are joined for inference. Existing ticket labels, notes,
uploader details and workspace data are not features. No stemming or stop-word
removal discards negation; case folding and tokenization occur inside TF-IDF.
There is no hidden truncation of long tickets or logging of ticket content.

The pipeline uses word unigrams/bigrams, sublinear term frequency, smoothed IDF,
L2 normalization and up to 12,000 features, followed by multinomial logistic
regression with lbfgs, C=4 and max_iter=1,000. Seed is 42. Training limits numerical
thread pools to one and treats failure to converge as an error. Pinned runtime
versions and complete configuration travel with the artifact. All fitted vocabulary,
IDF and classifier parameters originate from the training split alone.

## Synthetic data and evaluation

The versioned [dataset](../data/synthetic/ticket-classification-v1/README.md) contains
280 synthetic examples, 40 per class, in 140 two-example scenario groups. No real
workspace content is read by the training pipeline. Group-preserving stratification
allocates 60/20/20 percent to train/validation/test: 168/56/56 records. Related
phrasings never cross the split; exact duplicate detection and a lexical
near-duplicate check reject obvious leakage. Saved manifests identify every record
and group. Manual review is still necessary for semantic duplicates.

Training parameters and the 0.45 threshold were fixed before evaluation; there is
no hyperparameter search or test-driven selection. The evaluation command reloads
the saved model and dataset snapshot, verifies hashes and split identities, and
requires its validation/test predictions and metrics to match the saved report.
Reports include accuracy, macro precision/recall/F1, each class, confusion matrix,
distribution, score bins, log loss, multiclass Brier score and threshold coverage.
See [ML_EVALUATION.md](ML_EVALUATION.md) for actual measurements and limits.

## Scores and manual decisions

`predict_proba` yields an **uncalibrated model probability**, not a verified chance
of correctness. The dataset is too small and synthetic to justify fitting a useful
production calibrator. Score bins and proper-scoring metrics are descriptive
checks only. The configurable threshold is an initial operating choice, not an
optimal or production-validated value.

Results contain the highest-scoring `predicted_category`, `score`, `score_kind`,
`model_version`, mapping version and active threshold. If the score is below the
threshold, or the input has no vocabulary features, `uncertain=true` and
`suggested_category=null`. The UI offers no Accept button in that case and directs
the user to manual editing. Other is an ordinary learned label; uncertainty is
not silently converted to Other. `human_review_recommended` is always true,
including above-threshold suggestions. A known word alone does not establish that
an input is in distribution; this baseline is not a general OOD detector.

## API, permissions and approval

`POST /api/v1/workspaces/{workspace_id}/tickets/{ticket_id}/classify` accepts only
an empty JSON object. It requires the existing session, exact trusted Origin,
CSRF token, workspace membership and ticket:write permission. It fetches the actual
stored title/description, scoped by workspace plus ticket ID. Owner/Admin can
classify workspace tickets; Support Agent can classify only unassigned or
self-assigned tickets, matching editing policy. Viewer is denied. A workspace
lock serializes permission and ticket snapshots with writes for the short inference.

The 200 response includes prediction fields plus `ticket_id` and `ticket_version`.
It does not change category, version, timestamps or activity, and returns no ticket
text, filesystem paths, coefficients or vocabulary. Missing/cross-tenant tickets
return 404; invalid input 422; unauthorized action 403; unauthenticated 401.
A missing/incompatible/busy/failing model returns safe 503 with
`error.code=classifier_unavailable`; ordinary ticket operations remain usable.
General `/ready` still checks PostgreSQL, not classifier availability.

The protected ticket details page offers **Classify with ML**, real loading and
error states, model score/version, uncertainty, Accept suggestion and Dismiss
suggestion. Accept sends the returned category through the **existing PATCH** with
its `expected_version`; central RBAC and assignment rules run again. An intervening
edit or note produces 409 instead of applying a suggestion to changed ticket state.
A successful category change preserves the existing `updated` activity with
`fields: ["category"]`, refreshes the UI and persists across reload. Identical
category updates retain existing no-op behavior. Dismissal is local UI state and
makes no write. Suggestions are not persisted or claimed as an ML audit registry;
activity records who changed the category, not model attribution.

## Artifact security and lifecycle

The controlled default root is repository `.local/classifier/`, excluded from Git
and separate from document uploads. Each version directory holds `model.json`
and `evaluation.json`. Models contain **data-only JSON**: fitted vocabulary,
IDF, coefficients/intercepts/classes, metadata, pipeline/schema versions,
dependency versions, dataset SHA-256, configuration, split manifest and metrics.
No pickle/joblib deserialization or arbitrary Python object loading is used.
The fixed loader reconstructs only the two known sklearn estimator types and
checks version compatibility, dimensions, finite numeric values, class mapping,
vocabulary indexing and a 16 MiB file limit. Round-trip inference is tested.

Only operator-configured roots and validated version names are accepted; no model
upload endpoint exists. Root/version symlinks, final-file symlinks and paths writable
by other users are rejected. Training uses a private staging directory, 0600 files,
fsync and directory rename, and refuses to replace an existing version. Generated
reports include an artifact hash for provenance, not a cryptographic signature.
A privileged operator can still alter local data; trusted ownership and parent
directory permissions are operational requirements. This format is intentionally
limited to this pipeline, not a generic sklearn model interchange standard.

Environment settings:

| Setting (`RESOLVEFLOW_` prefix) | Default |
| --- | --- |
| `CLASSIFIER_ARTIFACT_ROOT` | Absolute repository `.local/classifier` path |
| `CLASSIFIER_MODEL_VERSION` | `baseline-v1` |
| `CLASSIFIER_THRESHOLD` | `0.45`, accepted 0.15–1.0 |

Changing the active version or threshold requires an API restart. Missing or invalid
models fail closed without disabling login/tickets. The model file is already
trained locally in this checkout; a fresh checkout must run the training command.
Do not point the model root at public web folders or document storage.

## Commands and replacement procedure

From `apps/api`, install the lockfile and train explicitly on the committed corpus:

```bash
export UV_CACHE_DIR=../../.cache/uv
uv sync --locked
uv run python scripts/classifier.py train --version baseline-v1
uv run python scripts/classifier.py evaluate --version baseline-v1 --output ../../.cache/ml-evaluation.json
uv run python scripts/classifier.py benchmark --version baseline-v1 --output ../../.cache/ml-benchmark.json
uv run pytest tests/test_ml.py
uv run python scripts/local_db.py start
uv run python scripts/local_db.py test
```

Training refuses to overwrite `baseline-v1` if already present. For a new candidate,
use a new version (for example `baseline-v2`) and optional `--config` JSON containing
TrainingConfig fields: seed, c, max_features, ngram_max, max_iter, threshold. Freeze
choices using training/validation experiments before inspecting final test results.
The initial command evaluates the frozen model on both splits; repeated test-set
inspection must not become a tuning loop. For substantial future iteration, reserve
a new untouched test cohort and new dataset version. Never add customer data without
separate explicit permission. No command scrapes application tickets.

Evaluate/benchmark that exact candidate version, inspect per-class errors and
uncertainty coverage, then set `RESOLVEFLOW_CLASSIFIER_MODEL_VERSION` and the
explicit runtime threshold in the API environment and restart. Roll back by
selecting the previous retained version and restarting. No automatic promotion,
cleanup of old models or hot reload is implemented.

Start the app after the database is running:

```bash
uv run alembic upgrade head
uv run --locked uvicorn resolveflow.main:app --app-dir src --host 127.0.0.1 --port 8000 --no-proxy-headers --reload
```

In another terminal from the repository root:

```bash
API_INTERNAL_URL=http://127.0.0.1:8000 npm --prefix apps/web run dev
```

Open a ticket as an authorized editor. For all production-build browser regressions:

```bash
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
NEXT_TELEMETRY_DISABLED=1 npm --prefix apps/web run build
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run python scripts/test_browser.py)
```

Unit/integration tests train in temporary model directories. The browser harness
also trains its own real synthetic model and uses its own disposable database and
storage. Existing tests do not load a developer's model. Browser/API fixtures can
use training examples to verify behavior; they are **not** independent accuracy
measurements. Only the preserved held-out evaluation reports measure performance.

## Limits and future work

Batches are bounded to 1–32 validated tickets, with at most two concurrent inference
calls per API process. No ticket-content cache crosses tenants. This is not a global
rate limiter or distributed capacity guarantee; public exposure needs abuse controls,
monitoring, request-level latency/load tests and operational ownership. Benchmark
results exclude HTTP/auth/database and use one local machine, not production load.

English synthetic-only training, weak open-set detection, small per-class test
counts, subjective boundary labels, limited typo/domain diversity and uncalibrated
scores prevent production-accuracy claims. Future separately authorized work may
add representative consented data, calibration, drift evaluation and alternative
classifiers through the same interface. No Step 8 or other AI integration is included.

References: sklearn's [pipeline leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html),
[probability calibration](https://scikit-learn.org/stable/modules/calibration.html),
and [model persistence security](https://scikit-learn.org/stable/model_persistence.html).
