import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from resolveflow.documents.models import DocumentStatus
from resolveflow.schemas.tickets import PageQuery


class DocumentQuery(PageQuery):
    search: str = Field(default="", max_length=200)
    status: DocumentStatus | None = None
    sort: Literal["created_at", "file_size"] = "created_at"
    direction: Literal["asc", "desc"] = "desc"


class DocumentResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    uploaded_by: uuid.UUID
    uploaded_by_email: str
    original_filename: str
    content_type: str
    file_size: int
    checksum: str
    processing_status: DocumentStatus
    total_chunks: int
    processing_error: str | None
    indexing_status: Literal["not_indexed", "indexing", "indexed", "failed"]
    indexing_error: str | None
    indexed_model: str | None
    created_at: datetime
    updated_at: datetime


class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    document_id: uuid.UUID
    workspace_id: uuid.UUID
    chunk_index: int
    content: str
    character_count: int
    page_number: int | None
    source_metadata: dict[str, str | int]
    created_at: datetime


class UploadConfig(BaseModel):
    max_bytes: int
    formats: list[str] = ["pdf", "txt", "md"]
    max_pages: int
    chunk_size: int
    chunk_overlap: int
