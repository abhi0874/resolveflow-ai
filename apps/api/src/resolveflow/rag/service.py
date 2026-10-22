"""Bounded RAG orchestration. No delivery or customer-action capability exists here."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from resolveflow.ai.contracts import AIError, AIProvider, GenerationResult
from resolveflow.core.config import Settings
from resolveflow.db.models import AccountStatus, User
from resolveflow.documents.models import Document, DocumentChunk, DocumentStatus
from resolveflow.rag.context import input_reason, select_context
from resolveflow.rag.models import DraftCitation, DraftReview, ResponseDraft
from resolveflow.rag.prompt import (
    PROMPT_VERSION,
    abstention,
    build_prompt,
    validate_response,
)
from resolveflow.rag.schemas import DraftResponse, GenerateInput, ReviewInput
from resolveflow.retrieval.contracts import EmbeddingProvider, SearchRequest, fingerprint
from resolveflow.retrieval.service import search
from resolveflow.services.authorization import Permission, access
from resolveflow.services.tickets import require_editor, scoped_ticket


def authorize(
    db: Session, user: User, workspace_id: uuid.UUID, ticket_id: uuid.UUID, *, write=False
):
    db.refresh(user)
    if user.account_status != AccountStatus.ACTIVE:
        raise HTTPException(401)
    access(db, user, workspace_id, Permission.DOCUMENT_CONTENT, lock=True)
    ticket = scoped_ticket(db, workspace_id, ticket_id)
    db.refresh(ticket)
    if write:
        _, member = access(db, user, workspace_id, Permission.TICKET_WRITE)
        require_editor(ticket, member)
    return ticket


def scoped_draft(db, workspace_id, ticket_id, draft_id):
    draft = db.scalar(
        select(ResponseDraft)
        .where(
            ResponseDraft.workspace_id == workspace_id,
            ResponseDraft.ticket_id == ticket_id,
            ResponseDraft.id == draft_id,
        )
        .execution_options(populate_existing=True)
    )
    if draft is None:
        raise HTTPException(404)
    return draft


def current_source(db, workspace_id, document_id, chunk_id):
    return db.execute(
        select(DocumentChunk, Document)
        .join(
            Document,
            (Document.id == DocumentChunk.document_id)
            & (Document.workspace_id == DocumentChunk.workspace_id),
        )
        .where(
            DocumentChunk.workspace_id == workspace_id,
            DocumentChunk.id == chunk_id,
            DocumentChunk.document_id == document_id,
            Document.processing_status == DocumentStatus.COMPLETED,
        )
        .execution_options(populate_existing=True)
    ).first()


def representation(db, draft, ticket) -> DraftResponse:
    citations = []
    saved = db.scalars(
        select(DraftCitation)
        .where(DraftCitation.workspace_id == draft.workspace_id, DraftCitation.draft_id == draft.id)
        .order_by(DraftCitation.position)
    ).all()
    valid = len(saved) == draft.citation_count
    for cite in saved:
        source = current_source(db, draft.workspace_id, cite.document_id, cite.chunk_id)
        if source is None or fingerprint(source[0].content) != cite.content_hash:
            valid = False
            continue
        chunk, doc = source
        citations.append(
            dict(
                document_id=doc.id,
                chunk_id=chunk.id,
                document_name=doc.original_filename,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                supporting_quote=cite.supporting_quote,
                similarity_score=cite.similarity_score,
            )
        )
    current = ticket.version == draft.ticket_version
    eligible = (
        valid
        and current
        and not draft.insufficient_evidence
        and draft.generation_status == "completed"
        and bool(citations)
    )
    values = {
        name: getattr(draft, name) for name in DraftResponse.model_fields if hasattr(draft, name)
    }
    return DraftResponse(
        **values,
        citations=citations,
        sources_current=valid,
        ticket_current=current,
        can_approve=eligible and draft.review_status == "pending_review",
        approval_current=eligible and draft.review_status == "approved",
        review=db.scalar(
            select(DraftReview).where(
                DraftReview.workspace_id == draft.workspace_id, DraftReview.draft_id == draft.id
            )
        ),
    )


def reserve(db, user, workspace_id, ticket, body, provider, settings):
    # Global DB lock makes budgets and in-flight reservations atomic across API processes.
    # Always acquire workspace before this short-lived global lock.
    db.execute(text("SELECT pg_advisory_xact_lock(726374091)"))
    cutoff = datetime.now(UTC) - timedelta(seconds=120)
    db.execute(
        update(ResponseDraft)
        .where(ResponseDraft.generation_status == "generating", ResponseDraft.created_at < cutoff)
        .values(generation_status="failed", error_code="generation_interrupted")
    )
    existing = db.scalar(
        select(ResponseDraft).where(
            ResponseDraft.workspace_id == workspace_id,
            ResponseDraft.requested_by == user.id,
            ResponseDraft.request_id == body.request_id,
        )
    )
    if existing:
        if (
            existing.ticket_id != ticket.id
            or existing.ticket_version != body.expected_ticket_version
        ):
            raise HTTPException(409)
        db.commit()
        return existing, False
    if ticket.version != body.expected_ticket_version:
        raise HTTPException(409)
    if len(ticket.title) + len(ticket.description or "") > settings.ai_ticket_chars:
        raise AIError("ticket_too_long")
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    count = select(func.count()).select_from(ResponseDraft).where(ResponseDraft.created_at >= today)
    for query, limit in (
        (count, settings.ai_daily_global),
        (count.where(ResponseDraft.workspace_id == workspace_id), settings.ai_daily_workspace),
        (count.where(ResponseDraft.requested_by == user.id), settings.ai_daily_user),
    ):
        if db.scalar(query) >= limit:
            raise AIError("ai_daily_budget", 86400)
    active = db.scalar(
        select(func.count())
        .select_from(ResponseDraft)
        .where(ResponseDraft.generation_status == "generating")
    )
    if active >= settings.ai_concurrency:
        raise AIError("ai_busy", 30)
    info = provider.get_model_info()
    draft = ResponseDraft(
        workspace_id=workspace_id,
        ticket_id=ticket.id,
        requested_by=user.id,
        request_id=body.request_id,
        ticket_version=ticket.version,
        provider=info.provider,
        model=info.model,
        fixture=info.fixture,
        prompt_version=PROMPT_VERSION,
    )
    db.add(draft)
    db.commit()
    return draft, True


def generate(
    db: Session,
    user: User,
    workspace_id: uuid.UUID,
    ticket_id: uuid.UUID,
    body: GenerateInput,
    provider: AIProvider,
    embeddings: EmbeddingProvider,
    settings: Settings,
    *,
    prepared_evidence: list[dict] | None = None,
    check_continue=None,
) -> DraftResponse:
    ticket = authorize(db, user, workspace_id, ticket_id, write=True)
    draft, fresh = reserve(db, user, workspace_id, ticket, body, provider, settings)
    if not fresh:
        # Failure and interrupted states are durable; replay never creates another provider call.
        return representation(db, draft, ticket)
    draft_id = draft.id
    try:
        ticket = authorize(db, user, workspace_id, ticket_id, write=True)
        if ticket.version != body.expected_ticket_version:
            raise AIError("ticket_changed")
        title, description = ticket.title, ticket.description or ""
        db.commit()  # Do not hold a workspace lock while embedding the query.
        reason = input_reason(title, description)
        evidence = []
        if not reason:
            results = prepared_evidence
            if results is None:
                results = search(
                    db,
                    user,
                    workspace_id,
                    SearchRequest(
                        query=(title + "\n" + description)[:1000], top_k=settings.ai_top_k
                    ),
                    embeddings,
                    settings,
                )["results"]
            evidence, reason = select_context(results, settings)
        ticket = authorize(db, user, workspace_id, ticket_id, write=True)
        if ticket.version != body.expected_ticket_version:
            raise AIError("ticket_changed")
        check_evidence(db, workspace_id, evidence)
        draft = scoped_draft(db, workspace_id, ticket_id, draft_id)
        draft.evidence_manifest = [
            dict(
                document_id=str(e["document_id"]),
                chunk_id=str(e["chunk_id"]),
                content_hash=fingerprint(e["content"]),
                similarity_score=e["similarity_score"],
            )
            for e in evidence
        ]
        if reason:
            result = GenerationResult(output=abstention(reason), duration_ms=0)
            draft.generation_origin = "local_abstention"
            db.commit()
        else:
            if not provider.health_check():
                raise AIError("ai_not_configured")
            if not provider.get_model_info().fixture and (
                workspace_id not in settings.ai_synthetic_workspaces or not body.synthetic_confirmed
            ):
                raise AIError("synthetic_only")
            prompt = build_prompt(title, description, evidence, settings.ai_max_output_tokens)
            db.commit()  # Release DB locks/connections before the network call.
            if check_continue:
                check_continue()
            result = provider.generate_structured(prompt)
        output = result.output if reason else validate_response(result.output, evidence)
        db.expire_all()
        ticket = authorize(db, user, workspace_id, ticket_id, write=True)
        if ticket.version != body.expected_ticket_version:
            raise AIError("ticket_changed")
        check_evidence(db, workspace_id, evidence)
        draft = scoped_draft(db, workspace_id, ticket_id, draft_id)
        if draft.generation_status != "generating":
            raise AIError("generation_interrupted")
        if check_continue:
            check_continue()
        draft.response_text = output.response_text
        draft.insufficient_evidence = output.insufficient_evidence
        draft.uncertainty_notes = output.uncertainty_notes
        draft.suggested_next_steps = output.suggested_next_steps
        draft.input_tokens, draft.output_tokens = result.input_tokens, result.output_tokens
        draft.duration_ms = result.duration_ms
        draft.generation_status = "completed"
        draft.citation_count = len(output.statements)
        by_id = {str(e["chunk_id"]): e for e in evidence}
        for position, statement in enumerate(output.statements):
            item = by_id[statement.chunk_id]
            db.add(
                DraftCitation(
                    draft_id=draft.id,
                    position=position,
                    workspace_id=workspace_id,
                    document_id=item["document_id"],
                    chunk_id=item["chunk_id"],
                    content_hash=fingerprint(item["content"]),
                    supporting_quote=statement.supporting_quote,
                    statement_text=statement.text,
                    similarity_score=item["similarity_score"],
                )
            )
        db.commit()
        return representation(db, draft, ticket)
    except Exception as exc:
        db.rollback()
        # Persist only an allowlisted service code, never SDK errors, prompt or customer data.
        code = exc.code if isinstance(exc, AIError) else "generation_failed"
        db.execute(
            update(ResponseDraft)
            .where(
                ResponseDraft.id == draft_id,
                ResponseDraft.workspace_id == workspace_id,
                ResponseDraft.generation_status == "generating",
            )
            .values(generation_status="failed", error_code=code)
        )
        db.commit()
        if isinstance(exc, (AIError, HTTPException)):
            raise
        raise AIError("generation_failed") from None


def check_evidence(db, workspace_id, evidence):
    for item in evidence:
        source = current_source(db, workspace_id, item["document_id"], item["chunk_id"])
        if source is None or source[0].content != item["content"]:
            raise AIError("sources_changed")


def review(
    db: Session,
    user: User,
    workspace_id: uuid.UUID,
    ticket_id: uuid.UUID,
    draft_id: uuid.UUID,
    body: ReviewInput,
) -> DraftResponse:
    ticket = authorize(db, user, workspace_id, ticket_id, write=True)
    draft = scoped_draft(db, workspace_id, ticket_id, draft_id)
    if (
        draft.version != body.expected_version
        or draft.review_status != "pending_review"
        or draft.generation_status != "completed"
    ):
        raise HTTPException(409)
    if body.action == "approved" and not representation(db, draft, ticket).can_approve:
        raise HTTPException(409)
    db.add(
        DraftReview(
            workspace_id=workspace_id,
            draft_id=draft.id,
            actor_id=user.id,
            decision=body.action,
            draft_version=draft.version,
            response_hash=fingerprint(draft.response_text),
        )
    )
    draft.review_status = body.action
    draft.version += 1
    db.commit()
    return representation(db, draft, ticket)
