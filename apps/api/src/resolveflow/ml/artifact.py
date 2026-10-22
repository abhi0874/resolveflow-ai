"""Data-only, version-pinned persistence for this fixed TF-IDF/logistic pipeline."""

import hashlib
import json
import os
import re
import stat
from pathlib import Path

import numpy as np
import sklearn
from pydantic import BaseModel, ConfigDict, Field
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from resolveflow.ml.contracts import CATEGORY_VERSION, LABELS, PREPROCESSING_VERSION, ModelInfo

MAX_ARTIFACT_BYTES = 16 * 1024**2


class TrainingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    seed: int = Field(default=42, ge=0, le=2**31 - 1)
    c: float = Field(default=4.0, gt=0, le=100)
    max_features: int = Field(default=12000, ge=100, le=20000)
    ngram_max: int = Field(default=2, ge=1, le=2)
    max_iter: int = Field(default=1000, ge=100, le=3000)
    threshold: float = Field(default=0.45, ge=0.15, le=1)


class Artifact(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    schema_version: int
    info: ModelInfo
    preprocessing_version: str
    sklearn_version: str
    numpy_version: str
    dataset_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    config: TrainingConfig
    classes: list[str]
    vocabulary: dict[str, int]
    idf: list[float]
    coefficients: list[list[float]]
    intercepts: list[float]
    training_iterations: list[int]
    # Manifest and actual evaluation metrics travel with each immutable model.
    evaluation: dict


def valid_version(version: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", version):
        raise ValueError("Invalid model version")
    return version


def new_pipeline(config: TrainingConfig) -> Pipeline:
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, config.ngram_max),
                    sublinear_tf=True,
                    max_features=config.max_features,
                    lowercase=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    C=config.c, solver="lbfgs", max_iter=config.max_iter, random_state=config.seed
                ),
            ),
        ]
    )


def encode(
    pipeline: Pipeline, info: ModelInfo, digest: str, config: TrainingConfig, evaluation: dict
) -> Artifact:
    vectorizer, classifier = pipeline.named_steps["tfidf"], pipeline.named_steps["classifier"]
    return Artifact(
        schema_version=1,
        info=info,
        preprocessing_version=PREPROCESSING_VERSION,
        sklearn_version=sklearn.__version__,
        numpy_version=np.__version__,
        dataset_sha256=digest,
        config=config,
        classes=classifier.classes_.tolist(),
        vocabulary=vectorizer.vocabulary_,
        idf=vectorizer.idf_.tolist(),
        coefficients=classifier.coef_.tolist(),
        intercepts=classifier.intercept_.tolist(),
        training_iterations=classifier.n_iter_.tolist(),
        evaluation=evaluation,
    )


def decode(artifact: Artifact, version: str) -> Pipeline:
    if (
        artifact.schema_version != 1
        or artifact.info.model_version != valid_version(version)
        or artifact.info.category_mapping_version != CATEGORY_VERSION
        or artifact.preprocessing_version != PREPROCESSING_VERSION
        or artifact.sklearn_version != sklearn.__version__
        or artifact.numpy_version != np.__version__
        or artifact.classes != LABELS
    ):
        raise ValueError("Incompatible artifact")
    n = len(artifact.vocabulary)
    if not 1 <= n <= artifact.config.max_features or sorted(artifact.vocabulary.values()) != list(
        range(n)
    ):
        raise ValueError("Invalid vocabulary")
    if any(not word or len(word) > 17000 for word in artifact.vocabulary):
        raise ValueError("Invalid feature")
    idf = np.asarray(artifact.idf, dtype=float)
    weights = np.asarray(artifact.coefficients, dtype=float)
    intercept = np.asarray(artifact.intercepts, dtype=float)
    if idf.shape != (n,) or weights.shape != (len(LABELS), n) or intercept.shape != (len(LABELS),):
        raise ValueError("Invalid model dimensions")
    if not all(np.isfinite(x).all() for x in (idf, weights, intercept)) or (idf < 1).any():
        raise ValueError("Invalid model values")
    pipeline = new_pipeline(artifact.config)
    vectorizer, classifier = pipeline.named_steps["tfidf"], pipeline.named_steps["classifier"]
    vectorizer.set_params(vocabulary=artifact.vocabulary)
    vectorizer.idf_ = idf
    classifier.classes_ = np.asarray(artifact.classes)
    classifier.coef_, classifier.intercept_, classifier.n_features_in_ = weights, intercept, n
    classifier.n_iter_ = np.asarray(artifact.training_iterations)
    return pipeline


def read_artifact(root: Path, version: str) -> Artifact:
    valid_version(version)
    # Root is operator configuration, never request input. Reject final symlinks and
    # writable-by-other-user artifact paths; read a bounded regular data file.
    folder = root / version
    for directory in (root, folder):
        if directory.is_symlink() or not directory.is_dir() or directory.stat().st_mode & 0o022:
            raise ValueError("Unsafe model directory")
    fd = os.open(folder / "model.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as source:
        mode = os.fstat(source.fileno())
        if not stat.S_ISREG(mode.st_mode) or mode.st_mode & 0o022:
            raise ValueError("Unsafe model file")
        raw = source.read(MAX_ARTIFACT_BYTES + 1)
    if len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError("Artifact exceeds limit")
    return Artifact.model_validate_json(raw)


def write_artifact(root: Path, artifact: Artifact) -> Path:
    import shutil
    import tempfile

    version = valid_version(artifact.info.model_version)
    decode(artifact, version)  # Validate before publishing.
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.is_symlink() or root.stat().st_mode & 0o022:
        raise ValueError("Unsafe model directory")
    destination = root / version
    if destination.exists():
        raise ValueError("Model version already exists; choose a new version")
    staging = Path(tempfile.mkdtemp(prefix=".training-", dir=root))
    try:
        raw = artifact.model_dump_json().encode()
        if len(raw) > MAX_ARTIFACT_BYTES:
            raise ValueError("Artifact exceeds limit")
        for name, content in (
            ("model.json", raw),
            (
                "evaluation.json",
                json.dumps(
                    {
                        "info": artifact.info.model_dump(),
                        "config": artifact.config.model_dump(),
                        "dataset_sha256": artifact.dataset_sha256,
                        "artifact_sha256": hashlib.sha256(raw).hexdigest(),
                        "sklearn_version": artifact.sklearn_version,
                        "numpy_version": artifact.numpy_version,
                        **artifact.evaluation,
                    },
                    indent=2,
                ).encode(),
            ),
        ):
            fd = os.open(staging / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as out:
                out.write(content)
                out.flush()
                os.fsync(out.fileno())
        os.rename(staging, destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return destination
