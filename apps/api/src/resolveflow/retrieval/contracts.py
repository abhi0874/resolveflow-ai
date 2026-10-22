"""Provider-neutral retrieval contracts and embedding-space identity."""

import hashlib
import unicodedata
from typing import Protocol

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
DIMENSIONS = 384
# Includes the full-text window aggregation policy; changing it requires reindexing.
SPACE = f"{MODEL_ID}@{REVISION}:windows254-overlap32-mean-l2-v1"


class EmbeddingUnavailable(Exception):
    pass


class EmbeddingInfo(BaseModel):
    model_id: str = MODEL_ID
    revision: str = REVISION
    space: str = SPACE
    dimensions: int = DIMENSIONS
    device: str = "cpu"


class EmbeddingProvider(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...
    def get_dimensions(self) -> int: ...
    def get_model_info(self) -> EmbeddingInfo: ...
    def health_check(self) -> bool: ...


def prepare(text: str, limit: int = 4000) -> str:
    if not isinstance(text, str) or not 1 <= len(text) <= limit:
        raise ValueError("Invalid text length")
    if any(unicodedata.category(c) == "Cc" and c not in "\n\r\t" for c in text):
        raise ValueError("Invalid text characters")
    result = " ".join(unicodedata.normalize("NFC", text).split())
    if not result:
        raise ValueError("Empty text")
    return result


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_vectors(values, count: int, dimensions: int = DIMENSIONS) -> list[list[float]]:
    data = np.asarray(values, dtype=np.float32)
    if data.shape != (count, dimensions) or not np.isfinite(data).all():
        raise ValueError("Invalid embedding dimensions or values")
    norms = np.linalg.norm(data, axis=1)
    if not np.all((norms >= 0.999) & (norms <= 1.001)):
        raise ValueError("Embeddings must be nonzero unit vectors")
    return data.tolist()


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    min_similarity: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)

    @field_validator("query")
    @classmethod
    def query_text(cls, value):
        return prepare(value, 1000)


class IndexRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    force: bool = False
