import { ApiError } from "./session-api";
import { ticketError } from "./tickets";

export type DraftConfig = {
  provider: string; model: string; fixture: boolean; available: boolean;
  synthetic_confirmation_required: boolean; max_ticket_chars: number;
};
export type Draft = {
  id: string; ticket_id: string; ticket_version: number; version: number;
  generation_status: "generating" | "completed" | "failed";
  review_status: "pending_review" | "approved" | "rejected" | "needs_revision";
  provider: string; model: string; fixture: boolean; prompt_version: string;
  generation_origin: string; response_text: string | null; insufficient_evidence: boolean;
  uncertainty_notes: string | null; suggested_next_steps: string[]; error_code: string | null;
  created_at: string; duration_ms: number | null; input_tokens: number | null; output_tokens: number | null;
  sources_current: boolean; ticket_current: boolean; can_approve: boolean; approval_current: boolean;
  citations: { document_id: string; chunk_id: string; document_name: string; chunk_index: number;
    page_number: number | null; supporting_quote: string; similarity_score: number }[];
  review: { actor_id: string; decision: string; created_at: string; draft_version: number; response_hash: string } | null;
};
export const draftStates = {
  pending_review: "Needs human review", approved: "Approved internally",
  rejected: "Rejected", needs_revision: "Revision requested",
};
const messages: Record<string, string> = {
  ai_not_configured: "Gemini is not enabled for this environment. Ask the developer to configure verified free-tier access.",
  synthetic_only: "Live generation is restricted to approved synthetic workspaces and confirmed synthetic tickets.",
  sensitive_input: "This request may contain sensitive data. Remove it before using the synthetic demo.",
  ticket_too_long: "This ticket exceeds the generation input limit. Shorten it before generating a draft.",
  ai_daily_budget: "The daily draft budget is exhausted. Try after the next UTC day begins.",
  ai_quota_exhausted: "Gemini’s quota is exhausted. Wait for the provider quota to reset; no automatic retry was made.",
  ai_busy: "Draft generation is busy. Wait briefly, then try again.",
  ai_timeout: "Generation timed out. Refresh draft history before starting another request.",
  ai_credentials_invalid: "Gemini credentials were rejected. Ask the developer to check the server configuration.",
  ai_model_unavailable: "The configured Gemini model is unavailable. No replacement model was used.",
  invalid_output: "The generator returned an invalid response. No draft was accepted.",
  invalid_citation: "The response cited unsupported evidence. No draft was accepted.",
  unsupported_claim: "The response failed claim checks. No draft was accepted.",
  sources_changed: "Source evidence changed during generation. Refresh and generate a new draft.",
  ticket_changed: "This ticket changed during generation. Refresh the ticket before trying again.",
  generation_interrupted: "This generation was interrupted. Start a new draft when ready.",
};
export function draftFailure(code: string | null) {
  return (code && messages[code]) || "Draft generation is unavailable. Check the service and refresh history before trying again.";
}
export function draftError(error: unknown) {
  if (error instanceof ApiError) {
    if (error.code && messages[error.code]) return messages[error.code];
    if (error.status === 409) return "The ticket, evidence or review changed. Refresh before reviewing this draft.";
    if (error.status === 503) return draftFailure(error.code ?? null);
  }
  return ticketError(error);
}
