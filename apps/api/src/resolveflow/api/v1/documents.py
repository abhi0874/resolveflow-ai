import hashlib
import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Body, Header, HTTPException, Query, Request, Response

from resolveflow.documents import repository, service
from resolveflow.documents.models import DocumentStatus
from resolveflow.documents.schemas import (
    ChunkResponse,
    DocumentQuery,
    DocumentResponse,
    UploadConfig,
)
from resolveflow.retrieval import service as retrieval
from resolveflow.retrieval.contracts import IndexRequest
from resolveflow.schemas.tickets import Page, PageQuery
from resolveflow.services.auth import CSRF, DB, CurrentUser
from resolveflow.services.authorization import Permission, access

router = APIRouter(prefix="/workspaces/{workspace_id}/documents", tags=["documents"])


@router.get("/config", response_model=UploadConfig)
def config(workspace_id: uuid.UUID, request: Request, db: DB, user: CurrentUser):
    access(db, user, workspace_id)
    settings = request.app.state.settings
    return UploadConfig(
        max_bytes=settings.document_upload_max_bytes,
        max_pages=settings.document_max_pages,
        chunk_size=settings.document_chunk_size,
        chunk_overlap=settings.document_chunk_overlap,
    )


@router.post("", response_model=DocumentResponse, status_code=201)
def upload(
    workspace_id: uuid.UUID,
    request: Request,
    db: DB,
    user: CurrentUser,
    csrf: CSRF,
    content: Annotated[bytes, Body(media_type="application/octet-stream")],
    filename: Annotated[str, Header(alias="X-Upload-Filename", max_length=2048)],
):
    doc = service.upload(
        db,
        user,
        workspace_id,
        filename,
        content,
        request.app.state.document_storage,
        request.app.state.settings,
    )
    return repository.document_response(db, doc)


@router.get("", response_model=Page[DocumentResponse])
def listing(
    workspace_id: uuid.UUID, query: Annotated[DocumentQuery, Query()], db: DB, user: CurrentUser
):
    access(db, user, workspace_id)
    return repository.list_documents(db, workspace_id, query)


@router.get("/{document_id}", response_model=DocumentResponse)
def detail(workspace_id: uuid.UUID, document_id: uuid.UUID, db: DB, user: CurrentUser):
    access(db, user, workspace_id)
    return repository.document_response(db, repository.scoped(db, workspace_id, document_id))


@router.get("/{document_id}/chunks", response_model=Page[ChunkResponse])
def chunks(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    query: Annotated[PageQuery, Query()],
    db: DB,
    user: CurrentUser,
):
    access(db, user, workspace_id, Permission.DOCUMENT_CONTENT)
    doc = repository.scoped(db, workspace_id, document_id)
    if doc.processing_status != DocumentStatus.COMPLETED:
        raise HTTPException(409)
    return repository.chunks(db, doc, query)


@router.get("/{document_id}/download")
def download(
    workspace_id: uuid.UUID, document_id: uuid.UUID, request: Request, db: DB, user: CurrentUser
):
    access(db, user, workspace_id, Permission.DOCUMENT_CONTENT)
    doc = repository.scoped(db, workspace_id, document_id, lock=True)
    if doc.processing_status != DocumentStatus.COMPLETED:
        raise HTTPException(409)
    try:
        content = request.app.state.document_storage.read(
            workspace_id, doc.storage_key, 5 * 1024**2
        )
    except OSError:
        raise HTTPException(503) from None
    if hashlib.sha256(content).hexdigest() != doc.checksum:
        raise HTTPException(503)
    return Response(
        content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": "attachment; filename*=UTF-8''"
            + quote(doc.original_filename, safe=""),
            "Content-Security-Policy": "sandbox",
        },
    )


@router.post("/{document_id}/retry", response_model=DocumentResponse)
def retry(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    request: Request,
    db: DB,
    user: CurrentUser,
    csrf: CSRF,
):
    doc = service.retry(
        db,
        user,
        workspace_id,
        document_id,
        request.app.state.document_storage,
        request.app.state.settings,
    )
    return repository.document_response(db, doc)


@router.delete("/{document_id}", status_code=204)
def remove(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    request: Request,
    db: DB,
    user: CurrentUser,
    csrf: CSRF,
):
    service.remove(db, user, workspace_id, document_id, request.app.state.document_storage)


@router.post("/{document_id}/index", response_model=DocumentResponse)
def index_document(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    body: IndexRequest,
    request: Request,
    db: DB,
    user: CurrentUser,
    csrf: CSRF,
):
    doc = retrieval.index_document(
        db,
        user,
        workspace_id,
        document_id,
        request.app.state.embeddings,
        request.app.state.settings,
        body.force,
    )
    return repository.document_response(db, doc)
