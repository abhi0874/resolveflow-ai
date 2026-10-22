"""One opt-in synthetic generation; never loads customer or database records."""

import argparse
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from resolveflow.ai.contracts import AIError
from resolveflow.ai.providers import GeminiProvider
from resolveflow.core.config import Settings
from resolveflow.rag.prompt import build_prompt, validate_response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-live-synthetic", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    provider = GeminiProvider(settings)
    if not args.allow_live_synthetic or not provider.health_check():
        print(
            "Not run: requires explicit flag, server key, live enablement and verified free tier."
        )
        return 2
    evidence = [
        {
            "chunk_id": str(uuid.uuid4()),
            "content": (
                "Synthetic demonstration policy: a first purchase is refundable within 30 days."
            ),
        }
    ]
    result = None
    validation_stage = "provider"
    configuration = {
        "provider": provider.get_model_info().model_dump(),
        "max_output_tokens": settings.ai_max_output_tokens,
        "thinking_level": settings.gemini_thinking_level,
        "customer_data_used": False,
    }
    try:
        result = provider.generate_structured(
            build_prompt(
                "Synthetic refund eligibility",
                "What is the refund deadline for a first purchase?",
                evidence,
                settings.ai_max_output_tokens,
            )
        )
        validation_stage = "grounding"
        checked = validate_response(result.output, evidence)
        print(
            json.dumps(
                {
                    **configuration,
                    "status": "passed",
                    "calls": 1,
                    "citation_validation": "passed",
                    "insufficient_evidence": checked.insufficient_evidence,
                    "duration_ms": result.duration_ms,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "diagnostics": result.diagnostics.model_dump() if result.diagnostics else None,
                }
            )
        )
        return 0
    except AIError as exc:
        diagnostics = exc.diagnostics or (result.diagnostics if result else None)
        print(
            json.dumps(
                {
                    **configuration,
                    "status": "failed",
                    "code": exc.code,
                    "calls_at_most": 1,
                    "validation_stage": validation_stage,
                    "grounding_error_category": (
                        {
                            "invalid_output": "response_statement_mismatch_or_missing",
                            "invalid_citation": "invalid_citation",
                            "unsupported_claim": "unsupported_claim",
                        }.get(exc.code, "other")
                        if validation_stage == "grounding"
                        else None
                    ),
                    "diagnostics": diagnostics.model_dump() if diagnostics else None,
                }
            )
        )
        return 1
    finally:
        provider.close()


if __name__ == "__main__":
    raise SystemExit(main())
