"""Offline training, immutable-artifact evaluation and a measured local benchmark."""

import argparse
import json
import platform
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np
from threadpoolctl import threadpool_limits

from resolveflow.core.config import Settings
from resolveflow.ml.artifact import TrainingConfig, decode, read_artifact
from resolveflow.ml.classifier import LocalTicketClassifier
from resolveflow.ml.contracts import TicketText
from resolveflow.ml.dataset import load_dataset, split_dataset, split_manifest
from resolveflow.ml.evaluation import evaluate
from resolveflow.ml.training import train


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["train", "evaluate", "benchmark"])
    parser.add_argument("--version", default="baseline-v1")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--config", type=Path, help="Optional training-configuration JSON")
    parser.add_argument("--output", type=Path, help="Evaluation/benchmark JSON output")
    args = parser.parse_args()
    settings = Settings()
    root = args.root or settings.classifier_artifact_root
    if args.command == "train":
        config = (
            TrainingConfig.model_validate_json(args.config.read_text())
            if args.config
            else TrainingConfig()
        )
        destination = train(root, args.version, config)
        print(f"Trained immutable model {args.version}; report: {destination / 'evaluation.json'}")
        return
    artifact = read_artifact(root, args.version)
    rows, digest = load_dataset()
    if digest != artifact.dataset_sha256:
        raise ValueError("Dataset differs from the training snapshot")
    splits = split_dataset(rows, artifact.config.seed)
    if split_manifest(splits) != artifact.evaluation["split"]:
        raise ValueError("Evaluation split differs from the training snapshot")
    with threadpool_limits(limits=1):
        if args.command == "evaluate":
            model = decode(artifact, args.version)
            result = {
                "model_version": args.version,
                "dataset_sha256": digest,
                "validation": evaluate(model, splits["validation"], artifact.config.threshold),
                "test": evaluate(model, splits["test"], artifact.config.threshold),
            }
            if any(result[part] != artifact.evaluation[part] for part in ("validation", "test")):
                raise ValueError("Evaluation differs from saved predictions")
        else:
            start = time.perf_counter()
            model = LocalTicketClassifier(root, args.version, artifact.config.threshold)
            if not model.health_check():
                raise ValueError("Classifier unavailable")
            load_ms = (time.perf_counter() - start) * 1000
            inputs = [TicketText(title=r.title, description=r.description) for r in splits["test"]]
            for ticket in inputs[:20]:
                model.predict(ticket)
            durations = []
            for i in range(500):
                start = time.perf_counter()
                model.predict(inputs[i % len(inputs)])
                durations.append((time.perf_counter() - start) * 1000)
            result = {
                "model_version": args.version,
                "platform": platform.platform(),
                "machine": platform.machine(),
                "python": platform.python_version(),
                "samples": 500,
                "warmup": 20,
                "batch_size": 1,
                "threads": 1,
                "input_source": "held-out synthetic test examples; no database or HTTP",
                "load_ms": load_ms,
                "median_ms": float(np.median(durations)),
                "p95_ms": float(np.percentile(durations, 95)),
                "max_ms": max(durations),
            }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            result
            if args.command == "benchmark"
            else {
                part: {
                    key: result[part][key]
                    for key in ("accuracy", "macro_precision", "macro_recall", "macro_f1")
                }
                for part in ("validation", "test")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
