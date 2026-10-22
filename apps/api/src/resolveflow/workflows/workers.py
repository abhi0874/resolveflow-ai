"""Logical workers reusing existing services; all execution dependencies stay out of state."""

import time
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from langgraph.errors import GraphInterrupt
from langgraph.types import interrupt
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from resolveflow.ai.contracts import AIError, GeneratedResponse
from resolveflow.db.models import User
from resolveflow.db.session import DatabaseUnavailableError
from resolveflow.ml.contracts import ModelUnavailable, TicketText
from resolveflow.rag import service as rag
from resolveflow.rag.context import input_reason, select_context
from resolveflow.rag.models import DraftCitation, ResponseDraft
from resolveflow.rag.prompt import validate_response
from resolveflow.rag.schemas import GenerateInput
from resolveflow.retrieval.contracts import EmbeddingUnavailable, SearchRequest, fingerprint
from resolveflow.retrieval.service import search
from resolveflow.workflows.contracts import VERSION
from resolveflow.workflows.models import WorkflowExecution
from resolveflow.workflows.priority import recommend


def now():
    return datetime.now(UTC).isoformat()


def references(evidence):
    return [
        dict(
            document_id=str(e["document_id"]),
            chunk_id=str(e["chunk_id"]),
            content_hash=fingerprint(e["content"]),
            similarity_score=e["similarity_score"],
        )
        for e in evidence
    ]


def load_evidence(db, workspace_id, refs):
    items = []
    for ref in refs:
        source = rag.current_source(
            db, workspace_id, uuid.UUID(ref["document_id"]), uuid.UUID(ref["chunk_id"])
        )
        if source is None or fingerprint(source[0].content) != ref["content_hash"]:
            raise AIError("sources_changed")
        chunk, doc = source
        items.append(
            dict(
                document_id=doc.id,
                chunk_id=chunk.id,
                content=chunk.content,
                similarity_score=ref["similarity_score"],
            )
        )
    return items


class Workers:
    def __init__(self, db, user, execution, settings, classifier, embeddings, provider, guard=None):
        self.db, self.user, self.execution = db, user, execution
        self.settings, self.classifier, self.embeddings, self.provider = (
            settings,
            classifier,
            embeddings,
            provider,
        )
        self.guard = guard
        self.deadline = time.monotonic() + settings.workflow_timeout_seconds

    def check_continue(self):
        if self.guard:
            self.guard()
        if self.db.scalar(
            select(WorkflowExecution.cancel_requested).where(
                WorkflowExecution.id == self.execution.id
            )
        ):
            raise AIError("workflow_cancelled")

    def ticket(self, *, current=True):
        self.check_continue()
        e = self.execution
        ticket = rag.authorize(self.db, self.user, e.workspace_id, e.ticket_id, write=True)
        if current and ticket.version != e.ticket_version:
            raise AIError("ticket_changed")
        return ticket

    def wrap(self, name, operation):
        def node(state):
            started = time.monotonic()
            try:
                if state["workflow_version"] != VERSION or (
                    state["execution_id"],
                    state["workspace_id"],
                    state["ticket_id"],
                ) != (
                    str(self.execution.id),
                    str(self.execution.workspace_id),
                    str(self.execution.ticket_id),
                ):
                    raise AIError("workflow_state_invalid")
                if started > self.deadline:
                    raise AIError("workflow_timeout")
                self.ticket(current=name != "approval")
                self.execution.current_stage = name
                self.db.commit()
                updates = operation(state)
                self.check_continue()
                completed = list(dict.fromkeys([*state.get("completed_stages", []), name]))
                updates.update(
                    current_stage=name,
                    completed_stages=completed,
                    updated_at=now(),
                    timings_ms={
                        **state.get("timings_ms", {}),
                        name: (time.monotonic() - started) * 1000,
                    },
                )
            except GraphInterrupt:
                # LangGraph owns this control-flow exception; it must persist the pause.
                raise
            except Exception as exc:
                self.db.rollback()
                if not self.settings.workflow_inline_tests and isinstance(
                    exc, (SQLAlchemyError, DatabaseUnavailableError, EmbeddingUnavailable)
                ):
                    raise
                code = "workflow_worker_failed"
                if isinstance(exc, AIError):
                    code = exc.code
                elif isinstance(exc, EmbeddingUnavailable):
                    code = "embedding_unavailable"
                elif isinstance(exc, HTTPException):
                    code = (
                        "authorization_changed"
                        if exc.status_code in {401, 403, 404}
                        else "workflow_conflict"
                    )
                updates = dict(
                    status="cancelled" if code == "workflow_cancelled" else "failed",
                    current_stage=name,
                    error={"code": code, "stage": name},
                    updated_at=now(),
                    finished_at=now(),
                )
            # Publish progress without creating duplicate append-only events.
            merged = {**state, **updates}
            self.execution.state = merged
            self.execution.status = merged["status"]
            self.execution.current_stage = name
            if merged.get("finished_at"):
                self.execution.finished_at = datetime.fromisoformat(merged["finished_at"])
            self.db.commit()
            return updates

        return node

    def classification(self, state):
        ticket = self.ticket()
        text = TicketText(title=ticket.title, description=ticket.description or "")
        self.db.commit()
        try:
            value = self.classifier.predict(text).model_dump(mode="json")
        except ModelUnavailable:
            value = {"unavailable": True}
        return {"classification": value}

    def priority(self, state):
        ticket = self.ticket()
        return {
            "priority": recommend(
                ticket.title, ticket.description or "", ticket.priority.value
            ).model_dump()
        }

    def retrieval(self, state):
        ticket = self.ticket()
        reason = input_reason(ticket.title, ticket.description or "")
        query = (ticket.title + "\n" + (ticket.description or ""))[:1000]
        self.db.commit()
        rows = (
            []
            if reason
            else search(
                self.db,
                self.user,
                self.execution.workspace_id,
                SearchRequest(query=query, top_k=self.settings.ai_top_k),
                self.embeddings,
                self.settings,
            )["results"]
        )
        return {"evidence": references(rows)}

    def context(self, state):
        ticket = self.ticket()
        reason = input_reason(ticket.title, ticket.description or "")
        evidence = load_evidence(self.db, self.execution.workspace_id, state.get("evidence", []))
        selected, missing = select_context(evidence, self.settings)
        if reason:
            selected = []
        return {
            "evidence": references(selected),
            "context_summary": {
                "passages": len(selected),
                "characters": sum(len(e["content"]) for e in selected),
                "abstention_required": bool(reason or missing),
                "reason": reason or missing,
            },
        }

    def generation(self, state):
        e = self.execution
        # Stable execution UUID and original requester survive recovery by a different actor.
        original = self.db.get(User, e.requested_by)
        existing = self.db.scalar(
            select(ResponseDraft).where(
                ResponseDraft.workspace_id == e.workspace_id,
                ResponseDraft.requested_by == e.requested_by,
                ResponseDraft.request_id == e.id,
                ResponseDraft.ticket_id == e.ticket_id,
            )
        )
        if existing:
            # An ambiguous interrupted reservation is NEVER retried, even after the worker died.
            if existing.generation_status != "completed":
                raise AIError(existing.error_code or "generation_interrupted")
            result = rag.representation(self.db, existing, self.ticket())
        else:
            result = rag.generate(
                self.db,
                original,
                e.workspace_id,
                e.ticket_id,
                GenerateInput(
                    request_id=e.id,
                    expected_ticket_version=e.ticket_version,
                    synthetic_confirmed=e.synthetic_confirmed,
                ),
                self.provider,
                self.embeddings,
                self.settings,
                check_continue=self.check_continue,
                prepared_evidence=load_evidence(self.db, e.workspace_id, state.get("evidence", [])),
            )
        if result.generation_status != "completed":
            raise AIError(result.error_code or "generation_failed")
        return {"draft_id": str(result.id)}

    def verified_draft(self, state):
        ticket = self.ticket()
        draft = rag.scoped_draft(
            self.db,
            self.execution.workspace_id,
            self.execution.ticket_id,
            uuid.UUID(state["draft_id"]),
        )
        result = rag.representation(self.db, draft, ticket)
        if not result.sources_current or not result.ticket_current:
            raise AIError("sources_changed")
        if result.generation_status != "completed":
            raise AIError("invalid_output")
        if not result.insufficient_evidence:
            saved = self.db.scalars(
                select(DraftCitation)
                .where(
                    DraftCitation.workspace_id == self.execution.workspace_id,
                    DraftCitation.draft_id == draft.id,
                )
                .order_by(DraftCitation.position)
            ).all()
            if len(saved) != len(result.citations) or any(s.statement_text is None for s in saved):
                raise AIError("invalid_output")
            output = GeneratedResponse(
                response_text=result.response_text,
                statements=[
                    dict(
                        text=cite.statement_text,
                        chunk_id=str(cite.chunk_id),
                        supporting_quote=cite.supporting_quote,
                    )
                    for cite in saved
                ],
                requires_human_review=True,
                insufficient_evidence=False,
                uncertainty_notes="",
                suggested_next_steps=[],
            )
            validate_response(
                output, load_evidence(self.db, self.execution.workspace_id, draft.evidence_manifest)
            )
        return result

    def verification(self, state):
        result = self.verified_draft(state)
        return {
            "verification": {
                "passed": True,
                "abstained": result.insufficient_evidence,
                "citations": len(result.citations),
                "requires_human_review": True,
                "proves_factual_groundedness": False,
            },
            "approval_status": "pending_review",
        }

    def approval(self, state):
        # Always the same interrupt position on replay. The resume payload is not a decision.
        self.db.commit()
        interrupt({"draft_id": state["draft_id"], "requires_human_review": True})
        ticket = self.ticket(current=False)
        draft = rag.scoped_draft(
            self.db,
            self.execution.workspace_id,
            self.execution.ticket_id,
            uuid.UUID(state["draft_id"]),
        )
        result = rag.representation(self.db, draft, ticket)
        review = result.review
        if (
            review is None
            or review.decision != result.review_status
            or (
                review.draft_version != 1
                or review.response_hash != fingerprint(result.response_text or "")
            )
        ):
            raise AIError("approval_invalid")
        if result.review_status == "approved":
            if not result.approval_current:
                raise AIError("approval_stale")
            self.verified_draft(state)
        return {
            "approval_status": result.review_status,
            "status": ("completed" if result.review_status == "approved" else result.review_status),
            "finished_at": now(),
        }
