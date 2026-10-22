"""DB-journalled private file lifecycle, with bounded synchronous processing."""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from resolveflow.core.config import Settings
from resolveflow.db.models import User
from resolveflow.documents import repository
from resolveflow.documents.chunking import chunk_pages
from resolveflow.documents.extraction import ProcessingError, extract
from resolveflow.documents.models import Document, DocumentChunk
from resolveflow.documents.models import DocumentStatus as Status
from resolveflow.documents.storage import Storage
from resolveflow.documents.validation import validate_upload
from resolveflow.services.authorization import Permission, access


def upload(
    db: Session,
    user: User,
    workspace_id: uuid.UUID,
    filename: str,
    data: bytes,
    storage: Storage,
    settings: Settings,
) -> Document:
    access(db, user, workspace_id, Permission.DOCUMENT_UPLOAD, lock=True)
    filename, mime = validate_upload(filename, data, settings.document_upload_max_bytes)
    checksum = hashlib.sha256(data).hexdigest()
    existing = db.scalar(
        select(Document).where(Document.workspace_id == workspace_id, Document.checksum == checksum)
    )
    if existing:
        if existing.processing_status == Status.DELETING:
            raise HTTPException(409)
        return existing  # Content-identical uploads are durable idempotent within this tenant.
    doc = Document(
        workspace_id=workspace_id,
        uploaded_by=user.id,
        original_filename=filename,
        storage_key=uuid.uuid4().hex,
        content_type=mime,
        file_size=len(data),
        checksum=checksum,
        processing_config={
            "version": 1,
            "chunk_size": settings.document_chunk_size,
            "overlap": settings.document_chunk_overlap,
        },
    )
    db.add(doc)
    db.commit()  # Journal exists before any filesystem write.
    doc = repository.scoped(db, workspace_id, doc.id, lock=True)
    try:
        storage.save(workspace_id, doc.storage_key, data)
    except OSError:
        doc.processing_status, doc.error_code = Status.FAILED, "storage_error"
        db.commit()
        return doc
    doc.processing_status, doc.processing_token = Status.PROCESSING, uuid.uuid4()
    token = doc.processing_token
    db.commit()
    return process_claim(db, workspace_id, doc.id, token, storage, settings)


def retry(
    db: Session,
    user: User,
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    storage: Storage,
    settings: Settings,
) -> Document:
    access(db, user, workspace_id, Permission.DOCUMENT_UPLOAD, lock=True)
    doc = repository.scoped(db, workspace_id, document_id, lock=True)
    if doc.processing_status == Status.COMPLETED:
        return doc
    if doc.processing_status != Status.FAILED:
        raise HTTPException(409)
    doc.processing_status, doc.error_code, doc.processing_token = (
        Status.PROCESSING,
        None,
        uuid.uuid4(),
    )
    token = doc.processing_token
    db.commit()
    return process_claim(db, workspace_id, document_id, token, storage, settings)


def process_claim(
    db: Session,
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    token: uuid.UUID,
    storage: Storage,
    settings: Settings,
) -> Document:
    doc = repository.scoped(db, workspace_id, document_id, lock=True)
    if doc.processing_status != Status.PROCESSING or doc.processing_token != token:
        raise HTTPException(409)
    # Only this document stays locked during bounded extraction, not the workspace.
    # Deletion/recovery/retry uses skip-locked semantics and cannot race this claim.
    try:
        data = storage.read(workspace_id, doc.storage_key, 5 * 1024**2)
        if hashlib.sha256(data).hexdigest() != doc.checksum:
            raise ProcessingError("storage_error")
        pages = extract(data, doc.content_type, settings)
        pieces = chunk_pages(
            doc.id, pages, doc.processing_config["chunk_size"], doc.processing_config["overlap"]
        )
        if not pieces:
            raise ProcessingError("no_text")
    except OSError:
        doc.processing_status, doc.error_code = Status.FAILED, "storage_error"
    except ProcessingError as exc:
        doc.processing_status, doc.error_code = Status.FAILED, exc.code
    except ValueError:
        doc.processing_status, doc.error_code = Status.FAILED, "resource_limit"
    else:
        db.execute(
            delete(DocumentChunk).where(
                DocumentChunk.workspace_id == workspace_id, DocumentChunk.document_id == doc.id
            )
        )
        for piece in pieces:
            db.add(
                DocumentChunk(
                    id=piece.id,
                    document_id=doc.id,
                    workspace_id=workspace_id,
                    chunk_index=piece.index,
                    content=piece.content,
                    character_count=len(piece.content),
                    page_number=piece.page_number,
                    source_metadata={
                        "filename": doc.original_filename,
                        "start_offset": piece.start,
                        "end_offset": piece.end,
                        "pipeline_version": 1,
                    },
                )
            )
        doc.total_chunks, doc.processing_status, doc.error_code = (
            len(pieces),
            Status.COMPLETED,
            None,
        )
    doc.processing_token = None
    db.commit()  # Chunks and success status become visible together.
    return doc


def remove(
    db: Session, user: User, workspace_id: uuid.UUID, document_id: uuid.UUID, storage: Storage
) -> None:
    access(db, user, workspace_id, Permission.DOCUMENT_DELETE, lock=True)
    doc = repository.scoped(db, workspace_id, document_id, lock=True)
    doc.processing_status, doc.processing_token = Status.DELETING, None
    db.execute(
        delete(DocumentChunk).where(
            DocumentChunk.workspace_id == workspace_id, DocumentChunk.document_id == document_id
        )
    )
    doc.indexing_status, doc.indexing_token, doc.indexed_model = "not_indexed", None, None
    doc.total_chunks = 0
    db.commit()  # Tombstone prevents serving content if file deletion fails.
    if not finish_delete(db, workspace_id, document_id, storage):
        raise HTTPException(503)


def finish_delete(
    db: Session, workspace_id: uuid.UUID, document_id: uuid.UUID, storage: Storage
) -> bool:
    doc = repository.scoped(db, workspace_id, document_id, lock=True)
    if doc.processing_status != Status.DELETING:
        raise HTTPException(409)
    try:
        storage.delete(workspace_id, doc.storage_key)
    except OSError:
        doc.error_code = "delete_failed"
        db.commit()
        return False
    db.delete(doc)
    db.commit()  # Crash here leaves a tracked tombstone; missing files are safe on retry.
    return True


def recover(db: Session, storage: Storage, settings: Settings) -> int:
    """Explicit maintenance. Skip live document locks; never scan arbitrary filesystem paths."""
    threshold = datetime.now(UTC) - timedelta(seconds=settings.document_timeout_seconds + 60)
    ids = db.execute(
        select(Document.workspace_id, Document.id)
        .where(
            Document.processing_status.in_([Status.PENDING, Status.PROCESSING, Status.DELETING]),
            Document.updated_at < threshold,
        )
        .limit(100)
    ).all()
    db.rollback()
    recovered = 0
    for workspace_id, document_id in ids:
        try:
            doc = repository.scoped(db, workspace_id, document_id, lock=True)
        except HTTPException:
            db.rollback()
            continue
        if doc.updated_at >= threshold:
            db.rollback()
            continue
        if doc.processing_status == Status.DELETING:
            recovered += int(finish_delete(db, workspace_id, document_id, storage))
        elif doc.processing_status in {Status.PENDING, Status.PROCESSING}:
            doc.processing_status, doc.error_code, doc.processing_token = (
                Status.FAILED,
                "interrupted",
                None,
            )
            db.commit()
            recovered += 1
        else:
            db.rollback()
    return recovered
