"use client";
import Link from "next/link";
import { dateLabel } from "@/lib/tickets";
import { draftFailure, draftStates, type Draft } from "@/lib/drafts";

export function DraftCard({ draft, workspaceId, editable, pending, loading, review }: {
  draft: Draft; workspaceId: string; editable: boolean; pending: boolean; loading: boolean;
  review: (action: "approved" | "rejected" | "needs_revision") => Promise<void>;
}) {
  return <article className="draft-result" aria-label="Selected response draft">
      <div className="ticket-actions"><span className="role-badge">{draftStates[draft.review_status]}</span>
        {draft.fixture && <span className="role-badge">Test fixture</span>}
        {draft.generation_origin === "local_abstention" && <span className="role-badge">Local evidence check</span>}</div>
      {draft.generation_status === "failed" && <p role="alert" className="form-error">{draftFailure(draft.error_code)}</p>}
      {draft.generation_status === "generating" && <p role="status">This request is still in progress or was interrupted. Refresh history before retrying. Requests older than two minutes are recovered on the next generation request.</p>}
      {(!draft.sources_current || !draft.ticket_current) && <p className="form-error" role="status">This draft is stale: its ticket or source evidence changed. Any historical approval is no longer current. Generate a new draft.</p>}
      {draft.insufficient_evidence && draft.generation_status === "completed" && <p className="form-error">Insufficient evidence · human verification required. This draft cannot be approved.</p>}
      {draft.response_text && <p className="draft-text">{draft.response_text}</p>}
      {draft.uncertainty_notes && <p className="field-help">{draft.uncertainty_notes}</p>}
      {draft.citations.length > 0 && <div className="draft-sources"><h3>Supporting sources</h3>
        {draft.citations.map((cite, index) => <blockquote key={`${cite.chunk_id}-${index}`}>
          <p>{cite.supporting_quote}</p>
          <Link href={`/app/knowledge-base/${cite.document_id}?workspace=${workspaceId}`}>{cite.document_name} · {cite.page_number ? `Page ${cite.page_number} · ` : ""}Chunk {cite.chunk_index + 1}</Link>
        </blockquote>)}
      </div>}
      {!!draft.suggested_next_steps.length && <ul>{draft.suggested_next_steps.map((step, i) => <li key={i}>{step}</li>)}</ul>}
      <dl className="classification-metadata">
        <div><dt>Provider / model</dt><dd>{draft.provider} / {draft.model}</dd></div>
        <div><dt>Prompt version</dt><dd>{draft.prompt_version}</dd></div>
        <div><dt>Created</dt><dd>{dateLabel(draft.created_at)}</dd></div>
        <div><dt>Ticket revision</dt><dd>{draft.ticket_version}</dd></div>
        <div><dt>Generation time</dt><dd>{draft.duration_ms === null ? "Unavailable" : `${Math.round(draft.duration_ms)} ms`}</dd></div>
        <div><dt>Input / output tokens</dt><dd>{draft.input_tokens ?? "—"} / {draft.output_tokens ?? "—"}</dd></div>
      </dl>
      {draft.review && <p className="field-help">Review recorded {dateLabel(draft.review.created_at)} for draft revision {draft.review.draft_version}. {draft.approval_current ? "Approved internally. No customer action was taken." : draftStates[draft.review_status]}</p>}
      {editable && draft.generation_status === "completed" && draft.review_status === "pending_review" && <div className="ticket-actions">
        <button className="action-button" disabled={pending || loading || !draft.can_approve} onClick={() => void review("approved")}>Approve exact draft</button>
        <button className="subtle-button" disabled={pending || loading} onClick={() => void review("needs_revision")}>Request revision</button>
        <button className="subtle-button" disabled={pending || loading} onClick={() => void review("rejected")}>Reject draft</button>
      </div>}
    </article>;
}
