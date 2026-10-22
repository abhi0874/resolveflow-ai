from datetime import datetime
from typing import Literal, TypedDict
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from resolveflow.ml.contracts import Prediction
from resolveflow.rag.schemas import DraftResponse, GenerateInput

VERSION = "ticket-workflow-v1"
STAGES = (
    "classification",
    "priority",
    "retrieval",
    "context",
    "generation",
    "verification",
    "approval",
)
TERMINAL = {"completed", "rejected", "needs_revision", "failed", "cancelled"}


class EvidenceReference(TypedDict):
    document_id: str
    chunk_id: str
    content_hash: str
    similarity_score: float


class WorkflowState(TypedDict, total=False):
    execution_id: str
    workspace_id: str
    ticket_id: str
    ticket_version: int
    workflow_version: str
    current_stage: str
    completed_stages: list[str]
    classification: dict
    priority: dict
    evidence: list[EvidenceReference]
    context_summary: dict
    draft_id: str | None
    verification: dict
    approval_status: str
    status: str
    started_at: str
    updated_at: str
    finished_at: str | None
    error: dict | None
    timings_ms: dict[str, float]


class StartInput(GenerateInput):
    pass


class ResumeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PriorityRecommendation(BaseModel):
    suggested_priority: Literal["low", "medium", "high", "urgent"]
    rule_ids: list[str]
    requires_review: Literal[True] = True
    rules_version: Literal["priority-rules-v1"] = "priority-rules-v1"


class EvidenceView(BaseModel):
    document_id: UUID
    chunk_id: UUID
    document_name: str
    chunk_index: int
    similarity_score: float


class JobResponse(BaseModel):
    id: UUID
    kind: Literal["start", "resume", "cancel"]
    status: Literal["queued", "running", "waiting_for_approval", "completed", "failed", "cancelled"]
    attempts: int = Field(ge=0)
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    next_attempt_at: datetime | None
    error_code: str | None


class ExecutionResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    ticket_id: UUID
    requested_by: UUID
    workflow_version: str
    status: str
    current_stage: str
    completed_stages: list[str]
    classification: Prediction | None
    classification_unavailable: bool = False
    priority: PriorityRecommendation | None
    evidence: list[EvidenceView]
    context_summary: dict
    verification: dict
    approval_status: str
    draft: DraftResponse | None
    error_code: str | None
    failed_stage: str | None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None
    timings_ms: dict[str, float]
    attempts: int = Field(ge=0)
    can_resume: bool
    job: JobResponse | None = None
    cancel_requested: bool = False
