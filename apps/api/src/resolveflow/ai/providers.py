"""Explicit provider selection; fixture mode never substitutes for a failed live call."""

import json
import time
import warnings
from threading import BoundedSemaphore

from resolveflow.ai.contracts import (
    AIError,
    AIProvider,
    GeneratedResponse,
    GenerationDiagnostics,
    GenerationInput,
    GenerationResult,
    ProviderInfo,
)
from resolveflow.ai.gemini_response import parse_response
from resolveflow.core.config import Settings


class GeminiProvider:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._slots = BoundedSemaphore(settings.ai_concurrency)

    def get_model_info(self) -> ProviderInfo:
        return ProviderInfo(provider="gemini", model=self.settings.ai_model)

    def health_check(self) -> bool:
        # Configuration readiness only; never consume quota on a health check.
        return bool(
            self.settings.ai_live_enabled
            and self.settings.ai_free_tier_verified
            and self.settings.gemini_api_key
        )

    def close(self) -> None:
        # Each request owns and closes its client; no network resources survive a call.
        pass

    def generate_structured(self, request: GenerationInput) -> GenerationResult:
        diagnostics = GenerationDiagnostics(model=self.settings.ai_model)
        if not self.health_check():
            raise AIError("ai_not_configured", diagnostics=diagnostics)
        if not self._slots.acquire(False):
            raise AIError("ai_busy", 30, diagnostics=diagnostics)
        start = time.perf_counter()
        try:
            from google import genai
            from google.genai import types

            diagnostics = diagnostics.model_copy(
                update={"operation_status": "requesting", "stage": "request"}
            )
            # SDK retries are explicitly disabled: one generation = at most one outbound call.
            # A per-call client also avoids shared lazy-initialization races.
            with (
                warnings.catch_warnings(),
                genai.Client(
                    api_key=self.settings.gemini_api_key.get_secret_value(),
                    vertexai=False,
                    http_options=types.HttpOptions(
                        timeout=self.settings.ai_timeout_seconds * 1000,
                        retry_options=types.HttpRetryOptions(attempts=1),
                    ),
                ) as client,
            ):
                # SDK unknown-enum warnings interpolate arbitrary upstream values.
                # Diagnostics below normalize those values without exposing them.
                warnings.filterwarnings(
                    "ignore", category=UserWarning, module=r"google\.genai\._common"
                )
                response = client.models.generate_content(
                    model=self.settings.ai_model,
                    contents=request.content,
                    config=types.GenerateContentConfig(
                        system_instruction=request.system,
                        response_mime_type="application/json",
                        response_json_schema=GeneratedResponse.model_json_schema(),
                        max_output_tokens=request.max_output_tokens,
                        thinking_config=(
                            types.ThinkingConfig(
                                thinking_level=self.settings.gemini_thinking_level.upper(),
                                include_thoughts=False,
                            )
                            if self.settings.gemini_thinking_level != "default"
                            else None
                        ),
                        temperature=0,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(
                            disable=True
                        ),
                    ),
                )
            output, diagnostics = parse_response(response, diagnostics)
            return GenerationResult(
                output=output,
                input_tokens=diagnostics.input_tokens,
                output_tokens=diagnostics.output_tokens,
                duration_ms=(time.perf_counter() - start) * 1000,
                diagnostics=diagnostics,
            )
        except AIError:
            raise
        except Exception as exc:
            import httpx
            from google.genai import errors

            if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
                raise AIError(
                    "ai_timeout",
                    diagnostics=diagnostics.model_copy(update={"operation_status": "timeout"}),
                ) from None
            if isinstance(exc, errors.APIError):
                code = exc.code
                retry = None
                response = getattr(exc, "response", None)
                if response is not None:
                    raw = response.headers.get("retry-after", "")
                    if raw.isdigit():
                        retry = min(86400, max(1, int(raw)))
                mapping = {
                    400: "ai_request_rejected",
                    401: "ai_credentials_invalid",
                    403: "ai_credentials_invalid",
                    404: "ai_model_unavailable",
                    429: "ai_quota_exhausted",
                }
                raise AIError(
                    mapping.get(code, "ai_unavailable"),
                    retry,
                    diagnostics=diagnostics.model_copy(update={"operation_status": "api_error"}),
                ) from None
            raise AIError(
                "ai_unavailable",
                diagnostics=diagnostics.model_copy(update={"operation_status": "client_error"}),
            ) from None
        finally:
            self._slots.release()


class DeterministicMockProvider:
    """Labeled offline test fixture; extracts a source sentence, never pretends to be Gemini."""

    def get_model_info(self) -> ProviderInfo:
        return ProviderInfo(provider="fixture", model="deterministic-v1", fixture=True)

    def health_check(self) -> bool:
        return True

    def close(self) -> None:
        pass

    def generate_structured(self, request: GenerationInput) -> GenerationResult:
        start = time.perf_counter()
        evidence = json.loads(request.content)["RETRIEVED_EVIDENCE"]
        source = evidence[0]
        quote = (source["text"].split(". ")[0].rstrip(".") + ".")[:900]
        if quote not in source["text"]:
            quote = source["text"][:900]
        result = GeneratedResponse(
            response_text=quote,
            statements=[{"text": quote, "chunk_id": source["chunk_id"], "supporting_quote": quote}],
            requires_human_review=True,
            insufficient_evidence=False,
            uncertainty_notes="Deterministic test fixture, not Gemini inference.",
            suggested_next_steps=[],
        )
        return GenerationResult(output=result, duration_ms=(time.perf_counter() - start) * 1000)


def select_provider(settings: Settings) -> AIProvider:
    if settings.ai_provider == "fixture":
        if settings.environment != "test":
            raise ValueError("Fixture provider is test-only")
        return DeterministicMockProvider()
    return GeminiProvider(settings)
