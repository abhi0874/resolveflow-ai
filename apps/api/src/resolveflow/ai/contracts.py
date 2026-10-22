"""Provider-neutral requests/results. No SDK objects cross this boundary."""

from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class GenerationDiagnostics(BaseModel):
    """Content-free metadata for opt-in diagnostics; never raw provider/validation errors."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    model: str = Field(pattern=r"^[a-zA-Z0-9.-]{1,100}$")
    operation_status: Literal[
        "not_started", "requesting", "response_received", "api_error", "timeout", "client_error"
    ] = "not_started"
    stage: Literal["configuration", "request", "finish", "text", "json", "schema", "complete"] = (
        "configuration"
    )
    # Adapters allowlist provider enum members; unknown values become UNKNOWN.
    finish_reason: str | None = Field(default=None, pattern=r"^[A-Z_]{1,64}$")
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    thinking_tokens: int | None = Field(default=None, ge=0)
    text_present: bool | None = None
    json_decoded: bool | None = None
    schema_validated: bool | None = None
    validation_categories: tuple[
        Literal[
            "no_candidate",
            "non_success_finish",
            "empty_text",
            "oversized_text",
            "invalid_json",
            "missing_field",
            "unexpected_field",
            "invalid_type",
            "invalid_literal",
            "length_limit",
            "schema_constraint",
        ],
        ...,
    ] = ()


class AIError(Exception):
    def __init__(
        self,
        code: str,
        retry_after: int | None = None,
        *,
        diagnostics: GenerationDiagnostics | None = None,
    ):
        self.code, self.retry_after = code, retry_after
        self.diagnostics = diagnostics
        super().__init__(code)


class ProviderInfo(BaseModel):
    provider: str
    model: str
    fixture: bool = False


class Statement(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=1000)
    chunk_id: str = Field(min_length=36, max_length=36)
    supporting_quote: str = Field(min_length=10, max_length=1000)


class GeneratedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    response_text: str = Field(min_length=1, max_length=5000)
    statements: list[Statement] = Field(max_length=8)
    requires_human_review: Literal[True]
    insufficient_evidence: bool
    uncertainty_notes: str = Field(max_length=1000)
    suggested_next_steps: list[Annotated[str, Field(max_length=300)]] = Field(max_length=5)


class GenerationInput(BaseModel):
    system: str = Field(max_length=6000)
    content: str = Field(max_length=20000)
    max_output_tokens: int = Field(ge=128, le=2048)


class GenerationResult(BaseModel):
    output: GeneratedResponse
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    duration_ms: float = Field(ge=0, allow_inf_nan=False)
    diagnostics: GenerationDiagnostics | None = None


class AIProvider(Protocol):
    def generate_structured(self, request: GenerationInput) -> GenerationResult: ...
    def get_model_info(self) -> ProviderInfo: ...
    def health_check(self) -> bool: ...
    def close(self) -> None: ...
