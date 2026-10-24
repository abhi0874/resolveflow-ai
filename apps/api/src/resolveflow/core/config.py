from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

API_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Current configuration only; future integrations must add validated fields."""

    model_config = SettingsConfigDict(
        env_prefix="RESOLVEFLOW_",
        env_file=API_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="forbid",
        populate_by_name=True,
        hide_input_in_errors=True,
    )

    environment: Literal["development", "test", "production"] = "development"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    docs_enabled: bool = True
    database_url: SecretStr | None = Field(default=None, validation_alias="DATABASE_URL")
    db_pool_size: int = Field(default=5, ge=1, le=30)
    db_max_overflow: int = Field(default=5, ge=0, le=30)
    db_pool_timeout: int = Field(default=3, ge=1, le=30)
    db_connect_timeout: int = Field(default=3, ge=1, le=30)
    db_statement_timeout_ms: int = Field(default=5000, ge=100, le=120000)

    trusted_origins: list[str] = ["http://127.0.0.1:3000", "http://localhost:3000"]
    session_hours: int = Field(default=12, ge=1, le=168)
    require_email_verification: bool | None = None
    email_delivery: Literal["disabled", "local", "smtp"] = "disabled"
    email_public_origin: str = "http://127.0.0.1:3000"
    email_from: str = "no-reply@resolveflow.test"
    smtp_host: str = "127.0.0.1"
    smtp_port: int = Field(default=1025, ge=1, le=65535)
    smtp_tls: Literal["starttls", "ssl", "none"] = "none"
    smtp_username: str = ""
    smtp_password: SecretStr | None = None
    smtp_timeout_seconds: int = Field(default=5, ge=1, le=10)

    @property
    def email_verification_required(self) -> bool:
        return self.environment == "production" or self.require_email_verification is True

    @model_validator(mode="after")
    def email_settings(self):
        from email_validator import validate_email

        validate_email(self.email_from, check_deliverability=False, test_environment=True)
        origin = urlsplit(self.email_public_origin)
        if (
            origin.scheme not in {"http", "https"}
            or not origin.hostname
            or origin.username
            or origin.password
            or origin.path not in {"", "/"}
            or origin.query
            or origin.fragment
        ):
            raise ValueError("Email links require a configured origin without path or credentials")
        if self.environment == "production":
            if self.require_email_verification is False:
                raise ValueError("Production requires email verification")
            if self.email_delivery == "local":
                raise ValueError("Local email delivery is forbidden in production")
        if self.email_delivery == "local":
            if (
                self.smtp_host not in {"127.0.0.1", "::1"}
                or self.smtp_tls != "none"
                or self.smtp_username
                or self.smtp_password
            ):
                raise ValueError("Local inbox must be loopback only without external credentials")
        if self.email_delivery == "smtp":
            if (
                self.smtp_tls == "none"
                or not self.smtp_username
                or not self.smtp_password
                or not self.smtp_password.get_secret_value()
            ):
                raise ValueError("SMTP requires authenticated TLS")
            if origin.scheme != "https" or origin.hostname in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("External SMTP links require an HTTPS public origin")
        if any(c in self.smtp_host + self.smtp_username + self.email_from for c in "\r\n"):
            raise ValueError("Invalid email transport configuration")
        return self

    invitation_delivery: Literal["disabled", "local"] = "disabled"
    invitation_delivery_root: Path = API_ROOT.parents[1] / ".local" / "invitation-mailbox"

    @model_validator(mode="after")
    def invitation_settings(self):
        if self.environment == "production" and self.invitation_delivery != "disabled":
            raise ValueError("Local invitation delivery is forbidden in production")
        root = self.invitation_delivery_root
        if not root.is_absolute() or any(
            root.resolve().is_relative_to(path.resolve())
            or path.resolve().is_relative_to(root.resolve())
            for path in (
                API_ROOT.parent / "web" / "public",
                self.document_storage_root,
                self.classifier_artifact_root,
                self.embedding_model_root,
            )
        ):
            raise ValueError("Invitation delivery requires a separate absolute private path")
        return self

    classifier_artifact_root: Path = API_ROOT.parents[1] / ".local" / "classifier"
    classifier_model_version: str = Field(
        default="baseline-v1", pattern=r"^[a-z0-9][a-z0-9-]{0,63}$"
    )
    classifier_threshold: float = Field(default=0.45, ge=0.15, le=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def classifier_settings(self):
        root = self.classifier_artifact_root
        public = API_ROOT.parent / "web" / "public"
        if not root.is_absolute() or root.resolve().is_relative_to(public.resolve()):
            raise ValueError("Classifier storage must be an absolute private path")
        if root.resolve().is_relative_to(self.document_storage_root.resolve()):
            raise ValueError("Models must be separate from uploaded documents")
        return self

    ai_provider: Literal["gemini", "fixture"] = "gemini"
    ai_model: str = Field(default="gemini-3.6-flash", pattern=r"^[a-zA-Z0-9.-]{1,100}$")
    gemini_api_key: SecretStr | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    # "default" omits thinking configuration when selecting a different model.
    gemini_thinking_level: Literal["minimal", "low", "medium", "high", "default"] = "minimal"
    ai_live_enabled: bool = False
    ai_free_tier_verified: bool = False
    ai_synthetic_workspaces: list[UUID] = []
    ai_timeout_seconds: int = Field(default=25, ge=1, le=30)
    ai_max_retries: Literal[0] = 0
    ai_max_calls: Literal[1] = 1
    ai_concurrency: int = Field(default=2, ge=1, le=4)
    ai_daily_global: int = Field(default=20, ge=1, le=100)
    ai_daily_workspace: int = Field(default=10, ge=1, le=50)
    ai_daily_user: int = Field(default=5, ge=1, le=25)
    ai_context_chars: int = Field(default=6000, ge=500, le=8000)
    ai_ticket_chars: int = Field(default=4000, ge=200, le=8000)
    ai_top_k: int = Field(default=4, ge=1, le=8)
    ai_max_output_tokens: int = Field(default=1024, ge=128, le=2048)
    workflow_concurrency: int = Field(default=2, ge=1, le=4)
    workflow_timeout_seconds: int = Field(default=60, ge=10, le=90)
    workflow_max_attempts: int = Field(default=3, ge=1, le=5)
    redis_url: SecretStr = SecretStr("redis://127.0.0.1:56379/0")
    job_queue: str = Field(default="resolveflow-workflows", pattern=r"^[a-z0-9-]{1,80}$")
    worker_concurrency: int = Field(default=1, ge=1, le=4)
    job_workspace_concurrency: int = Field(default=1, ge=1, le=4)
    job_timeout_seconds: int = Field(default=120, ge=30, le=300)
    job_max_attempts: int = Field(default=3, ge=1, le=5)
    job_queue_capacity: int = Field(default=50, ge=1, le=500)
    job_max_pending: int = Field(default=100, ge=1, le=1000)
    job_workspace_pending: int = Field(default=10, ge=1, le=100)
    job_reconcile_seconds: int = Field(default=5, ge=1, le=60)
    workflow_inline_tests: bool = False
    workflow_daily_user: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def ai_settings(self):
        if self.workflow_inline_tests and self.environment != "test":
            raise ValueError("Inline workflow execution is restricted to tests")
        if self.ai_provider == "fixture" and self.environment != "test":
            raise ValueError("Fixture provider is restricted to test environments")
        return self

    embedding_model_root: Path = API_ROOT.parents[1] / ".local" / "embeddings" / "minilm-v1"
    embedding_device: Literal["cpu", "mps"] = "cpu"
    embedding_batch_size: int = Field(default=16, ge=1, le=32)
    indexing_max_chunks: int = Field(default=256, ge=1, le=2000)
    indexing_timeout_seconds: int = Field(default=40, ge=5, le=45)
    search_min_similarity: float = Field(default=0.30, ge=0, le=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def embedding_settings(self):
        root = self.embedding_model_root
        if (
            not root.is_absolute()
            or root.resolve().is_relative_to((API_ROOT.parent / "web" / "public").resolve())
            or root.resolve().is_relative_to(self.document_storage_root.resolve())
        ):
            raise ValueError("Embedding models require a separate absolute private path")
        return self

    document_storage_root: Path = API_ROOT.parents[1] / ".local" / "documents"
    document_upload_max_bytes: int = Field(default=2 * 1024**2, ge=1024, le=5 * 1024**2)
    document_max_pages: int = Field(default=100, ge=1, le=200)
    document_max_chars: int = Field(default=500000, ge=1000, le=1000000)
    document_timeout_seconds: int = Field(default=15, ge=1, le=30)
    document_memory_mb: int = Field(default=256, ge=64, le=512)
    document_chunk_size: int = Field(default=1200, ge=100, le=4000)
    document_chunk_overlap: int = Field(default=150, ge=0, le=1000)

    @model_validator(mode="after")
    def document_settings(self):
        if self.document_chunk_overlap >= self.document_chunk_size:
            raise ValueError("Document overlap must be smaller than chunk size")
        root = self.document_storage_root
        public = API_ROOT.parent / "web" / "public"
        if not root.is_absolute() or root.resolve().is_relative_to(public.resolve()):
            raise ValueError("Document storage must be an absolute private path")
        return self

    @property
    def cookie_name(self) -> str:
        return (
            "__Host-resolveflow_session"
            if self.environment == "production"
            else "resolveflow_session"
        )

    @model_validator(mode="after")
    def production_security(self):
        if not self.trusted_origins:
            raise ValueError("At least one explicit trusted application origin is required")
        self.validate_origins(self.trusted_origins)
        if self.environment == "production" and any(
            not origin.startswith("https://")
            or urlsplit(origin).hostname in {"localhost", "127.0.0.1", "::1"}
            for origin in self.trusted_origins
        ):
            raise ValueError("Production requires explicit HTTPS application origins")
        return self

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        try:
            url = make_url(value.get_secret_value())
            if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}:
                raise ValueError
            if not url.database or not url.host or not url.username:
                raise ValueError
            if url.port is not None and not 1 <= url.port <= 65535:
                raise ValueError
            url = url.set(drivername="postgresql+psycopg")
        except ArgumentError, ValueError:
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL URL with username, host and database"
            ) from None
        return SecretStr(url.render_as_string(hide_password=False))

    @field_validator("cors_origins")
    @classmethod
    def validate_origins(cls, origins: list[str]) -> list[str]:
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("CORS origins must be explicit HTTP(S) origins without paths")
            # Accessing port also validates the range and numeric format.
            _ = parsed.port
        return origins
