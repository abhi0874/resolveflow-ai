import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GenerateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: uuid.UUID
    expected_ticket_version: int = Field(ge=1)
    synthetic_confirmed: bool = False


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    action: Literal["approved", "rejected", "needs_revision"]


class CitationResponse(BaseModel):
    document_id: uuid.UUID
    chunk_id: uuid.UUID
    document_name: str
    chunk_index: int
    page_number: int | None
    supporting_quote: str
    similarity_score: float


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    actor_id: uuid.UUID
    decision: str
    draft_version: int
    response_hash: str
    created_at: datetime


class DraftResponse(BaseModel):
    id: uuid.UUID
    ticket_id: uuid.UUID
    ticket_version: int
    version: int
    generation_status: str
    review_status: str
    provider: str
    model: str
    fixture: bool
    prompt_version: str
    generation_origin: str
    response_text: str | None
    insufficient_evidence: bool
    uncertainty_notes: str | None
    suggested_next_steps: list[str]
    error_code: str | None
    created_at: datetime
    input_tokens: int | None
    output_tokens: int | None
    duration_ms: float | None
    citations: list[CitationResponse]
    sources_current: bool
    ticket_current: bool
    can_approve: bool
    approval_current: bool
    requires_human_review: Literal[True] = True
    review: ReviewResponse | None


class DraftConfig(BaseModel):
    provider: str
    model: str
    fixture: bool
    available: bool
    synthetic_confirmation_required: bool
    max_ticket_chars: int
