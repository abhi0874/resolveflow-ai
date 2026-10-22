import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, log_loss
from sklearn.pipeline import Pipeline

from resolveflow.ml.contracts import LABELS
from resolveflow.ml.dataset import Example


def evaluate(pipeline: Pipeline, rows: list[Example], threshold: float) -> dict:
    texts, truth = [r.combined() for r in rows], [r.label.value for r in rows]
    probabilities = pipeline.predict_proba(texts)
    classes = pipeline.named_steps["classifier"].classes_
    predictions = classes[probabilities.argmax(axis=1)]
    scores = probabilities.max(axis=1)
    has_features = np.asarray(pipeline.named_steps["tfidf"].transform(texts).getnnz(axis=1)) > 0
    correct = predictions == np.asarray(truth)
    report = classification_report(
        truth, predictions, labels=LABELS, output_dict=True, zero_division=0
    )
    # Descriptive diagnostics only; this tiny synthetic sample does not justify calibration.
    bins = []
    for lower, upper in zip(np.arange(0, 1, 0.2), np.arange(0.2, 1.2, 0.2), strict=True):
        mask = (scores >= lower) & (scores < upper if upper < 1 else scores <= 1)
        bins.append(
            {
                "lower": float(lower),
                "upper": min(1.0, float(upper)),
                "count": int(mask.sum()),
                "mean_score": float(scores[mask].mean()) if mask.any() else None,
                "accuracy": float(correct[mask].mean()) if mask.any() else None,
            }
        )
    behavior = []
    for value in sorted({0.25, 0.35, 0.45, 0.55, 0.65, threshold}):
        accepted = (scores >= value) & has_features
        behavior.append(
            {
                "threshold": value,
                "suggested": int(accepted.sum()),
                "coverage": float(accepted.mean()),
                "suggestion_accuracy": float(correct[accepted].mean()) if accepted.any() else None,
            }
        )
    onehot = np.asarray([[int(label == actual) for label in LABELS] for actual in truth])
    return {
        "count": len(rows),
        "accuracy": float(accuracy_score(truth, predictions)),
        "macro_precision": report["macro avg"]["precision"],
        "macro_recall": report["macro avg"]["recall"],
        "macro_f1": report["macro avg"]["f1-score"],
        "per_category": {label: report[label] for label in LABELS},
        "confusion_labels": LABELS,
        "confusion_matrix": confusion_matrix(truth, predictions, labels=LABELS).tolist(),
        "log_loss": float(log_loss(truth, probabilities, labels=LABELS)),
        "multiclass_brier_sum": float(np.square(probabilities - onehot).sum(axis=1).mean()),
        "score_bins": bins,
        "threshold_behavior": behavior,
        "predictions": [
            {"id": r.id, "actual": r.label.value, "predicted": str(p), "score": float(s)}
            for r, p, s in zip(rows, predictions, scores, strict=True)
        ],
    }
