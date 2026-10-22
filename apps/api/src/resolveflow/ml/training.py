"""Offline training on the versioned synthetic corpus only; never reads a database."""

import warnings
from datetime import UTC, datetime
from pathlib import Path

from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits

from resolveflow.ml.artifact import TrainingConfig, encode, new_pipeline, write_artifact
from resolveflow.ml.contracts import CATEGORY_VERSION, ModelInfo
from resolveflow.ml.dataset import (
    DATASET_PATH,
    DATASET_VERSION,
    load_dataset,
    split_dataset,
    split_manifest,
)
from resolveflow.ml.evaluation import evaluate


def train(root: Path, version: str, config: TrainingConfig, dataset: Path = DATASET_PATH) -> Path:
    records, digest = load_dataset(dataset)
    splits = split_dataset(records, config.seed)
    pipeline = new_pipeline(config)
    with threadpool_limits(limits=1), warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        pipeline.fit(
            [r.combined() for r in splits["train"]], [r.label.value for r in splits["train"]]
        )
        evaluation = {
            "split": split_manifest(splits),
            "split_strategy": "stratified scenario groups 60/20/20",
            "validation": evaluate(pipeline, splits["validation"], config.threshold),
            "test": evaluate(pipeline, splits["test"], config.threshold),
            "limitations": (
                "Synthetic English data only; no production accuracy "
                "or calibrated confidence claim. "
                "Fixed parameters and threshold; no test-set tuning."
            ),
        }
    info = ModelInfo(
        model_version=version,
        trained_at=datetime.now(UTC).isoformat(),
        dataset_version=DATASET_VERSION,
        category_mapping_version=CATEGORY_VERSION,
    )
    return write_artifact(root, encode(pipeline, info, digest, config, evaluation))
