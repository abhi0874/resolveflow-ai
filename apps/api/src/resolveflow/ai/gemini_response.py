"""Gemini response normalization. Only allowlisted metadata leaves this adapter."""

from typing import TYPE_CHECKING

from pydantic import ValidationError

from resolveflow.ai.contracts import AIError, GeneratedResponse, GenerationDiagnostics

if TYPE_CHECKING:
    from google.genai.types import GenerateContentResponse


def parse_response(
    response: GenerateContentResponse, diagnostics: GenerationDiagnostics
) -> tuple[GeneratedResponse, GenerationDiagnostics]:
    from google.genai.types import FinishReason

    usage = response.usage_metadata
    candidate = response.candidates[0] if response.candidates else None
    reason = candidate.finish_reason.value if candidate and candidate.finish_reason else "MISSING"
    # Unknown SDK enum values may contain arbitrary upstream text. Never echo them.
    safe_reason = reason if reason in FinishReason.__members__ or reason == "MISSING" else "UNKNOWN"
    parts = candidate.content.parts if candidate and candidate.content else []
    # Same final-text semantics as SDK .text, without helper warnings or thought text.
    raw = "".join(part.text for part in (parts or []) if part.text and not part.thought)
    categories = []
    stage = "complete"
    if not candidate or reason != "STOP":
        stage = "finish"
        categories.append("no_candidate" if not candidate else "non_success_finish")
    output = None
    json_decoded = schema_validated = None
    if not raw or len(raw) > 24000:
        if stage == "complete":
            stage = "text"
        categories.append("empty_text" if not raw else "oversized_text")
    else:
        try:
            # Keep the exact validation model used to produce response_json_schema.
            output = GeneratedResponse.model_validate_json(raw)
            json_decoded = schema_validated = True
        except ValidationError as exc:
            # Do not retain inputs, locations (which can contain private keys), or messages.
            kinds = {
                error["type"]
                for error in exc.errors(
                    include_url=False, include_context=False, include_input=False
                )
            }
            json_decoded = "json_invalid" not in kinds
            schema_validated = False if json_decoded else None
            if stage == "complete":
                stage = "schema" if json_decoded else "json"
            mapping = {
                "json_invalid": "invalid_json",
                "missing": "missing_field",
                "extra_forbidden": "unexpected_field",
                "literal_error": "invalid_literal",
                "string_too_short": "length_limit",
                "string_too_long": "length_limit",
                "too_short": "length_limit",
                "too_long": "length_limit",
            }
            categories.extend(
                mapping.get(kind, "invalid_type" if kind.endswith("_type") else "schema_constraint")
                for kind in kinds
            )
    diagnostics = diagnostics.model_copy(
        update={
            "operation_status": "response_received",
            "stage": stage,
            "finish_reason": safe_reason,
            "input_tokens": usage.prompt_token_count if usage else None,
            "output_tokens": usage.candidates_token_count if usage else None,
            "thinking_tokens": usage.thoughts_token_count if usage else None,
            "text_present": bool(raw),
            "json_decoded": json_decoded,
            "schema_validated": schema_validated,
            "validation_categories": tuple(sorted(set(categories))),
        }
    )
    # Even valid JSON from an unsuccessful finish must never be accepted.
    if categories:
        raise AIError("invalid_output", diagnostics=diagnostics)
    assert output is not None
    return output, diagnostics
