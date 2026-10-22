# Demo security and live-inference boundary

## Data and authentication separation

The demo imports only authored TypeScript fixtures and browser-local state. It has
no database client, provider SDK, credential loader or real-workspace identifier.
The public route is separate from `/app`; demo mode never grants a production user
or workspace permission. Its server-side API proxy rejects all `/api/v1/*` methods
before cookies/backend resolution. Server data reads fail unauthorized without an
outbound request. The full mode's original authentication, CSRF and RBAC remain intact.
Mode is validated deployment configuration; query parameters, headers and local storage
cannot select the server mode. A future deployment must use a separate demo origin.

Browser storage is untrusted: the adapter validates command types, enum values,
lengths, references, action count and maximum serialized size before replaying a
journal. Invalid journals restore fresh fixtures with a notice. Text is rendered by
React without unsafe HTML. Reset touches one demo-specific session key. There are
no uploads or arbitrary URL fetches. Local actions are not a security audit ledger.
No private content should be entered; the UI explicitly requests synthetic data.

## Live AI is deliberately unavailable

`POST /api/demo/generate` is a fail-closed reserved boundary returning 403
`demo_live_disabled` for every request, including authenticated-looking requests,
missing keys, invalid scenarios and attempted output-limit overrides. It does not
parse prompts, read an API key, instantiate an SDK or make an outbound request.
Other unsupported methods receive the framework's method rejection. There is no
public password, browser secret, process-memory rate budget or paid fallback.

`DEMO_LIVE_AI_ENABLED` accepts only unset/`false`; `true` or malformed values fail
configuration validation. This is stronger than an enableable feature flag: public
inference is **not implemented** in this release. The demo works independently of
provider availability, missing credentials or exhausted quota, using clearly labeled
examples at all times. There is no claim that SDK quota-response parsing, output-token
limits or timeouts were newly tested in this disabled Next.js endpoint. Existing
Python Gemini adapter tests continue covering those controls in the full application.

Reliable public usage limits need an approved server-authorized mechanism and shared
atomic budget persistence. Neither is provisioned here. Future activation requires
separate work and approval: authorize each fixed synthetic scenario server-side,
reserve a global request budget atomically before dispatch, cap output and timeout,
use appropriate minimal thinking, forbid retries/fallback, normalize quota failures,
validate structured output/citations and keep any key in server-only secret storage.
The existing provider-neutral Python AIProvider interface and configurable
`RESOLVEFLOW_AI_MODEL=gemini-3.6-flash` remain unchanged. No UI component hardcodes
provider model selection. Do not add a Gemini key to this demo deployment yet.

## Verification and remaining limits

Tests reject full API reads/writes with session-like cookies, verify no demo interaction
issues API requests, check text escaping, validate corrupt journals, preserve other
storage keys and reject invalid/duplicate/abstention approvals. Demo E2E runs against
unreachable backend origins and blocks external requests. Full-mode regression tests
separately verify real auth/workspace behavior.

No real records or credentials were exported; no customer action, AI request or service
purchase occurs. This foundation is not a penetration-test certification. Hosting
quotas, future production controls and public-domain acceptance remain separate gates.
