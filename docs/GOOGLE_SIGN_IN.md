# Google sign-in for the account application

The full application's sign-in and registration forms use the same Google flow. The recruiter showcase remains a separate synthetic experience. Google sign-in is disabled by default. Email/password sign-in, registration and recovery work independently.

## Configure a separate account origin

1. In Google Auth Platform, configure the audience, branding, support contact and test users for the account application. Create a **Web application** OAuth client. Use distinct clients and secrets for local development, staging and production.
2. Register the exact **authorized redirect URI**. For a local web server on port 3000 use `http://127.0.0.1:3000/auth/google/callback`. For staging or production use the corresponding account origin over HTTPS followed by `/auth/google/callback`. Match scheme, host, port and path exactly. The recruiter showcase URL is outside this flow.
3. Configure the following server-only FastAPI variables in its ignored local environment file or the hosting secret manager. Keep credentials out of source control, client bundles and logs.

| Variable | Purpose |
|---|---|
| `RESOLVEFLOW_GOOGLE_ENABLED` | Enable with `true` once the other values are set. |
| `RESOLVEFLOW_GOOGLE_CLIENT_ID` | Web client ID for this environment. |
| `RESOLVEFLOW_GOOGLE_CLIENT_SECRET` | Corresponding secret, available only to FastAPI. |
| `RESOLVEFLOW_GOOGLE_REDIRECT_URI` | Exact callback registered with Google. |
| `RESOLVEFLOW_TRUSTED_ORIGINS` | Include the callback's origin in the existing explicit JSON list. |

4. Use a full-mode Next.js build with the existing server-only `API_INTERNAL_URL`. Apply migration 0013 through the normal migration procedure for the intended account database. Downgrade refuses to discard existing provider identities. Google-only accounts have a null password hash.
5. Before staging, configure the existing verified email delivery path, confirm private HTTPS ingress and cookie settings, and exclude callback query strings, request bodies, cookies, token responses and authorization URLs from access logs and telemetry. Test real consent, denial, return sign-in, mailbox proof, logout and session expiry using approved staging test users. A real Google consent test remains outstanding.

## Session and identity handling

A same-origin CSRF-protected POST starts one five-minute authorization transaction per anonymous session. FastAPI creates state, nonce and an S256 PKCE challenge. PostgreSQL holds the hashed state and nonce, the short-lived verifier and a validated internal destination. The callback consumes the transaction before exchanging its code at Google's fixed HTTPS endpoint. Google Auth verifies the signed ID token. The application also checks nonce, authorized party, verified email and subject. It retains the Google subject and the local user association. Provider tokens are discarded.

New accounts start without workspace memberships. An email collision or a changed Google email returns a generic sign-in error. An existing user can use their original sign-in method. Automatic linking remains unavailable. Personal settings can change the local email after proof of both inboxes. The original Google email check stays bound to the same provider subject. Password recovery cannot establish a password for a Google-only account.

Where the existing policy requires application mailbox verification, Google sign-in creates a restricted session. Open the verification email in that same browser and choose **Verify with my signed-in Google account**. Verification revokes the session. Sign in again for workspace access. Google's verified-email claim alone cannot satisfy the application's production SMTP proof requirement.

## Local verification

The backend Google suite uses an offline authorization-code fixture, one-use grants and RSA-signed ID tokens. Its test certificate transport exercises the production signature verifier. Run the database-backed suite with the existing disposable PostgreSQL test runner. For browser verification, build the full web app and run `python scripts/test_browser.py --google-oidc` from the API directory using the configured local environment. This opt-in runner uses a loopback provider fixture and skips classifier training. Playwright intercepts the browser's outbound Google navigation. The normal API entry point has no fixture authorization endpoint.

[Google OpenID Connect guide](https://developers.google.com/identity/openid-connect/openid-connect) · [Google ID token validation](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token)
