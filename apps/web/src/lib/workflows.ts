import { ApiError, errorMessage } from "./session-api";
import { draftFailure, type Draft } from "./drafts";

export const workflowStages = [
  ["classification", "Classification"],
  ["priority", "Priority"],
  ["retrieval", "Retrieval"],
  ["context", "Context preparation"],
  ["generation", "Response generation"],
  ["verification", "Verification"],
  ["approval", "Human approval"],
] as const;

export const workflowStatuses: Record<string, string> = {
  queued: "Queued", waiting_for_approval: "Awaiting human review", running: "Processing", paused: "Awaiting human review", completed: "Completed",
  rejected: "Rejected", needs_revision: "Revision requested", failed: "Failed", cancelled: "Stopped",
};

export type Workflow = {
  job: { id: string; kind: string; status: string; attempts: number; started_at: string | null;
    finished_at: string | null; next_attempt_at: string | null; error_code: string | null } | null;
  cancel_requested: boolean;
  id: string; status: string; current_stage: string; completed_stages: string[];
  workflow_version: string; created_at: string; updated_at: string; finished_at: string | null;
  classification: { suggested_category: string | null; uncertain: boolean; model_version: string } | null;
  classification_unavailable: boolean;
  priority: { suggested_priority: string; rule_ids: string[]; requires_review: true } | null;
  evidence: { document_id: string; chunk_id: string; document_name: string; chunk_index: number; similarity_score: number }[];
  context_summary: { passages?: number; characters?: number; abstention_required?: boolean; reason?: string };
  verification: { passed?: boolean; abstained?: boolean; citations?: number };
  approval_status: string; draft: Draft | null; error_code: string | null;
  failed_stage: string | null; timings_ms: Record<string, number>; attempts: number; can_resume: boolean;
};

export function workflowFailure(code: string | null): string {
  const messages: Record<string, string> = {
    broker_unavailable: "The queue is temporarily unavailable. Your saved request will be published when it recovers.",
    database_unavailable: "Storage was temporarily unavailable. A bounded retry is scheduled.",
    retrieval_unavailable: "The local search model could not run. Check the worker model installation.",
    worker_interrupted: "A worker was interrupted. Processing will recover from saved progress.",
    job_attempts_exhausted: "The retry limit was reached. Ask the developer to inspect this execution.",
    job_execution_failed: "The worker could not complete this execution safely.",
    embedding_unavailable: "The local search model is unavailable. Restore it before starting a new workflow.",
    authorization_changed: "Access changed while this workflow was processing. An authorized editor must review it.",
    workflow_timeout: "The workflow reached its processing time limit. No automatic retry was made.",
    workflow_worker_failed: "A workflow stage could not finish safely. Ask the developer to check the service.",
    approval_stale: "The ticket or evidence changed after review. A new draft and review are required.",
    approval_invalid: "The saved decision no longer matches this exact draft. Completion was blocked.",
    workflow_state_invalid: "This workflow state is incompatible. Ask the developer to inspect its version.",
    workflow_conflict: "The ticket or workflow changed while processing. Refresh its status.",
  };
  return (code && messages[code]) || draftFailure(code);
}

export function workflowError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 409) return "Review is still pending, another request is running, or this workflow cannot resume. Refresh its status.";
    if (error.status === 429) return "The workflow or generation limit has been reached. Wait before starting another request.";
    if (error.status === 503) return "Workflow storage or a required service is unavailable. Refresh history before recovering this execution.";
  }
  return errorMessage(error);
}

export function workflowLabel(run: Workflow): string {
  return workflowStatuses[run.job && ["queued", "running"].includes(run.job.status) ? run.job.status : run.status] ?? run.status;
}
