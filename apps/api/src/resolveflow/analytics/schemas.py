from datetime import UTC, date, datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DateRange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: date = Field(default_factory=lambda: datetime.now(UTC).date() - timedelta(days=29))
    end: date = Field(default_factory=lambda: datetime.now(UTC).date())

    @model_validator(mode="after")
    def bounds(self):
        if self.start > self.end or (self.end - self.start).days >= 366:
            raise ValueError("Select an ordered range of at most 366 UTC days")
        if self.end > datetime.now(UTC).date():
            raise ValueError("Future dates are not supported")
        return self

    def timestamps(self):
        return (
            datetime.combine(self.start, datetime.min.time(), UTC),
            datetime.combine(self.end + timedelta(days=1), datetime.min.time(), UTC),
        )


class Distribution(BaseModel):
    label: str
    count: int = Field(ge=0)


class Trend(BaseModel):
    day: date
    count: int = Field(ge=0)


class Measurement(BaseModel):
    value: float | None
    samples: int = Field(ge=0)
    unavailable_reason: str | None = None


class TicketAnalytics(BaseModel):
    total: int
    statuses: list[Distribution]
    priorities: list[Distribution]
    categories: list[Distribution]
    created_trend: list[Trend]
    resolution_trend: list[Trend]
    resolution_average_seconds: Measurement
    resolution_median_seconds: Measurement
    resolution_history_excluded: int


class WorkflowAnalytics(BaseModel):
    total: int
    statuses: list[Distribution]
    stages: list[Distribution]
    success_rate: Measurement
    failure_rate: Measurement
    elapsed_average_seconds: Measurement


class JobAnalytics(BaseModel):
    current_statuses: list[Distribution]
    cohort_total: int
    retained_phase_retries: int
    latest_attempt_average_seconds: Measurement
    initial_wait_average_seconds: Measurement


class ReviewAnalytics(BaseModel):
    total_completed_drafts: int
    outcomes: list[Distribution]
    approval_rate: Measurement
    request_to_review_average_seconds: Measurement


class KnowledgeAnalytics(BaseModel):
    total: int
    processed: int
    failed: int
    indexed: int
    chunks: int
    upload_trend: list[Trend]


class Overview(BaseModel):
    range: DateRange
    generated_at: datetime
    tickets: TicketAnalytics
    workflows: WorkflowAnalytics
    jobs: JobAnalytics
    reviews: ReviewAnalytics
    knowledge_base: KnowledgeAnalytics
