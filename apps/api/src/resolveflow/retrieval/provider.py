"""Offline, data-only local Sentence Transformer adapter. No request downloads."""

import json
from pathlib import Path
from threading import BoundedSemaphore

import numpy as np

from resolveflow.retrieval.contracts import (
    DIMENSIONS,
    REVISION,
    EmbeddingInfo,
    EmbeddingUnavailable,
    prepare,
    validate_vectors,
)

FILES = (
    "config.json",
    "config_sentence_transformers.json",
    "sentence_bert_config.json",
    "modules.json",
    "1_Pooling/config.json",
    "model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.txt",
)


def verify_snapshot(root: Path):
    if root.is_symlink() or not root.is_dir() or root.stat().st_mode & 0o022:
        raise ValueError("Unsafe model directory")
    manifest_path = root / "manifest.json"
    if manifest_path.is_symlink() or manifest_path.stat().st_size > 16384:
        raise ValueError("Unsafe model manifest")
    manifest = json.loads(manifest_path.read_text())
    if manifest["revision"] != REVISION or set(manifest["files"]) != set(FILES):
        raise ValueError("Incompatible model snapshot")
    import hashlib

    for name in FILES:
        path = root / name
        if path.is_symlink() or path.parent.is_symlink() or path.stat().st_mode & 0o022:
            raise ValueError("Unsafe model file")
        with path.open("rb") as file:
            digest = hashlib.file_digest(file, "sha256").hexdigest()
        if digest != manifest["files"][name]:
            raise ValueError("Model checksum mismatch")
    modules = json.loads((root / "modules.json").read_text())
    if [m["type"] for m in modules] != [
        "sentence_transformers.models.Transformer",
        "sentence_transformers.models.Pooling",
        "sentence_transformers.models.Normalize",
    ] or [m["path"] for m in modules] != ["", "1_Pooling", "2_Normalize"]:
        raise ValueError("Unsupported model modules")


class LocalSentenceTransformerProvider:
    def __init__(self, root: Path, device: str = "cpu", batch_size: int = 16):
        self._model = None
        self._slots = BoundedSemaphore(1)
        self.batch_size = batch_size
        self.info = EmbeddingInfo()
        try:
            verify_snapshot(root)
            import torch
            from sentence_transformers import SentenceTransformer

            torch.set_num_threads(2)
            selected = "mps" if device == "mps" and torch.backends.mps.is_available() else "cpu"
            self._model = SentenceTransformer(
                str(root),
                device=selected,
                local_files_only=True,
                trust_remote_code=False,
                model_kwargs={"use_safetensors": True},
            )
            if self._model.get_embedding_dimension() != DIMENSIONS:
                raise ValueError("Wrong model dimensions")
            self.info.device = selected
            self.embed_query("Local embedding startup check")
        except Exception:
            self._model = None

    def health_check(self) -> bool:
        return self._model is not None

    def get_dimensions(self) -> int:
        return DIMENSIONS

    def get_model_info(self) -> EmbeddingInfo:
        if not self.health_check():
            raise EmbeddingUnavailable("Local embeddings unavailable")
        return self.info.model_copy()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([prepare(text, 1000)])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not isinstance(texts, list) or not 1 <= len(texts) <= 32:
            raise ValueError("Expected 1–32 texts")
        texts = [prepare(t) for t in texts]
        self.get_model_info()
        if not self._slots.acquire(blocking=False):
            raise EmbeddingUnavailable("Local embeddings busy")
        try:
            parts, spans = [], []
            for text in texts:
                ids = self._model.tokenizer.encode(text, add_special_tokens=False)
                windows = [ids[i : i + 254] for i in range(0, len(ids), 222)]
                if not windows or len(windows) > 32:
                    raise ValueError("Text exceeds token window budget")
                start = len(parts)
                for window in windows:
                    part = self._model.tokenizer.decode(window, skip_special_tokens=True)
                    if len(self._model.tokenizer.encode(part, add_special_tokens=True)) > 256:
                        raise ValueError("Token window cannot be represented without truncation")
                    parts.append(part)
                spans.append((start, len(parts)))
            try:
                vectors = self._model.encode(
                    parts,
                    batch_size=self.batch_size,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                )
            except RuntimeError:
                if self.info.device != "mps":
                    raise
                self._model.to("cpu")
                self.info.device = "cpu"
                vectors = self._model.encode(
                    parts,
                    batch_size=self.batch_size,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                )
            result = []
            for start, end in spans:
                mean = np.asarray(vectors[start:end], dtype=np.float32).mean(axis=0)
                result.append(mean / np.linalg.norm(mean))
            return validate_vectors(result, len(texts))
        except Exception:
            raise EmbeddingUnavailable("Local embedding inference failed") from None
        finally:
            self._slots.release()
