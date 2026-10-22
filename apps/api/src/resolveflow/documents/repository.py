import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from resolveflow.db.models import User
from resolveflow.db.ticket_queries import paginate
from resolveflow.documents.models import Document, DocumentChunk
from resolveflow.documents.schemas import ChunkResponse, DocumentQuery, DocumentResponse
from resolveflow.documents.validation import ERRORS
from resolveflow.schemas.tickets import Page, PageQuery


def scoped(db: Session, workspace_id: uuid.UUID, document_id: uuid.UUID, *, lock=False) -> Document:
    query = select(Document).where(
        Document.workspace_id == workspace_id, Document.id == document_id
    )
    doc = db.scalar(query.execution_options(populate_existing=True))
    if doc is None:
        raise HTTPException(404)
    if lock:
        doc = db.scalar(
            query.with_for_update(skip_locked=True).execution_options(populate_existing=True)
        )
        if doc is None:
            raise HTTPException(409)
    return doc


def response(doc: Document, email: str) -> DocumentResponse:
    return DocumentResponse(
        **{
            name: getattr(doc, name)
            for name in DocumentResponse.model_fields
            if name not in {"uploaded_by_email", "processing_error"}
        },
        uploaded_by_email=email,
        processing_error=ERRORS.get(doc.error_code),
    )


def document_response(db: Session, doc: Document) -> DocumentResponse:
    return response(doc, db.scalar(select(User.email).where(User.id == doc.uploaded_by)))


def list_documents(
    db: Session, workspace_id: uuid.UUID, query: DocumentQuery
) -> Page[DocumentResponse]:
    stmt = (
        select(Document, User.email)
        .join(User, User.id == Document.uploaded_by)
        .where(Document.workspace_id == workspace_id)
    )
    if query.search:
        pattern = (
            "%" + query.search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        )
        stmt = stmt.where(Document.original_filename.ilike(pattern, escape="\\"))
    if query.status:
        stmt = stmt.where(Document.processing_status == query.status)
    field = getattr(Document, query.sort)
    stmt = (
        stmt.order_by(field.asc(), Document.id.asc())
        if query.direction == "asc"
        else stmt.order_by(field.desc(), Document.id.desc())
    )
    rows, meta = paginate(db, stmt, query)
    return Page(items=[response(doc, email) for doc, email in rows], **meta)


def chunks(db: Session, doc: Document, query: PageQuery) -> Page[ChunkResponse]:
    stmt = (
        select(DocumentChunk)
        .where(DocumentChunk.workspace_id == doc.workspace_id, DocumentChunk.document_id == doc.id)
        .order_by(DocumentChunk.chunk_index)
    )
    rows, meta = paginate(db, stmt, query)
    return Page(items=[ChunkResponse.model_validate(row[0]) for row in rows], **meta)
