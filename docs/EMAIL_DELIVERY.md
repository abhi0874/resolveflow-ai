# Email verification and account recovery — Step 19B

Implemented locally with the existing FastAPI/PostgreSQL sessions, Argon2id,
CSRF protection, shared rate limits and RQ/Valkey workers. No hosted email account,
billing, deployment or live Gemini inference is configured by this step.

**Local SMTP receipt is tested with Mailpit. External mailbox deliverability is
not verified.** A mock TLS/authentication adapter test is not evidence of external
delivery. Final executed suite results are recorded in [PROJECT_STATUS.md](PROJECT_STATUS.md).

## Architecture and endpoints

Registration creates an identity-email delivery intent and hashed random token in
the same transaction as the account. The HTTP request does not connect to SMTP.
The existing `scripts/jobs.py dispatch` publishes due intent UUIDs onto the existing
RQ queue; `scripts/jobs.py worker` executes the fixed allowlisted email handler.
PostgreSQL remains the durable source of truth. No second queue framework or paid
dependency was added.

`EmailDelivery` defines verification/recovery sends and a safe `DeliveryResult`.
The SMTP adapter uses Python's standard-library `smtplib`, `email` and `ssl`.
Business logic does not depend on a vendor SDK. `local` sends actual MIME messages
to a loopback-only inbox without credentials. `smtp` requires authentication plus
certificate-validated STARTTLS or implicit TLS; it never falls back to plaintext.

All endpoints below are POST under `/api/v1/auth`, with JSON, existing same-origin
CSRF protection, body-size limits and Pydantic validation. GET links never mutate
accounts. No response returns a token, password or hash.

| Route | Input / result |
| --- | --- |
| `/register` | Existing email/password/confirmation schema. Verified-only policy returns generic 202 for both new and existing addresses and does not create an authenticated session. Local compatibility mode retains the existing 201 session / duplicate 409 contract. |
| `/verification/request` | Email; generic 202 whether missing, inactive, already verified or eligible. Eligible accounts receive an intent, subject to cooldown. |
| `/verification/confirm` | Token and the registration password; verifies ownership, consumes token and invalidates prior sessions. Sign in again afterward. |
| `/password/request` | Email; generic 202 for eligible and unknown/inactive accounts. Never sends existing passwords. |
| `/password/confirm` | Token, new password and matching confirmation; updates Argon2id hash, consumes token, rotates credential version and revokes all account sessions. Sign in again afterward. |

Existing login, logout, invitation, workspace and tenant APIs are retained.
Unverified users with correct passwords receive `email_verification_required` when
policy blocks login. Existing authenticated sessions also face the server-side
workspace boundary; a client flag cannot bypass it. Workers recheck that policy
before executing queued privileged workflows.

## Token and account security

- Tokens contain 32 cryptographically random bytes, encoded as 43 URL-safe
  characters. PostgreSQL stores only SHA-256 digests. Hash comparison uses
  `secrets.compare_digest`; password hashing continues through Argon2id.
- The delivery worker creates a fresh token immediately before sending and commits
  only its hash. This avoids a plaintext or decryptable token in PostgreSQL/RQ.
  Raw tokens exist transiently in worker/browser memory and in the actual email,
  including the private test inbox; they are never an application log field.
- Tokens bind user ID, normalized address, purpose and credential version. Verify
  links expire 24 hours after the request; reset links expire after 30 minutes.
  Queue delays/retries do not extend those deadlines. Wrong purpose/account,
  changed email/credentials, inactive users, expiry, invalidation and replay fail.
- Consumption locks the account before the token. Exactly one concurrent reset
  succeeds. Verification requires the registration password as well as the link:
  someone must not activate an attacker-created preregistration with an
  attacker-known password just by clicking an unsolicited email. The page directs
  someone who did not register the account to recovery instead.
- A successful reset revokes all sessions, all other identity tokens and outstanding
  invitations targeting the account. It does not change workspace membership or
  role. Verification also revokes sessions and outstanding identity tokens.
  Login locks the account while checking credentials/issuing its session so an old
  password cannot race a committed reset to mint a surviving session.
- Verification records both the exact `verified_email` and proof source. Changing
  an address through the ORM clears verification; a mismatched address fails the
  property and token checks even if changed through SQL. **There is no public
  email-change endpoint.** A future address-change API must require reauthentication,
  new-address proof and session invalidation; do not add a direct update shortcut.
- Production rejects local proof and old local verification/reset tokens. Historical
  invitation timestamps are retained by migration, but not promoted to external
  proof. Production verification must be obtained through configured SMTP delivery.
- Rate limits reuse shared PostgreSQL counters: 60 requests per connecting IP and
  10 per address per 15 minutes for request endpoints; confirmation attempts have
  their own IP limit. Resends additionally coalesce within 60 seconds and invalidate
  earlier unconsumed tokens. Unknown addresses use the same response and rate keys.
  Registration in local compatibility mode still reveals duplicate conflict; this
  mode is forbidden as a production verification-policy bypass. Response equality
  is not a constant-time account-enumeration guarantee.
- Structured audit rows contain account ID, event and timestamp, not tokens,
  passwords or email bodies. Delivery rows track attempt/status and sanitized error
  category. Existing request logs record route/status/correlation, not request bodies.

The emailed URL uses `/verify-email#token=...` or `/reset-password#token=...`.
Fragments do not reach HTTP access logs or Referer headers. The frontend extracts
the token into component memory and removes the fragment with `replaceState`;
it does not use browser storage or render the raw token. Pages set no-referrer and
noindex metadata. Submitting the form uses the existing CSRF-protected proxy.
Any same-origin script/XSS could still read in-memory tokens: existing CSP and XSS
hardening limitations remain, rather than being solved by URL fragments.

## Delivery reliability and limits

An intent tracks `pending`, `sending`, `sent`, `failed` or `cancelled`. Publishing
is bounded to 20 due rows per dispatcher pass and respects existing queue capacity.
RQ carries only the intent UUID; no token, password, recipient or body. Publishing
uses a 60-second deduplication interval. Workers claim a 120-second lease, with a
45-second RQ job timeout and configurable 1–10 second SMTP socket timeout.

There are at most **three delivery attempts per intent**, with 60/120-second
backoff before retry, including lease recovery after worker failure. Authentication
and permanent SMTP errors fail without retry; transient transport/4xx errors can
retry. Duplicate queue execution during the lease or after success does not send
again. Expired/revoked requests are cancelled. Broker failure leaves the durable
intent available for a later dispatcher pass. No blanket RQ retry policy is enabled.

SMTP cannot guarantee exactly-once receipt: a server may accept DATA just before
the worker crashes. Bounded recovery can then send another message, rotating the
token so the earlier link is invalid. Use the most recently delivered link. This
is explicitly not a transactional email-provider delivery guarantee. A successful
SMTP result means transport acceptance, not inbox placement or proof that a human
read it. No bounce/webhook processing is implemented.

Email and workflow tasks currently share the bounded worker queue. Production
capacity/fairness, sustained abuse tests, dead-letter alerting, and retention/pruning
of identity/audit rows need an operational policy. Do not describe this local
implementation as a complete commercial messaging service.

## Migration and rollout

New additive Alembic revision **0012**, after unchanged 0011, adds exact-address
verification source, credential version, `identity_emails` and `identity_audit`.
Existing users, password hashes, sessions, memberships and business records remain.
Existing development users keep their compatibility-mode access. Historical
verification timestamps are retained but do not automatically verify ownership.

**Step 19B.1 applied 0012 to the owned development database on 2026-10-24**, after a
fresh private backup, isolated restore/migration rehearsal and original-record
fingerprint comparison. Revision/head and metadata agree. See [DATABASE.md](DATABASE.md)
for the retained backup and recovery precautions. Other checkouts still need a
protected, deliberate migration before starting new API/workers against an old schema.
Downgrade tests run only in disposable databases: downgrading 0012 loses the new
outbox/audit/proof data and must not be used as a casual rollback on populated data.

The actual development frontend flow passed through FastAPI, RQ/Valkey and Mailpit:
registration unverified → local email verification → login → recovery email → reset
→ new-password login. Replayed links, old sessions and the old password were rejected;
workspace permissions were preserved. PostgreSQL confirmed local proof and consumed
tokens, with exactly one delivery per purpose despite immediate resend requests.
The synthetic account/workspace were retained. Fresh isolated tests additionally
verified expiry and shared rate limits. This is **local Mailpit evidence only**;
external SMTP delivery is still unconfigured and unverified.

Verification used process-only local mail settings. Private `.env` was not changed,
and the existing development compatibility policy remains intact. The temporary
application/worker/inbox processes were stopped after testing; start the documented
services below to use local email again.

Production policy always requires verification. `RESOLVEFLOW_REQUIRE_EMAIL_VERIFICATION=false`
is rejected in production. For rollout, prepare authorized SMTP delivery and HTTPS
origins first, then provide recovery/verification to existing accounts before
expecting privileged access. Local-only proof must be reverified. Production SMTP
invitation delivery remains a separate gap: this step implements **account**
verification/recovery, not a new workspace invitation transport.

## Local inbox setup — free, no external mail

Mailpit is MIT licensed. The installed test binary is **1.32.0**, downloaded from
the official project release, macOS ARM64 SHA-256:
`23709bd727f20da2290de6a2a40c4685c48a3127586d77370efd1a3a595f9ef6`.
Its archive and license are retained under ignored local directories. The adapter
requires no new Python dependencies; Python's existing standard library is used.
See [official installation](https://mailpit.axllent.org/docs/install/),
[MIT license](https://github.com/axllent/mailpit/blob/develop/LICENSE),
[SMTP settings](https://mailpit.axllent.org/docs/configuration/smtp/) and
[Python SMTP documentation](https://docs.python.org/3/library/smtplib.html).

On this Mac, the already installed binary is
`.local/native/mailpit-1.32.0/mailpit`. For another platform, obtain its matching
official release binary and verify that artifact's checksum; do not reuse the
ARM64 macOS checksum for another artifact. No system service or global installation
is required. Keep the release's license with the binary.

For a manual synthetic inbox, from the repository root (first check ports are free):

```bash
umask 077
mkdir -p .local/mailpit
env -i PATH="$PATH" .local/native/mailpit-1.32.0/mailpit \
  --smtp 127.0.0.1:1025 --listen 127.0.0.1:8025 \
  --database "$PWD/.local/mailpit/inbox.db" \
  --disable-version-check --quiet --max 100 --max-message-size 1 \
  --allowed-hosts 127.0.0.1,localhost --block-remote-css-and-fonts
```

Open `http://127.0.0.1:8025` locally. Do not expose or tunnel these ports, enable
relay/webhooks, or put real customer messages in this inbox. It contains synthetic
tokens; do not copy messages into chat, logs, commits or issue attachments. Stop
only the foreground process with Ctrl+C. The test harness instead allocates random
loopback ports, uses a private temporary inbox and removes it after stopping its
own process. It strips inherited Mailpit environment configuration so it cannot
inherit a relay or external update check.

After the migration is deliberately applied, configure the API, dispatcher and
worker consistently in their process environments or private `apps/api/.env`:

```dotenv
RESOLVEFLOW_EMAIL_DELIVERY=local
RESOLVEFLOW_EMAIL_PUBLIC_ORIGIN=http://127.0.0.1:3000
RESOLVEFLOW_EMAIL_FROM=no-reply@resolveflow.test
RESOLVEFLOW_SMTP_HOST=127.0.0.1
RESOLVEFLOW_SMTP_PORT=1025
RESOLVEFLOW_SMTP_TLS=none
RESOLVEFLOW_SMTP_TIMEOUT_SECONDS=5
RESOLVEFLOW_REQUIRE_EMAIL_VERIFICATION=true
RESOLVEFLOW_AI_LIVE_ENABLED=false
```

Use the existing startup commands in [WORKER_OPERATIONS.md](WORKER_OPERATIONS.md).
No SMTP username/password is allowed in local mode. Verification is optional by
default only in development/test; the explicit setting above rehearses the secure
policy. The frontend needs no mail credentials. Open a synthetic verification link,
enter the password chosen at registration, then sign in. Use **Forgot password?**
to request another synthetic email and choose a new password. GET link previewing
does not consume it; form confirmation does.

## External SMTP prerequisites — pending, not activated

Only after separate authorization, supply an approved provider/account, validated
sender address/domain, current plan/quota/overage terms, and secrets through the
deployment's server-only secret mechanism. Do not use a personal Gmail account
implicitly. No provider's free tier is claimed or activated by this step.

Required variables for `RESOLVEFLOW_EMAIL_DELIVERY=smtp`:

- `RESOLVEFLOW_SMTP_HOST`, `RESOLVEFLOW_SMTP_PORT`
- `RESOLVEFLOW_SMTP_TLS=starttls` or `ssl` (no downgrade)
- `RESOLVEFLOW_SMTP_USERNAME`, `RESOLVEFLOW_SMTP_PASSWORD`
- `RESOLVEFLOW_EMAIL_FROM` (approved sender)
- `RESOLVEFLOW_EMAIL_PUBLIC_ORIGIN` (HTTPS frontend origin)
- Matching `RESOLVEFLOW_TRUSTED_ORIGINS` and `RESOLVEFLOW_ENVIRONMENT=production`

Keep passwords in the private environment file or approved secret manager; never
paste them into chat or a shell command that enters history. The safe template does
not contain real credentials. The user's existing `.env` and Gemini key were not
edited. Configure SPF/DKIM/DMARC, sender verification, transport limits, privacy,
bounce handling and monitoring as required by the chosen provider. Then request
an explicitly approved controlled delivery test. TLS adapter mocks and local
Mailpit tests do **not** satisfy external deliverability acceptance.

## Verification commands

With the existing owned PostgreSQL running, from `apps/api`:

```bash
PYTEST_ADDOPTS='tests/test_identity_email.py --tb=short' \
  RESOLVEFLOW_AI_LIVE_ENABLED=false .venv/bin/python scripts/local_db.py test
PYTEST_ADDOPTS=--tb=short RESOLVEFLOW_AI_LIVE_ENABLED=false \
  RESOLVEFLOW_AI_FREE_TIER_VERIFIED=false GEMINI_API_KEY=synthetic-test-key \
  .venv/bin/python scripts/local_db.py test
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

From repository root, using the installed Node 24 runtime:

```bash
export PATH="$PWD/.local/native/node-v24.22.1-darwin-arm64/bin:$PATH"
NEXT_PUBLIC_APP_MODE=full NEXT_TELEMETRY_DISABLED=1 npm --prefix apps/web run build -- --webpack
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
(cd apps/api && RESOLVEFLOW_AI_LIVE_ENABLED=false .venv/bin/python scripts/test_browser.py)
npm --prefix apps/web run demo:build
npm --prefix apps/web run test:demo
```

The browser harness enables local email only for its disposable environment. It
starts Mailpit plus actual dispatcher/RQ workers and reads synthetic SMTP messages
through the private inbox API to follow verification/reset links. Provider-failure,
replay, expiry, rate limits, session revocation, migration preservation and
cross-account/tenant behavior also receive backend coverage. No test contacts a
real SMTP provider or invokes Gemini.
