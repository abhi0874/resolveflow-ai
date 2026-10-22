# Gemini integration

Updated 2026-10-20. The official Python SDK **google-genai 2.31.0** is pinned in
`apps/api/pyproject.toml` and `uv.lock`. The adapter uses
`client.models.generate_content`, separate system instructions, JSON-schema
output and Pydantic validation. The current default model is **gemini-3.6-flash**,
updated from Gemini 3.5 Flash-Lite at the user's request after Step 9.
It is configurable through `RESOLVEFLOW_AI_MODEL`; there is no silent fallback.

Google's [model reference](https://ai.google.dev/gemini-api/docs/models/gemini-3.6-flash)
lists this exact model and structured-output support. The
[pricing page](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.6-flash)
lists free standard input/output on the free tier. The adapter uses neither paid
grounding nor optional services. See the official
[Python SDK reference](https://googleapis.github.io/python-genai/),
[structured-output guide](https://ai.google.dev/gemini-api/docs/structured-output),
and [rate-limit guide](https://ai.google.dev/gemini-api/docs/rate-limits).
These references were checked for the model configuration update; they do not establish this
developer's account, region, project billing or quota eligibility.

## Current live-test status

**First approved live smoke failed output validation.** After manual key setup,
explicit approval and developer confirmation of the free tier, one synthetic
`gemini-3.6-flash` request was attempted with a 512-token output cap and no retries.
The script exited 1 with `invalid_output`; no response passed validation. This
safe error did not distinguish a non-STOP finish, absent/oversized text, invalid
JSON/schema, or a later response/statement consistency failure. Exact cause,
usage and latency were not captured on this failure path.

No automatic retry was made. Live/free-tier flags were enabled only for that
process; saved live inference remains disabled. Mocked SDK transport tests still
pass, but successful live structured generation/citation validation is unresolved.
A further live diagnostic call requires explicit approval. No customer data,
billing activation or external deployment was involved.

## Offline investigation and diagnostic fix

The verified defect was lost diagnostic context: the adapter rejected responses
before retaining usage/finish metadata, and the smoke script reported the same
`invalid_output` for provider parsing and later grounding validation. The exact
historical cause cannot be recovered from that one error code. No new live call
was made during this investigation.

The leading configuration hypothesis is output-budget exhaustion. Google's
[thinking guide](https://ai.google.dev/gemini-api/docs/thinking) lists medium as
3.6 Flash's default versus minimal for 3.5 Flash-Lite, and explains that thinking
can consume the generation cap. A 512-token cap with implicit thinking can
therefore leave incomplete or empty JSON. This is a plausible mechanism, not a
measurement of the failed call. Minimal thinking does not guarantee zero thinking
tokens or successful generation.

| Investigated possibility | Evidence and disposition |
| --- | --- |
| Truncation / thinking exhaustion | Plausible with 512 and changed defaults; mocked `MAX_TOKENS` with partial/absent JSON now retains usage, including thinking tokens. Original finish/usage unknown. |
| Incomplete or invalid JSON | Previously collapsed into `invalid_output`; now separately identified without logging JSON. |
| SDK structured-output incompatibility | Installed 2.31.0 and official SDK reference support `response_mime_type="application/json"` plus `response_json_schema`. Mocked wire schema exactly matches the validation model. No SDK upgrade or schema substitution needed. |
| Schema mismatch / missing fields | Schema derives directly from `GeneratedResponse`; required, literal, extra-field, type and length failures still reject and now report safe categories. Live output unknown. |
| Invalid citations | Existing validator raises `invalid_citation`, not the observed `invalid_output`. It remains strict and has smoke regression coverage. |
| Missing text / non-success finish | Separate diagnostic stages now identify these cases, retaining usage even on rejection. Non-success finishes reject even valid JSON. |
| Valid structured response handled incorrectly | Valid JSON, split text parts and thought exclusion pass mocked SDK tests. No such bug reproduced. |
| Post-schema response inconsistency | Missing statements or response text differing from joined statements also produce `invalid_output`. Smoke diagnostics now distinguish this from provider rejection. |

The adapter now explicitly requests `ThinkingConfig(thinking_level="MINIMAL",
include_thoughts=False)`, configurable with `RESOLVEFLOW_GEMINI_THINKING_LEVEL`
(`minimal`, `low`, `medium`, `high`, or `default` to omit this configuration when
switching models). Supported levels must be checked before selecting a different
model. The [generateContent API reference](https://ai.google.dev/api/generate-content#ThinkingConfig)
documents these fields. Pinned SDK serialization emits `thinkingConfig` with
snake_case inner fields; the [ProtoJSON specification](https://protobuf.dev/programming-guides/json/#format-description)
permits original proto names as well as camelCase. Transport tests assert the
installed SDK's actual serialization.

The smoke script now honors `RESOLVEFLOW_AI_MAX_OUTPUT_TOKENS`, using the existing
application default of 1,024 and maximum of 2,048, instead of a hardcoded 512.
This pairs explicit minimal reasoning with room for the structured answer and its
required repeated statement/quotation fields. It is a bounded mitigation for the
budget hypothesis, not a claim that a larger cap alone fixes the original failure.

Smoke success and failure reports include model/configuration, API operation
status, normalized finish reason, input/output/thinking token counts if reported,
text presence, JSON/schema results and allowlisted validation categories.
`null` means unavailable or not attempted, not zero or success. A
`response_received` operation status only means the SDK returned a response.
`validation_stage=grounding` means schema validation succeeded and a later
citation/claim/response-consistency check rejected it.

Unknown finish values are reported as `UNKNOWN`; SDK warnings that interpolate
unknown enum values are suppressed within the request. No raw output, thoughts,
validation inputs/messages/locations, credentials, headers, ticket or document
text are included. Diagnostics stay in optional provider-neutral result/error
metadata and the smoke report; public HTTP error responses and database records
are unchanged. Strict output, citation and human-review checks remain in force.

### Next single test, only after explicit approval

Recommended process configuration: `RESOLVEFLOW_AI_PROVIDER=gemini`,
`RESOLVEFLOW_AI_MODEL=gemini-3.6-flash`,
`RESOLVEFLOW_GEMINI_THINKING_LEVEL=minimal`,
`RESOLVEFLOW_AI_MAX_OUTPUT_TOKENS=1024`,
`RESOLVEFLOW_AI_TIMEOUT_SECONDS=25`, one call, zero retries, built-in synthetic
data only. After approval, enable live/free-tier flags for that process only;
keep the saved `.env` flags false. The developer has confirmed the free tier;
reconfirm the same AI Studio project remains free before the next call.
If it fails, inspect metadata and stop; never automatically retry, continue a
truncated response, increase the cap, or switch models. This approval gate remains
independent of workflow development. The single approved test passed on 2026-10-20
(see PROJECT_STATUS.md); Step 10 added no further live calls.

## Local setup and explicit enablement

Normal startup, retrieval and tests need no Gemini key. Install locked packages
and apply the additive schema migration from `apps/api`:

```bash
export UV_CACHE_DIR=../../.cache/uv
uv sync --locked
uv run python scripts/local_db.py start
uv run alembic upgrade head
```

For a separately authorized synthetic live check, the developer must first
confirm the selected project is actually on the free tier, verify current model
availability/quotas in AI Studio, and review the provider's data terms. A boolean
setting cannot verify or change Google's billing configuration.

Configure `GEMINI_API_KEY` privately in the server process or ignored
`apps/api/.env`, never in web files, source control, chat or a `NEXT_PUBLIC_*`
variable. The exact existing local file is:

`/Users/abhisheshramadasshet/Documents/ChatGPT/ResolveFlow AI/apps/api/.env`

It is Git-ignored and restricted to the file owner (`0600`). Open it in a local
text editor, find `GEMINI_API_KEY=`, paste the key after the equals sign, and save.
Do not paste it into chat, a terminal command (shell history), the web environment,
or `.env.example`. Preserve the existing database settings and any existing key.
The application uses the `RESOLVEFLOW_` prefix: use `RESOLVEFLOW_AI_PROVIDER`,
not an unprefixed `AI_PROVIDER` variable.

Keep this configuration while waiting for explicit live-test approval:

```dotenv
GEMINI_API_KEY=
RESOLVEFLOW_AI_PROVIDER=gemini
RESOLVEFLOW_AI_MODEL=gemini-3.6-flash
RESOLVEFLOW_GEMINI_THINKING_LEVEL=minimal
RESOLVEFLOW_AI_MAX_OUTPUT_TOKENS=1024
RESOLVEFLOW_AI_LIVE_ENABLED=false
RESOLVEFLOW_AI_FREE_TIER_VERIFIED=false
```

Fill only the empty key value manually. Do not set the two flags to true until
the actual AI Studio project/model free tier has been confirmed and the developer
has explicitly approved a live test. Process environment variables override this
file, so remove stale model overrides from the launch shell when changing models.
Restart the API after configuration changes.

After that separate approval and deliberate enablement, the single-call synthetic
smoke command is (do not run it during configuration):

```bash
UV_CACHE_DIR=../../.cache/uv uv run python scripts/gemini_smoke.py --allow-live-synthetic
```

Without the flag and all three configuration prerequisites, it exits without a
provider call. It supplies its own synthetic policy/ticket, does not read business
records, uses the configured generation cap (default 1,024; maximum 2,048),
and reports metadata/validation only.
Each explicit invocation can make at most one call; this diagnostic bypasses
application draft budgets because it does not access the application database.
Do not put it in a retry loop or routine CI. Clear live enablement after testing.

For the ticket UI, additionally set `RESOLVEFLOW_AI_SYNTHETIC_WORKSPACES` to a JSON
array containing only the UUIDs of operator-verified synthetic workspaces, restart
the API, index their synthetic documents and open a synthetic ticket. An authorized
editor must check the synthetic-data confirmation before generating. No regular
workspace is allowlisted by default.

## Limits and failure behavior

| Setting | Default | Enforced maximum |
| --- | --- | --- |
| `AI_TICKET_CHARS` | 4,000 title + description | 8,000; longer tickets rejected |
| `AI_TOP_K` | 4 passages | 8 |
| `AI_CONTEXT_CHARS` | 6,000 passage characters | 8,000; whole passages selected |
| Retrieval query | first 1,000 title/description characters | 1,000 |
| Prompt contracts | system 6,000 / JSON content 20,000 characters | fixed bounds |
| `AI_MAX_OUTPUT_TOKENS` | 1,024 | 2,048 |
| `GEMINI_THINKING_LEVEL` | minimal | explicit supported level; `default` omits configuration |
| Output validation | raw JSON 24,000 characters; response 5,000; 8 statements | fixed bounds |
| `AI_TIMEOUT_SECONDS` | 25 | 30 |
| `AI_MAX_CALLS` / `AI_MAX_RETRIES` | 1 / 0 | fixed in this step |
| `AI_CONCURRENCY` | 2 | 4; DB reservations and process semaphore |
| `AI_DAILY_GLOBAL` | 20 requests | 100 |
| `AI_DAILY_WORKSPACE` | 10 requests | 50 |
| `AI_DAILY_USER` | 5 requests | 25 |

All `AI_*` and `GEMINI_THINKING_LEVEL` settings have the `RESOLVEFLOW_` prefix. Input
budgets are character bounds, not exact provider token estimates. Output tokens
are capped in the SDK; reported usage is stored when available.

Daily UTC budgets conservatively count reserved requests, including abstentions
and failures. A PostgreSQL transaction advisory lock makes checks/reservations
atomic across API processes. Replaying a request UUID returns its existing state
without another call. Failed requests require a new deliberate request; quota
errors never trigger a paid fallback or automated retry. An abandoned reservation
older than two minutes is marked failed on the next generation request.

An SDK timeout is a network timeout, not a guarantee that the remote provider
cancelled computation. Browser disconnect/cancellation cannot reliably cancel
the synchronous upstream call; the API may finish and persist it. Refresh draft
history before retrying. Idempotency prevents duplicate calls for the same request.
Native embedding cancellation and durable queued execution remain future work.

## Privacy boundary

Google's [Gemini API terms](https://ai.google.dev/gemini-api/terms) and pricing
describe data use for unpaid services. This integration therefore permits only
synthetic data in live tests. Cloud generation remains disabled by default.
The allowlist and explicit synthetic confirmation are the primary controls;
regex checks are a limited additional screen, **not comprehensive DLP**.

Do not enable this path for confidential customer tickets or private company
documents without a separately authorized privacy/security design and terms
review. No key, prompt, provider error body or raw output is written to logs.
Authorized draft records intentionally retain response text and review history.
Deleting source documents removes stored citation quotations/references but does
not erase generated response history, which may itself quote source text; retention/deletion policies are future work.
