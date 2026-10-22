"""Real SDK serialization/parsing with mocked transport; no live credentials or requests."""

import importlib.util
import json
import sys
import warnings
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError
from test_ai_provider import EVIDENCE, output, settings

from resolveflow.ai.contracts import AIError
from resolveflow.ai.providers import GeminiProvider
from resolveflow.rag.prompt import build_prompt

PRIVATE = "private-sensitive-sentinel"


def response_body(raw=None, finish="STOP", *, parts=None, usage=True):
    body = {
        "candidates": [
            {
                "finishReason": finish,
                "content": {"parts": parts if parts is not None else [{"text": raw}]},
            }
        ],
    }
    if usage:
        body["usageMetadata"] = {
            "promptTokenCount": 100,
            "candidatesTokenCount": 12,
            "thoughtsTokenCount": 500,
        }
    return body


def mock_transport(monkeypatch, body):
    calls = []

    def send(client, request, **kwargs):
        calls.append(request)
        return httpx.Response(200, request=request, json=body)

    monkeypatch.setattr(httpx.Client, "send", send)
    return calls


@pytest.mark.parametrize(
    "raw,stage,json_ok,schema_ok,category",
    [
        ('{"response_text":', "json", False, None, "invalid_json"),
        (PRIVATE, "json", False, None, "invalid_json"),
        ("", "text", None, None, "empty_text"),
        (None, "text", None, None, "empty_text"),
        ("x" * 24001, "text", None, None, "oversized_text"),
        ("{}", "schema", True, False, "missing_field"),
        (
            json.dumps({**output().model_dump(), PRIVATE: PRIVATE}),
            "schema",
            True,
            False,
            "unexpected_field",
        ),
        (
            output(requires_human_review=True)
            .model_dump_json()
            .replace('"requires_human_review":true', '"requires_human_review":false'),
            "schema",
            True,
            False,
            "invalid_literal",
        ),
        (
            json.dumps({**output().model_dump(), "response_text": 123}),
            "schema",
            True,
            False,
            "invalid_type",
        ),
        (
            json.dumps({**output().model_dump(), "response_text": ""}),
            "schema",
            True,
            False,
            "length_limit",
        ),
    ],
)
def test_rejection_diagnostics(monkeypatch, caplog, raw, stage, json_ok, schema_ok, category):
    calls = mock_transport(monkeypatch, response_body(raw))
    with pytest.raises(AIError) as caught:
        GeminiProvider(settings()).generate_structured(build_prompt("Refund?", "", EVIDENCE, 512))
    error = caught.value
    assert error.code == "invalid_output" and str(error) == "invalid_output"
    diagnostic = error.diagnostics
    assert diagnostic.model == "gemini-3.6-flash"
    assert diagnostic.operation_status == "response_received"
    assert diagnostic.stage == stage
    assert diagnostic.finish_reason == "STOP"
    assert diagnostic.text_present is bool(raw)
    assert diagnostic.json_decoded is json_ok
    assert diagnostic.schema_validated is schema_ok
    assert diagnostic.validation_categories == (category,)
    assert (diagnostic.input_tokens, diagnostic.output_tokens, diagnostic.thinking_tokens) == (
        100,
        12,
        500,
    )
    assert PRIVATE not in diagnostic.model_dump_json() + str(error) + caplog.text
    assert len(calls) == 1


@pytest.mark.parametrize(
    "finish",
    [
        "MAX_TOKENS",
        "SAFETY",
        "RECITATION",
        "BLOCKLIST",
        "PROHIBITED_CONTENT",
        "SPII",
        "MALFORMED_FUNCTION_CALL",
        "UNEXPECTED_TOOL_CALL",
        "CONTINUATION",
        None,
        PRIVATE,
    ],
)
def test_finish_reasons_reject_even_valid_json(monkeypatch, finish):
    calls = mock_transport(monkeypatch, response_body(output().model_dump_json(), finish))
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        with pytest.raises(AIError) as caught:
            GeminiProvider(settings()).generate_structured(
                build_prompt("Refund?", "", EVIDENCE, 512)
            )
    diagnostic = caught.value.diagnostics
    assert diagnostic.stage == "finish"
    expected = "UNKNOWN" if finish == PRIVATE else finish or "MISSING"
    assert diagnostic.finish_reason == expected
    assert diagnostic.json_decoded and diagnostic.schema_validated
    assert diagnostic.validation_categories == ("non_success_finish",)
    assert PRIVATE not in diagnostic.model_dump_json()
    assert all(PRIVATE not in str(w.message) for w in recorded)
    assert len(calls) == 1


@pytest.mark.parametrize("raw", ['{"response_text":', None])
def test_truncation_retains_thinking_usage(monkeypatch, raw):
    mock_transport(monkeypatch, response_body(raw, "MAX_TOKENS"))
    with pytest.raises(AIError) as caught:
        GeminiProvider(settings()).generate_structured(build_prompt("Refund?", "", EVIDENCE, 512))
    diagnostic = caught.value.diagnostics
    assert diagnostic.stage == "finish"
    assert diagnostic.finish_reason == "MAX_TOKENS"
    assert diagnostic.thinking_tokens == 500
    assert diagnostic.json_decoded is (False if raw else None)
    assert set(diagnostic.validation_categories) == {
        "non_success_finish",
        "invalid_json" if raw else "empty_text",
    }


def test_no_candidates(monkeypatch):
    mock_transport(monkeypatch, {"promptFeedback": {"blockReason": "SAFETY"}})
    with pytest.raises(AIError) as caught:
        GeminiProvider(settings()).generate_structured(build_prompt("Refund?", "", EVIDENCE, 512))
    diagnostic = caught.value.diagnostics
    assert diagnostic.finish_reason == "MISSING"
    assert diagnostic.validation_categories == ("empty_text", "no_candidate")
    assert diagnostic.input_tokens is diagnostic.thinking_tokens is None
    assert diagnostic.json_decoded is diagnostic.schema_validated is None


def test_thought_only_is_not_response_text(monkeypatch):
    mock_transport(monkeypatch, response_body(parts=[{"text": PRIVATE, "thought": True}]))
    with pytest.raises(AIError) as caught:
        GeminiProvider(settings()).generate_structured(build_prompt("Refund?", "", EVIDENCE, 512))
    assert caught.value.diagnostics.text_present is False
    assert caught.value.diagnostics.validation_categories == ("empty_text",)


@pytest.mark.parametrize("level", ["minimal", "low", "medium", "high", "default"])
def test_valid_split_text_thought_exclusion_and_thinking_configuration(monkeypatch, level):
    raw = output().model_dump_json()
    calls = mock_transport(
        monkeypatch,
        response_body(
            parts=[
                {"text": PRIVATE, "thought": True},
                {"text": raw[:20]},
                {"text": raw[20:]},
            ],
            usage=False,
        ),
    )
    monkeypatch.setenv("RESOLVEFLOW_GEMINI_THINKING_LEVEL", level)
    result = GeminiProvider(settings()).generate_structured(
        build_prompt("Refund?", "", EVIDENCE, 1024)
    )
    assert result.output == output()
    assert result.diagnostics.stage == "complete"
    assert result.diagnostics.json_decoded and result.diagnostics.schema_validated
    assert result.diagnostics.thinking_tokens is None
    assert result.diagnostics.validation_categories == ()
    assert PRIVATE not in result.model_dump_json()
    config = json.loads(calls[0].content)["generationConfig"]
    assert config["maxOutputTokens"] == 1024
    if level == "default":
        assert "thinkingConfig" not in config
    else:
        assert config["thinkingConfig"] == {
            "thinking_level": level.upper(),
            "include_thoughts": False,
        }
    assert len(calls) == 1


def test_settings_bounds():
    for overrides in [
        {"ai_max_output_tokens": 2049},
        {"ai_max_retries": 1},
        {"ai_max_calls": 2},
        {"gemini_thinking_level": "unbounded"},
    ]:
        with pytest.raises(ValidationError):
            settings(**overrides)


@pytest.fixture
def smoke(monkeypatch):
    path = Path(__file__).resolve().parents[1] / "scripts" / "gemini_smoke.py"
    spec = importlib.util.spec_from_file_location("gemini_smoke", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "Settings", lambda: settings(ai_max_output_tokens=1024))
    monkeypatch.setattr(sys, "argv", ["gemini_smoke.py", "--allow-live-synthetic"])
    return module


@pytest.mark.parametrize(
    "scenario",
    ["valid", "invalid_citation", "mismatch", "no_statements", "truncated", "unsupported_claim"],
)
def test_smoke_safe_diagnostics_at_provider_and_grounding_stages(
    monkeypatch, capsys, caplog, smoke, scenario
):
    calls = []

    def send(client, request, **kwargs):
        calls.append(request)
        payload = json.loads(request.content)
        assert payload["generationConfig"]["maxOutputTokens"] == 1024
        # The only data sent by the script is its built-in synthetic policy and question.
        content = json.loads(payload["contents"][0]["parts"][0]["text"])
        evidence = content["RETRIEVED_EVIDENCE"][0]
        text = evidence["text"]
        data = output(
            response_text=text,
            statements=[{"text": text, "chunk_id": evidence["chunk_id"], "supporting_quote": text}],
        ).model_dump()
        if scenario == "invalid_citation":
            data["statements"][0]["chunk_id"] = "00000000-0000-0000-0000-000000000000"
        if scenario == "mismatch":
            data["response_text"] = PRIVATE
        if scenario == "no_statements":
            data["statements"] = []
        if scenario == "unsupported_claim":
            data["response_text"] = data["statements"][0]["text"] = "We have processed your refund."
        body = response_body(
            '{"response_text":' if scenario == "truncated" else json.dumps(data),
            "MAX_TOKENS" if scenario == "truncated" else "STOP",
        )
        return httpx.Response(200, request=request, json=body)

    monkeypatch.setattr(httpx.Client, "send", send)
    assert smoke.main() == (0 if scenario == "valid" else 1)
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["provider"]["model"] == "gemini-3.6-flash"
    assert report["thinking_level"] == "minimal"
    assert report["customer_data_used"] is False
    assert report["diagnostics"]["thinking_tokens"] == 500
    if scenario == "valid":
        assert report["status"] == "passed" and report["citation_validation"] == "passed"
    elif scenario == "truncated":
        assert report["validation_stage"] == "provider"
        assert report["diagnostics"]["finish_reason"] == "MAX_TOKENS"
        assert report["diagnostics"]["json_decoded"] is False
    else:
        assert report["validation_stage"] == "grounding"
        assert report["diagnostics"]["schema_validated"] is True
        expected = (
            "response_statement_mismatch_or_missing"
            if scenario in {"mismatch", "no_statements"}
            else scenario
        )
        assert report["grounding_error_category"] == expected
    for secret in [
        PRIVATE,
        "synthetic-sdk-key",
        "Synthetic demonstration policy:",
        "x-goog-api-key",
    ]:
        assert secret not in captured.out + captured.err + caplog.text
    assert len(calls) == 1


@pytest.mark.parametrize("gate", ["flag", "live", "free_tier", "key"])
def test_smoke_disabled_gates_never_call(monkeypatch, capsys, smoke, gate):
    def forbidden(*args, **kwargs):
        pytest.fail("Disabled smoke must not reach the SDK transport")

    monkeypatch.setattr(httpx.Client, "send", forbidden)
    overrides = {
        "live": {"ai_live_enabled": False},
        "free_tier": {"ai_free_tier_verified": False},
        "key": {"GEMINI_API_KEY": None},
    }
    if gate == "flag":
        monkeypatch.setattr(sys, "argv", ["gemini_smoke.py"])
    else:
        monkeypatch.setattr(smoke, "Settings", lambda: settings(**overrides[gate]))
    assert smoke.main() == 2
    assert "Not run" in capsys.readouterr().out
