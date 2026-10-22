"""One loaded model per app lifespan, bounded batches, no retraining during inference."""

import math
from pathlib import Path
from threading import BoundedSemaphore

import numpy as np

from resolveflow.ml.artifact import decode, read_artifact
from resolveflow.ml.contracts import ModelInfo, ModelUnavailable, Prediction, TicketText


class LocalTicketClassifier:
    def __init__(self, root: Path, version: str, threshold: float):
        if not math.isfinite(threshold) or not 0.15 <= threshold <= 1:
            raise ValueError("Invalid decision threshold")
        self.threshold = threshold
        self._pipeline = None
        self._info = None
        self._slots = BoundedSemaphore(2)
        try:
            artifact = read_artifact(root, version)
            self._pipeline = decode(artifact, version)
            self._info = artifact.info
            self.predict(TicketText(title="Model startup check"))
        except Exception:
            # Fail closed without leaking paths/content or disrupting auth/ticket availability.
            self._pipeline, self._info = None, None

    def health_check(self) -> bool:
        return self._pipeline is not None

    def get_model_info(self) -> ModelInfo:
        if not self.health_check() or self._info is None:
            raise ModelUnavailable("Classifier is unavailable")
        return self._info.model_copy()

    def predict(self, ticket: TicketText) -> Prediction:
        return self.predict_batch([ticket])[0]

    def predict_batch(self, tickets: list[TicketText]) -> list[Prediction]:
        if not isinstance(tickets, list) or not 1 <= len(tickets) <= 32:
            raise ValueError("Expected 1–32 tickets")
        if any(not isinstance(t, TicketText) for t in tickets):
            raise ValueError("Expected validated ticket text")
        info = self.get_model_info()
        if not self._slots.acquire(blocking=False):
            raise ModelUnavailable("Classifier is busy")
        try:
            texts = [t.combined() for t in tickets]
            features = self._pipeline.named_steps["tfidf"].transform(texts)
            model = self._pipeline.named_steps["classifier"]
            probabilities = model.predict_proba(features)
            if (
                probabilities.shape != (len(tickets), len(model.classes_))
                or not np.isfinite(probabilities).all()
            ):
                raise ValueError("Invalid prediction")
            result = []
            for i, probabilities_row in enumerate(probabilities):
                top = int(probabilities_row.argmax())
                category, score = str(model.classes_[top]), float(probabilities_row[top])
                uncertain = features[i].nnz == 0 or score < self.threshold
                result.append(
                    Prediction(
                        predicted_category=category,
                        suggested_category=None if uncertain else category,
                        score=score,
                        threshold=self.threshold,
                        uncertain=uncertain,
                        model_version=info.model_version,
                    )
                )
            return result
        except Exception:
            raise ModelUnavailable("Classifier inference is unavailable") from None
        finally:
            self._slots.release()
