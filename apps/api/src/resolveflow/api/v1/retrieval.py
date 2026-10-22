import uuid

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from resolveflow.retrieval.contracts import EmbeddingInfo, SearchRequest
from resolveflow.retrieval.service import search
from resolveflow.services.auth import CSRF, DB, CurrentUser

router = APIRouter(prefix="/workspaces/{workspace_id}/knowledge-base", tags=["semantic search"])


class SearchResult(BaseModel):
    document_id: uuid.UUID
    chunk_id: uuid.UUID
    document_name: str
    content: str
    chunk_index: int
    page_number: int | None
    source_metadata: dict[str, str | int]
    similarity_score: float = Field(ge=-1.000001, le=1.000001, allow_inf_nan=False)


class SearchResponse(BaseModel):
    query: str
    model: EmbeddingInfo
    min_similarity: float
    results: list[SearchResult]


@router.post("/search", response_model=SearchResponse)
def semantic_search(
    workspace_id: uuid.UUID,
    body: SearchRequest,
    request: Request,
    db: DB,
    user: CurrentUser,
    csrf: CSRF,
):
    return search(
        db, user, workspace_id, body, request.app.state.embeddings, request.app.state.settings
    )
