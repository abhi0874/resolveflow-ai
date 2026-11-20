# Authentication — Step 4

## Current identity behavior — Step 19B

The original Step 4 narrative below is historical. Account verification and secure
password recovery now reuse the same sessions, Argon2id hashing, CSRF middleware
and shared rate limiter. See [EMAIL_DELIVERY.md](EMAIL_DELIVERY.md) for routes,
settings, token lifetimes, outbox retries, local SMTP setup and rollout limitations.

Registration creates a hash-only verification intent. With verification required,
new/duplicate registration returns generic 202 and does not sign the account in.
Local compatibility mode preserves the existing 201/session and duplicate-409
behavior; do not mistake this local contract for production enumeration resistance.
Production always requires exact-address SMTP verification; it rejects disabling
the policy, local proof and old local mail tokens. Existing development users keep
their default compatibility-mode access. Recovery/resend requests return generic
202 responses regardless of account eligibility; confirmation errors are generic.

Verify confirmation requires the email token plus the registration password to
avoid activating an attacker-created preregistration. Recovery requires the token
and matching new passwords, retains the 15–128 character policy, increments the
credential version and revokes all account sessions and other identity tokens.
Both actions are transactional, expiry-bound and single-use. Roles/memberships do
not change. Structured audit rows contain account ID/event/time only. Password
change and login serialize on the account row to prevent reset/login races.

No public email-change endpoint exists. Exact-address proof and token bindings
prevent a changed email from inheriting verification. A future change-address flow
must require reauthentication and proof of the new address, not a direct update.
Migration 0012 is tested locally in isolated databases and remains pending on the
development database. External delivery, MFA, device-management UI, global abuse
fairness, identity-record retention and commercial operational controls remain gaps.

**Local follow-up, 2026-10-23:** migration 0011 and account-bound invitation
acceptance now add a verification timestamp and rotate recipient sessions.
Delivery is a private synthetic local sink only, disabled by default and forbidden
in production; actual external email ownership remains unverified. The Step 4
description below is historical. See [IDENTITY_AND_RECOVERY.md](IDENTITY_AND_RECOVERY.md)
for current behavior, migration instructions and limitations.

Implemented and verified 2026-10-19. Authentication runs in FastAPI and PostgreSQL;
Next.js presents the forms and forwards a small, explicit set of first-party API
routes. There is no hosted identity provider, JWT, social login, email delivery,
password recovery or paid dependency.

## Request path and sessions

```text
Browser /login, /register, /app
  → same origin /api/v1/auth/* and /api/v1/workspaces/*
  → Next.js allowlisted route handler (server-only API_INTERNAL_URL)
  → FastAPI validation, session/CSRF checks, permission checks
  → SQLAlchemy request session → PostgreSQL
```

The browser never contacts a separate authentication origin. Next.js forwards
only the expected session cookies, Origin, Content-Type, CSRF and Fetch Metadata
headers. It does not forward user-supplied hosts or forwarding headers, accept
arbitrary upstream URLs, follow upstream redirects, or cache responses. The route
handler enforces a 16 KiB body limit while reading, except allowlisted document
uploads (5 MiB proxy ceiling, configurable backend limit defaulting to 2 MiB). Server rendering uses the same
upstream but checks `/auth/me` before fetching or rendering workspace data.
Invalid sessions redirect to `/login`; service failures render a safe unavailable
page. Logout uses a full document navigation, discarding the current client state.

Opaque session credentials contain 32 cryptographically random bytes, encoded as
43 URL-safe characters. Only SHA-256 digests are stored in `auth_sessions`; raw
credentials exist in HttpOnly cookies and request memory. This use of SHA-256 is
for random high-entropy credentials, never passwords. Each session also stores a
random synchronizer CSRF token, optional user ID, creation time and expiration.
An anonymous pre-login session lasts 10 minutes. Registration and login replace
it (or the previous signed-in session) with a new session and CSRF token, preventing
session fixation. Authenticated sessions expire after 12 hours by default, with
no sliding renewal or refresh tokens. Every protected request validates expiration,
current user account status and current workspace membership on the backend.
Logout deletes the session row and expires the cookie. Other devices' sessions are
not affected. Expired credentials cannot be revived by resetting browser cookies.

### Cookies

| Environment | Cookie | Behavior |
| --- | --- | --- |
| Local development / tests | `resolveflow_session` | HttpOnly, SameSite=Lax, Path=/, no Domain; HTTP permitted on loopback |
| API `RESOLVEFLOW_ENVIRONMENT=production` | `__Host-resolveflow_session` | HttpOnly, Secure, SameSite=Lax, Path=/, no Domain |

Production settings reject missing/empty, HTTP, wildcard or localhost trusted
origins. There is no option to turn off Secure cookies in production. Next.js adds
nosniff, frame-denial and same-origin referrer headers; its production build also
adds HSTS. Production must actually terminate TLS, set API production mode and use
explicit HTTPS origins. Neither a cookie flag nor an origin string supplies TLS.

For an independently hosted backend, keep the browser-facing Next.js application
and `/api/v1` route handler on the **same HTTPS origin**, and point the server-only
upstream at the backend's HTTPS origin. Keep session cookies host-only on the
frontend. Do not change SameSite to None or enable wildcard credentialed CORS as a
shortcut. Direct cross-site browser authentication is intentionally unsupported
and would require a separate security review. No hosted deployment has been tested.

## Passwords, email and account responses

`argon2-cffi==25.1.0` provides Argon2id with 64 MiB, three iterations and four lanes
(the RFC 9106 low-memory profile), random salts, 32-byte hashes, and verification
through the library. Successful login rehashes when parameters need updating.
Passwords must contain 15–128 characters, cannot be all whitespace, and are not
trimmed or silently truncated. Registration requires matching confirmation.
Passwords are Pydantic SecretStr values and never appear in response models.
The existing database hash-format constraint remains in place. New accounts use
Argon2id; authentication does not implement legacy bcrypt migration.

`email-validator==2.3.0` validates syntax without paid services or delivery checks.
Input is stripped and lowercased consistently with the existing unique index.
Registration returns only ID, email, created_at and `email_verified: false`.
No email ownership verification occurs. Do not use this implementation to claim
verified identities. Login failures use the same HTTP 401 response for absent
accounts, wrong passwords and inactive accounts. Missing accounts run a dummy
Argon2 verification. Duplicate registration performs hashing before returning a
generic HTTP 409. Its status still reveals a registration conflict, so account
enumeration is reduced, not eliminated. Authorized member addition also necessarily
reveals whether the requested existing account can be added. There is no public
account-search endpoint.

## CSRF and abuse defenses

1. `GET /api/v1/auth/csrf` creates a short-lived anonymous session if needed and
   returns its synchronizer token. It reuses a valid existing session. The response
   is `Cache-Control: no-store`; browser same-origin policy prevents foreign pages
   reading it. The cookie is HttpOnly; the client keeps the CSRF value only in
   transient request memory.
2. Every mutation, including login, registration and logout, requires the exact
   configured Origin, JSON Content-Type (binary only for the exact document upload
   collection POST), and matching `X-CSRF-Token` for the cookie's
   unexpired server-side session. Missing/null/foreign origins, malformed/mismatched
   tokens and explicit `Sec-Fetch-Site: cross-site` are rejected. SameSite and CORS
   are defense in depth, not the only CSRF controls.
3. API CORS remains exact-origin, GET-only, without credentials for the original
   public health indicator. Authentication uses the same-origin route handler.
4. Both servers bound ordinary mutation bodies to 16 KiB; the exact binary document
   upload endpoint has its separately bounded larger limit. Backend schemas reject unexpected
   fields, malformed email/UUIDs, invalid roles and oversized password/name/slug
   values. SQL uses parameter binding; user input never selects a SQL identifier.
5. `auth_rate_limits` has shared atomic PostgreSQL counters. Login and registration
   each allow 10 attempts per normalized-email key and 60 per connecting-IP key per
   15-minute window, counting successful and failed attempts. Anonymous CSRF-session
   creation allows 120 per connecting IP per window. HTTP 429 includes Retry-After.
   Counters use hashed keys, not plaintext email/IP fields; hashes are not anonymization.

Through the first-party proxy, the API sees the proxy's connecting IP, so the
60-attempt IP budget is currently shared by users of that proxy. This conservative
limit can throttle legitimate users; it is not a final production capacity policy.
Run Uvicorn with `--no-proxy-headers` as documented. Before public deployment, review
trusted ingress identity, edge limits, slow-request/header limits, denial-of-service
capacity, clock synchronization and a measured limit policy. Do not blindly trust
`X-Forwarded-For`. Account-key throttling can also be abused to temporarily deny
another user's login. No Redis or process-local limiter is used.

Session and counter expiry is enforced during requests, independent of cleanup.
For storage maintenance, run from `apps/api`:

```bash
UV_CACHE_DIR=../../.cache/uv uv run python scripts/prune_auth.py
```

This explicit command removes only expired authentication rows. No scheduler,
worker, or background service has been installed. Review scheduling and retention
before production; do not log cookies, passwords, full requests, or credentials.

## Endpoints

| Method/path under `/api/v1` | Behavior |
| --- | --- |
| GET `/auth/csrf` | CSRF bootstrap/retrieval; sets anonymous cookie when needed |
| POST `/auth/register` | JSON email, password, password_confirmation; 201 safe user + rotated session |
| POST `/auth/login` | JSON email/password; 200 safe user + rotated session, or generic 401 |
| POST `/auth/logout` | JSON `{}` with CSRF; 204, session deletion and expired cookie |
| GET `/auth/me` | Safe user; 401 for absent/expired/inactive sessions |

All identity, workspace and ticket API responses are no-store. Backend errors use the
existing safe envelope. A 403 indicates failed CSRF/authorization; 409 indicates
conflict; 422 invalid input; 429 throttling; 503 unavailable database/upstream.
No endpoint returns hashes or raw session tokens in JSON.

## Local setup and verification

From the repository root, in terminal 1:

```bash
cd apps/api
export UV_CACHE_DIR=../../.cache/uv
uv sync --locked
uv run python scripts/local_db.py start
uv run alembic upgrade head
uv run --locked uvicorn resolveflow.main:app --app-dir src --host 127.0.0.1 --port 8000 --no-proxy-headers --reload
```

In terminal 2, from the repository root:

```bash
npm --prefix apps/web ci --cache ../../.cache/npm
API_INTERNAL_URL=http://127.0.0.1:8000 npm --prefix apps/web run dev
```

Use one hostname consistently: [local login](http://127.0.0.1:3000/login),
[registration](http://127.0.0.1:3000/register), and [workspaces](http://127.0.0.1:3000/app).
Switching between localhost and 127.0.0.1 changes the cookie host. Defaults authorize
both port-3000 origins. `API_INTERNAL_URL` is mandatory for `next start`; development
only defaults to localhost port 8000. The original `NEXT_PUBLIC_API_BASE_URL` remains
for the landing-page health indicator and does not control auth routing.

Additional API configuration in `.env.example`:

```dotenv
RESOLVEFLOW_TRUSTED_ORIGINS=["http://127.0.0.1:3000","http://localhost:3000"]
RESOLVEFLOW_SESSION_HOURS=12
```

For production, set `RESOLVEFLOW_ENVIRONMENT=production`, explicit HTTPS trusted
origins and the server-only HTTPS backend URL. Keep database credentials server-only.
There is no static session-signing secret to provision; random credentials are
revocable in PostgreSQL. Ports/origins are configuration, not user-controlled routing.

Run backend checks using [DATABASE.md](DATABASE.md). Browser tests use installed
Google Chrome and Playwright 1.64.1, without modifying the user's browser profile:

```bash
# From repository root. Build first; no database is required for this build.
NEXT_TELEMETRY_DISABLED=1 npm --prefix apps/web run build
# PostgreSQL must be running. Creates and drops only a fresh marked test database.
(cd apps/api && UV_CACHE_DIR=../../.cache/uv uv run python scripts/test_browser.py)
```

The browser helper starts the built Next.js app on 3100 and FastAPI on 8100 against
a fresh random database, runs Playwright, stops its own process groups and removes
only its marked database. Direct `npm run test:e2e` refuses to run without the
isolation flag set by that helper. Ports 3100/8100 must be free. The helper refuses occupied ports before database
creation and waits for readiness in its own child logs, so it never reuses an
unrelated server. Logs/screenshots
remain in ignored `.cache/` and `test-results/`; traces are disabled so passwords
and session headers are not persisted in browser traces. No test accounts remain
in development. Dependency installation/network access is separate from test execution.

## Review results and limits

Automated tests cover real hashing, cookie rotation, persisted sessions, logout
replay rejection, expiration, inactive accounts, CSRF failures, malformed/oversized
input, shared throttling, protected SSR, and real browser registration/login/logout.
Authorization tests and role boundaries are detailed in [AUTHORIZATION.md](AUTHORIZATION.md).
Desktop/mobile screenshots were inspected, and 390/320px overflow checks passed.

Email verification, secure recovery, MFA, compromised-password checks, device/session
management, authentication audit events, full CSP rollout, production load/penetration tests,
and backup/restore exercises remain deferred. No production-security certification
is claimed. `npm audit --omit=dev` reported zero runtime vulnerabilities. The full
audit reports an unresolved high-severity development glob-parser chain through
`braces`/`micromatch`/`fast-glob` and Next's ESLint plugin
([advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm)). It is outside the
runtime bundle; do not process untrusted glob patterns with the lint tooling.
The suggested downgrade to eslint-config-next 14.2.35 is incompatible with this
Next 16 project and was not applied. This remains a dependency-maintenance limitation.

References: [Argon2 library API](https://argon2-cffi.readthedocs.io/en/stable/api.html),
[OWASP session guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html),
[OWASP CSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).

Step 5 extends the same proxy to allowlisted ticket endpoints and bounded,
validated collection/history queries. Cookie, Origin, CSRF, body-size and no-store
controls are preserved. See [TICKET_MANAGEMENT.md](TICKET_MANAGEMENT.md).

Step 6 extends the allowlist to document operations, preserving session, CSRF,
Origin, Fetch Metadata, no-store and tenant checks. Only document upload forwards
X-Upload-Filename and accepts application/octet-stream. Download forwards safe
attachment/CSP headers. See [KNOWLEDGE_BASE.md](KNOWLEDGE_BASE.md) for the contract.

Step 7 adds only the fixed ticket classify suffix to the session proxy allowlist.
The POST uses JSON, the ordinary 16 KiB body ceiling, exact Origin and session CSRF.
It returns noncached recommendations; arbitrary ticket text and model paths are
not accepted from the request. Existing auth/session behavior is unchanged.
