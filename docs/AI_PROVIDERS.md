# AI provider boundary

Step 9 implements a synchronous, provider-independent generation boundary in
`apps/api/src/resolveflow/ai/`. Step 10 reuses this boundary in a separate LangGraph
workflow package; provider SDK objects remain inside adapters. Neither path sends
customer messages.

`AIProvider` accepts `GenerationInput` and returns `GenerationResult`, both
Pydantic contracts. Its operations are `generate_structured`, `get_model_info`,
`health_check` and `close`. No Google SDK object crosses into RAG, ticket services,
database models, HTTP schemas or the frontend. Embeddings retain their separate
local `EmbeddingProvider`; changing generation never re-embeds documents.

| Adapter | Selection | Behavior |
| --- | --- | --- |
| `GeminiProvider` | `RESOLVEFLOW_AI_PROVIDER=gemini` (default) | Official `google-genai==2.31.0`, `models.generate_content`, configurable model, JSON schema, usage metadata and safe errors |
| `DeterministicMockProvider` | `fixture`, permitted only with `RESOLVEFLOW_ENVIRONMENT=test` | Extracts a bounded sentence from the first retrieved passage; explicit fixture metadata and UI badges; no network |

The fixture is never selected because Gemini fails or lacks credentials. It is
not an alternative development inference engine or an LLM-quality benchmark.
Browser tests explicitly select it in their isolated test environment.

The current Gemini default is `gemini-3.6-flash`; `RESOLVEFLOW_AI_MODEL` can
override it. The same SDK adapter passes that value directly to `generate_content`.
Mocked transport tests cover both 3.6 Flash and the previous 3.5 Flash-Lite model
identifier. No provider interface, RAG prompt, citation validator or review logic
needed a model-specific change. The first approved synthetic live check returned
`invalid_output`; its original diagnostic context was not retained. Successful
live structured generation and citation validation remain unverified.

`health_check` is configuration readiness only: no quota-consuming request or
claim of remote availability. A real call needs a server key, live enablement
and the operator's free-tier attestation. The RAG service additionally requires
an allowlisted synthetic workspace and per-request synthetic confirmation.

Each Gemini request owns and closes its official SDK client. SDK retry attempts
are set to one (the original request), automatic function calling is disabled,
and no tools, search, files, caching, fallback provider or model routing are used.
Timeouts, 400/401/403/404/429/5xx errors, malformed JSON, safety/truncation finish
reasons and schema failures become safe service codes. Numeric `Retry-After`
is preserved, bounded to 1–86,400 seconds. No automatic retry occurs.

The Gemini adapter explicitly configures minimal thinking for the current model,
via `RESOLVEFLOW_GEMINI_THINKING_LEVEL`. Supported alternatives are low, medium,
high, or default (omit thinking configuration for a future model). This setting
and SDK response normalization stay inside the adapter/configuration boundary.
The smoke script uses the existing configurable application token cap (1,024
default, 2,048 maximum). There is no automatic cap escalation or model fallback.

Optional `GenerationDiagnostics` on results and `AIError` retain content-free
operation/validation stages, normalized finish reasons, token usage including
thinking, text presence, JSON/schema outcomes and allowlisted error categories.
Unknown enum values are never echoed. Error messages, validation locations/inputs,
raw responses, prompts and hidden thoughts are excluded. Existing providers may
omit this metadata; the protocol signatures remain unchanged. RAG services and
public HTTP error schemas do not expose it. The smoke script preserves successful
provider diagnostics when subsequent grounding validation fails, distinguishing
that failure from malformed provider output. See GEMINI_INTEGRATION.md for the
investigation, uncertainty and approval-gated next test.

To add a future provider:

1. Implement the protocol behind a separate adapter and register an explicit
   configuration option. Review model identifiers and supported JSON schema.
2. Normalize usage, errors, finish reasons, timeout/retry behavior and lifecycle.
   Providers need not have identical schema support or token accounting.
3. Add offline transport/contract tests, preserving the common output schema
   and all citation, authorization and review checks.
4. Re-evaluate the synthetic corpus and obtain separate permission for any new
   external service. Verify its free tier and data terms before enabling it.

No Groq, OpenRouter, Ollama or other nonfunctional adapters were added. Existing
RAG services depend on the protocol, not on `GeminiProvider`. Ticket management,
retrieval, persistence and review remain independent of a provider SDK.
