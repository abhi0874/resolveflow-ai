"""Tenant-scoped indexing commands and exact database-side cosine retrieval."""

import time
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from resolveflow.core.config import Settings
from resolveflow.db.models import User
from resolveflow.documents.models import Document, DocumentChunk, DocumentStatus
from resolveflow.documents.repository import scoped
from resolveflow.retrieval.contracts import (
    DIMENSIONS,
    EmbeddingProvider,
    EmbeddingUnavailable,
    SearchRequest,
    fingerprint,
    validate_vectors,
)
from resolveflow.retrieval.models import ChunkEmbedding as E
from resolveflow.services.authorization import Permission, access


def content_hash():
    return func.encode(func.sha256(func.convert_to(DocumentChunk.content, "UTF8")), "hex")


def current_embeddings(workspace_id, document_id, space):
    return (
        select(func.count())
        .select_from(DocumentChunk)
        .join(
            E,
            and_(
                E.chunk_id == DocumentChunk.id,
                E.workspace_id == DocumentChunk.workspace_id,
                E.document_id == DocumentChunk.document_id,
            ),
        )
        .where(
            DocumentChunk.workspace_id == workspace_id,
            DocumentChunk.document_id == document_id,
            E.model_space == space,
            E.content_hash == content_hash(),
            func.vector_norm(E.embedding).between(0.999, 1.001),
        )
    )


def index_document(
    db: Session,
    user: User,
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    provider: EmbeddingProvider,
    settings: Settings,
    force: bool = False,
) -> Document:
    access(db, user, workspace_id, Permission.DOCUMENT_UPLOAD, lock=True)
    doc = scoped(db, workspace_id, document_id, lock=True)
    if doc.processing_status != DocumentStatus.COMPLETED or doc.total_chunks == 0:
        raise HTTPException(409)
    info = provider.get_model_info()
    if info.dimensions != DIMENSIONS or provider.get_dimensions() != DIMENSIONS:
        raise EmbeddingUnavailable("Embedding dimension requires a migration")
    if doc.total_chunks > settings.indexing_max_chunks:
        raise HTTPException(422)
    if doc.indexing_status == "indexing":
        # An active worker owns the document row lock. Only old abandoned claims can be retried.
        if doc.updated_at > datetime.now(UTC) - timedelta(
            seconds=settings.indexing_timeout_seconds + 60
        ):
            raise HTTPException(409)
    valid_count = db.scalar(current_embeddings(workspace_id, document_id, info.space))
    actual_count = db.scalar(
        select(func.count())
        .select_from(DocumentChunk)
        .where(DocumentChunk.workspace_id == workspace_id, DocumentChunk.document_id == document_id)
    )
    if actual_count != doc.total_chunks:
        raise HTTPException(409)
    if not force and valid_count == actual_count:
        doc.indexing_status, doc.indexing_error, doc.indexing_token = "indexed", None, None
        doc.indexed_model = info.space
        db.commit()
        return doc
    token = uuid.uuid4()
    doc.indexing_status, doc.indexing_error, doc.indexing_token = "indexing", None, token
    db.commit()
    return process_claim(db, user, workspace_id, document_id, token, provider, settings)


def process_claim(db, user, workspace_id, document_id, token, provider, settings):
    """Synchronous claim consumer; later workers must revalidate the actor before calling."""
    doc = scoped(db, workspace_id, document_id, lock=True)
    if doc.indexing_token != token or doc.processing_status != DocumentStatus.COMPLETED:
        raise HTTPException(409)
    start = time.monotonic()
    info = provider.get_model_info()
    try:
        with db.begin_nested():
            last = -1
            total = 0
            while True:
                if time.monotonic() - start > settings.indexing_timeout_seconds:
                    raise EmbeddingUnavailable("Indexing budget exceeded")
                chunks = db.scalars(
                    select(DocumentChunk)
                    .where(
                        DocumentChunk.workspace_id == workspace_id,
                        DocumentChunk.document_id == document_id,
                        DocumentChunk.chunk_index > last,
                    )
                    .order_by(DocumentChunk.chunk_index)
                    .limit(settings.embedding_batch_size)
                ).all()
                if not chunks:
                    break
                total += len(chunks)
                if total > settings.indexing_max_chunks:
                    raise ValueError("Too many chunks")
                vectors = validate_vectors(
                    provider.embed_documents([c.content for c in chunks]), len(chunks)
                )
                for chunk, vector in zip(chunks, vectors, strict=True):
                    statement = insert(E).values(
                        chunk_id=chunk.id,
                        workspace_id=workspace_id,
                        document_id=document_id,
                        model_space=info.space,
                        content_hash=fingerprint(chunk.content),
                        embedding=vector,
                    )
                    db.execute(
                        statement.on_conflict_do_update(
                            index_elements=[E.chunk_id],
                            set_={
                                "model_space": statement.excluded.model_space,
                                "content_hash": statement.excluded.content_hash,
                                "embedding": statement.excluded.embedding,
                                "updated_at": func.now(),
                            },
                        )
                    )
                last = chunks[-1].chunk_index
            if total == 0 or total != doc.total_chunks:
                raise ValueError("Chunk count changed")
            # Re-check current membership at publication, after potentially slow inference.
            access(db, user, workspace_id, Permission.DOCUMENT_UPLOAD, lock=True)
            if db.get(User, user.id, populate_existing=True).account_status.value != "active":
                raise HTTPException(403)
    except HTTPException:
        doc.indexing_status, doc.indexing_error, doc.indexing_token = (
            "failed",
            "access_changed",
            None,
        )
        db.commit()
        raise
    except EmbeddingUnavailable, ValueError:
        # Savepoint rolls back every partial vector replacement, retaining the previous index.
        doc.indexing_status, doc.indexing_error, doc.indexing_token = (
            "failed",
            "indexing_failed",
            None,
        )
    else:
        doc.indexing_status, doc.indexing_error, doc.indexing_token = "indexed", None, None
        doc.indexed_model = info.space
    db.commit()
    return doc


def retrieve(db: Session, workspace_id: uuid.UUID, vector, space: str, top_k: int, minimum: float):
    vector = validate_vectors([vector], 1)[0]
    distance = E.embedding.cosine_distance(vector)
    # All authorization scope, model compatibility, content freshness and ranking are in SQL.
    ranked = (
        select(
            Document.id.label("document_id"),
            Document.original_filename.label("document_name"),
            DocumentChunk.id.label("chunk_id"),
            DocumentChunk.content,
            DocumentChunk.chunk_index,
            DocumentChunk.page_number,
            DocumentChunk.source_metadata,
            (1 - distance).label("similarity_score"),
            func.row_number()
            .over(
                partition_by=E.content_hash,
                order_by=(distance, Document.id, DocumentChunk.chunk_index),
            )
            .label("duplicate_rank"),
        )
        .select_from(E)
        .join(
            DocumentChunk,
            and_(
                E.chunk_id == DocumentChunk.id,
                E.document_id == DocumentChunk.document_id,
                E.workspace_id == DocumentChunk.workspace_id,
            ),
        )
        .join(Document, and_(Document.id == E.document_id, Document.workspace_id == E.workspace_id))
        .where(
            E.workspace_id == workspace_id,
            DocumentChunk.workspace_id == workspace_id,
            Document.workspace_id == workspace_id,
            Document.processing_status == DocumentStatus.COMPLETED,
            E.model_space == space,
            E.content_hash == content_hash(),
            func.vector_norm(E.embedding).between(0.999, 1.001),
            distance <= 1 - minimum,
        )
        .subquery()
    )
    rows = (
        db.execute(
            select(ranked)
            .where(ranked.c.duplicate_rank == 1)
            .order_by(
                ranked.c.similarity_score.desc(),
                ranked.c.document_id,
                ranked.c.chunk_index,
            )
            .limit(top_k)
        )
        .mappings()
        .all()
    )
    return [{k: v for k, v in row.items() if k != "duplicate_rank"} for row in rows]


def search(db, user, workspace_id, request: SearchRequest, provider, settings):
    access(db, user, workspace_id, Permission.DOCUMENT_CONTENT)
    info = provider.get_model_info()
    vector = provider.embed_query(request.query)
    # Recheck role after inference and serialize the short retrieval with membership mutations.
    access(db, user, workspace_id, Permission.DOCUMENT_CONTENT, lock=True)
    minimum = (
        settings.search_min_similarity if request.min_similarity is None else request.min_similarity
    )
    return {
        "query": request.query,
        "model": info.model_dump(),
        "min_similarity": minimum,
        "results": retrieve(db, workspace_id, vector, info.space, request.top_k, minimum),
    }
