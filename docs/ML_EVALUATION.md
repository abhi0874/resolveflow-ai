# ML baseline evaluation

Measured 2026-10-19 (Asia/Kolkata). These are actual predictions from the trained
`baseline-v1` artifact, not hand-entered accuracy claims. The evaluation command
reloaded that artifact and reproduced validation/test predictions exactly.

## Frozen experiment

- Dataset: `ticket-classification-v1`, SHA-256 `029f27dfb47e5d6011e074146611b0063351b1a8b1ad9d5b9aae57f5a7373d54`.
- Trained at: `2026-10-19T16:09:02.223274+00:00` (UTC). Mapping: `support-categories-v1`.
- Artifact SHA-256: `28a6f5bd2049d6f321d6fbda7759cdc15ba61579dec2e63683458ddd49bc4f56`.
- scikit-learn 1.9.1; NumPy 2.5.4; Python 3.14.6.
- TF-IDF word unigrams/bigrams, sublinear TF, smoothed IDF, L2 normalization;
  vocabulary cap 12,000; logistic regression lbfgs, C=4, max_iter=1,000; seed 42.
- 280 synthetic examples; seven equally represented classes; 140 paired scenario groups.
- Group-stratified split: train 168 (24/class), validation 56 (8/class), test 56 (8/class).
- Fixed threshold 0.45, chosen before observing results. No hyperparameter search,
  calibration fitting, test-set tuning or refit on validation/test records.

## Observed classification performance

| Split | Accuracy | Macro precision | Macro recall | Macro F1 |
| --- | ---: | ---: | ---: | ---: |
| Validation (56) | 0.8929 | 0.8964 | 0.8929 | 0.8859 |
| Test (56) | 0.7857 | 0.7946 | 0.7857 | 0.7846 |

The held-out test has 44 correct predictions out of 56. Each class has only
eight records from four scenarios. The 28 test scenarios are more independent
units than their paired phrasings; these numbers are not estimates of real customer
performance. The validation/test gap and weak classes should guide future data
collection, not retrospective optimization against this frozen test set.

| Test category | Precision | Recall | F1 | Records |
| --- | ---: | ---: | ---: | ---: |
| Account Access | 0.700 | 0.875 | 0.778 | 8 |
| Billing | 1.000 | 1.000 | 1.000 | 8 |
| General Support | 0.600 | 0.750 | 0.667 | 8 |
| Other | 0.714 | 0.625 | 0.667 | 8 |
| Product Inquiry | 0.833 | 0.625 | 0.714 | 8 |
| Subscription Management | 1.000 | 1.000 | 1.000 | 8 |
| Technical Support | 0.714 | 0.625 | 0.667 | 8 |

Confusion matrix: rows are actual labels, columns are predicted labels.

| Actual / predicted | Access | Billing | General | Other | Product | Subscription | Technical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Account Access | 7 | 0 | 1 | 0 | 0 | 0 | 0 |
| Billing | 0 | 8 | 0 | 0 | 0 | 0 | 0 |
| General Support | 0 | 0 | 6 | 2 | 0 | 0 | 0 |
| Other | 1 | 0 | 1 | 5 | 0 | 0 | 1 |
| Product Inquiry | 0 | 0 | 2 | 0 | 5 | 0 | 1 |
| Subscription Management | 0 | 0 | 0 | 0 | 0 | 8 | 0 |
| Technical Support | 2 | 0 | 0 | 0 | 1 | 0 | 5 |

Errors overlap meaningfully: technical problems were confused with access/product
questions; general help, product inquiries and Other are not consistently separated.
Perfect Billing/Subscription results on eight synthetic records each do not establish
perfect behavior or broad domain coverage.

## Abstention and score diagnostics

At threshold 0.45, validation offers 10/56 suggestions (17.9% coverage) and test
offers 13/56 (23.2% coverage). Those small accepted subsets contain no observed
errors, but that is not evidence of 100% production precision. The other 43 test
records abstain and require manual categorization. All suggestions still require
human acceptance. Zero-vocabulary input also abstains regardless of score.

Threshold sweep below is descriptive; it was not used to select the initial threshold.
Future threshold decisions must use validation/representative data, not this test set.

| Threshold | Validation coverage | Validation suggestion accuracy | Test coverage | Test suggestion accuracy |
| --- | ---: | ---: | ---: | ---: |
| 0.25 | 0.768 (43/56) | 0.953 | 0.732 (41/56) | 0.927 |
| 0.35 | 0.393 (22/56) | 0.955 | 0.357 (20/56) | 0.950 |
| 0.45 | 0.179 (10/56) | 1.000 | 0.232 (13/56) | 1.000 |
| 0.55 | 0.089 (5/56) | 1.000 | 0.125 (7/56) | 1.000 |
| 0.65 | 0.054 (3/56) | 1.000 | 0.036 (2/56) | 1.000 |

Test log loss: **1.1495**. Multiclass Brier score (sum of squared
class errors per example, then averaged): **0.5336**.
Five score-bin counts/accuracies are saved in the JSON reports. These are descriptive
calibration diagnostics; no fitted calibrator or confidence-validity claim is made.
The tiny synthetic validation cohort cannot justify reliable real-world calibration.

## Local inference benchmark

Measured on `macOS-27.2-arm64-arm-64bit-Mach-O`, arm64, Python 3.14.6;
one numerical thread, batch size one, 20 warm-up calls then 500 sequential calls
cycling the held-out synthetic inputs. Timing covers the inference service, not
HTTP, authentication, database retrieval, browser rendering or network latency.

- Model load plus startup smoke inference: **3.400 ms**.
- Warm median: **0.161 ms**.
- Warm p95: **0.182 ms**; maximum: **0.268 ms**.

These observations are not a production SLA, a load test or a measured improvement
over another implementation. No prior latency baseline is claimed.

## Reproduce and inspect

From `apps/api`:

```bash
UV_CACHE_DIR=../../.cache/uv uv run python scripts/classifier.py evaluate --version baseline-v1 --output ../../.cache/ml-evaluation.json
UV_CACHE_DIR=../../.cache/uv uv run python scripts/classifier.py benchmark --version baseline-v1 --output ../../.cache/ml-benchmark.json
```

Training/replacement commands and artifact security are in [ML_CLASSIFICATION.md](ML_CLASSIFICATION.md).
The same locked environment, data bytes, preprocessing and seed reproduce fitted
parameters, split membership and predictions; training timestamps and wall-clock
benchmark samples naturally change. Cross-platform bitwise equality is not promised.

Committed machine-readable evidence:

- [Training configuration, provenance, split manifest and metrics](evaluation/classifier-v1-training.json)
- [Independent artifact reload evaluation](evaluation/classifier-v1-evaluation.json)
- [Observed benchmark](evaluation/classifier-v1-benchmark.json)

Future evaluation needs broader English/domain/typo coverage, independently reviewed
labels, realistic class prevalence, consented representative data and a fresh
untouched test cohort before model selection or production-readiness claims.
