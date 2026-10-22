import unicodedata
from enum import StrEnum
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Category(StrEnum):
    BILLING = "Billing"
    TECHNICAL = "Technical Support"
    ACCESS = "Account Access"
    SUBSCRIPTION = "Subscription Management"
    PRODUCT = "Product Inquiry"
    GENERAL = "General Support"
    OTHER = "Other"


CATEGORY_VERSION = "support-categories-v1"
LABELS = sorted(c.value for c in Category)
PREPROCESSING_VERSION = "ticket-text-v1"


class TicketText(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)
    title: str = Field(max_length=200)
    description: str = Field(default="", max_length=8000)

    @field_validator("title", "description")
    @classmethod
    def normalize(cls, value: str) -> str:
        if any(unicodedata.category(c).startswith("C") and c not in "\r\n\t" for c in value):
            raise ValueError("Unsupported control characters")
        return " ".join(unicodedata.normalize("NFC", value).split())

    @model_validator(mode="after")
    def nonempty(self):
        if not (self.title or self.description):
            raise ValueError("Ticket text is empty")
        return self

    def combined(self) -> str:
        return f"{self.title}\n{self.description}".strip()


class ModelInfo(BaseModel):
    model_version: str
    trained_at: str
    dataset_version: str
    category_mapping_version: str
    algorithm: Literal["TF-IDF + Logistic Regression"] = "TF-IDF + Logistic Regression"


class Prediction(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    predicted_category: Category
    suggested_category: Category | None
    score: float = Field(ge=0, le=1)
    score_kind: Literal["uncalibrated_model_probability"] = "uncalibrated_model_probability"
    threshold: float = Field(ge=0, le=1)
    uncertain: bool
    human_review_recommended: bool = True
    model_version: str
    category_mapping_version: str = CATEGORY_VERSION


class ModelUnavailable(Exception):
    """Safe unavailable state; never contains artifact paths or ticket text."""


class TicketClassifier(Protocol):
    def predict(self, ticket: TicketText) -> Prediction: ...
    def predict_batch(self, tickets: list[TicketText]) -> list[Prediction]: ...
    def get_model_info(self) -> ModelInfo: ...
    def health_check(self) -> bool: ...
