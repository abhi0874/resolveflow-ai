# ResolveFlow account staging

Status on 2026-11-21 (Asia/Kolkata): preparation only. Step 6A verified local behavior with synthetic accounts and provider fixtures. The separate, full account site is unprovisioned. Production account signup is closed because there is no production account origin. The recruiter showcase runs in demo mode and does not expose the account API.

## Historical paid sizing comparison

This comparison predates the mandatory zero-cost decision. Use the [zero-cost decision](ZERO_COST_HOSTING.md). These paid options are outside the release scope.

Use one always-on x86-64 EU Hetzner VM with at least 8 GiB RAM, one application worker, loopback PostgreSQL 18/pgvector and Valkey, and Caddy on public HTTPS. Keep Postgres data, Valkey AOF, uploads, and model artifacts on persistent storage. Mount a second encrypted filesystem for the commit witness and copy recovery material off-host. This is suitable for a small synthetic staging group. A host outage requires recovery from a backup. Linux service startup and resource sizing remain staging checks.

| Item | Estimate before tax |
| --- | --- |
| Hetzner CX33 when available | €8.49/month plus €0.50 for IPv4. The product page showed it unavailable when checked. |
| Hetzner CPX32 fallback, subject to capacity | €35.49/month plus €0.50 for IPv4. |
| Second filesystem | Allow about €1/month for a minimum-size 10 GB block volume. Confirm the quote at approval. |
| Brevo SMTP | $0 within 300 sends/day after account and sender configuration. |
| Backblaze B2 | $0 within the first 10 GB. Published storage rate above that allowance starts at $6.95/TB/month. Restore downloads above the free egress allowance and retained historical versions can add cost. |
| DNS and rehearsal | Existing domain assumed. Registration, taxes, and a temporary recovery VM are additional if needed. Use a separate existing machine for the drill where possible. |

Plan on **about €37/month** with the fallback or **€10/month** if CX33 becomes available and passes sizing. Confirm account/region pricing and disk and RAM headroom before ordering. Render Free sleeps, lacks persistent service disks and expires free PostgreSQL after 30 days. Free SMTP quotas do not guarantee inbox delivery. [Availability and VM sizes](https://www.hetzner.com/cloud/cost-optimized/) · [Hetzner pricing notice](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/) · [IPv4 pricing](https://docs.hetzner.com/cloud/servers/primary-ips/overview/) · [Volume minimum](https://docs.hetzner.com/cloud/volumes/overview/) · [Brevo free limits](https://help.brevo.com/hc/en-us/articles/208580669-FAQs-What-are-the-limits-of-the-Free-plan) · [B2 price and egress](https://www.backblaze.com/cloud-storage/pricing) · [Render Free limits](https://render.com/docs/free)

## Prerequisites and private inputs

| Owner provisions after approval | Inputs |
| --- | --- |
| DNS administrator and hosting operator | Separate hostname such as `staging.<owned-domain>`, A/optional AAAA records, approved tester source CIDRs, SSH public keys, region and budget. Serve only 80/443 publicly and restrict SSH to operator networks. Use direct DNS to Caddy so the access list evaluates the actual peer. |
| Database and broker operator | Fresh synthetic staging database, distinct administrator/migration/runtime credentials, and staging-only Valkey password/ACL. Inject `DATABASE_URL` and `RESOLVEFLOW_REDIS_URL` privately. |
| Google Auth Platform owner | Dedicated staging project and Web client, authorized domain, support contact, privacy policy, verification and **additional claims** enabled. Set the matching `RESOLVEFLOW_GOOGLE_CLIENT_ID`, `RESOLVEFLOW_GOOGLE_CLIENT_SECRET` and `RESOLVEFLOW_GOOGLE_REDIRECT_URI=https://staging.<owned-domain>/auth/google/callback`. Google documents that the app must be published and verified to receive additional claims. That Google setting is independent of application signup and the ingress allowlist. |
| Mail operator | Verified sender domain with SPF, DKIM and DMARC, sender address, SMTP login and SMTP key as `RESOLVEFLOW_SMTP_USERNAME` and `RESOLVEFLOW_SMTP_PASSWORD`, and approved test inboxes. Use authenticated STARTTLS on 587 and set `RESOLVEFLOW_EMAIL_DELIVERY=smtp` and the exact HTTPS origin only after verification. Hetzner permits 587 by default. |
| Recovery operator | Private ACL-scoped B2 upload and restore keys, Object Lock retention policy, separately escrowed Restic password, recovery encryption/signing keys and authenticated seal custody. Witness blocks on the app VM alone do not survive VM/account loss independently. Maintain a separate copy and recovery operator access. |

Use [api.env.example](../deploy/staging/api.env.example) and [web.env.example](../deploy/staging/web.env.example) as the complete application settings templates. Store filled files outside the checkout as root-owned mode `0600` files. The web process receives only its own environment. Record file hashes and binary versions in a private release manifest by name, with secrets excluded. [Google configuration and claims](https://developers.google.com/identity/siwg/security-bundle) · [OAuth protocol](https://developers.google.com/identity/openid-connect/openid-connect) · [Hetzner SMTP ports](https://docs.hetzner.com/cloud/servers/faq/) · [Object Lock](https://help.backblaze.com/hc/en-us/articles/360052973274-Object-Lock-FAQs)

## Reproduce the staging installation after approval

1. Prepare an approved source artifact from this worktree. The source currently includes uncommitted changes. Use its approved checksum plus both existing lockfiles. Install pinned Node 24, Python 3.14.6, uv, Caddy, Restic, PostgreSQL 18/pgvector, and Valkey on Linux. Verify package signatures or published checksums and record exact versions. Confirm locked dependencies and the CPU model fit the host. Keep two different filesystems for the journal and witness. Create private durable storage roots and mount the witness before accepting traffic. Use dedicated `resolveflow-staging` and `resolveflow-staging-web` service users. Make code and models read-only to runtime users and make the web user own only the Next.js cache.
2. From `/opt/resolveflow-staging/apps/api`, run `uv sync --locked --no-dev --python 3.14.6`. From `apps/web`, load the non-secret web environment and run `npm ci` then `npm run build -- --webpack`. Assign the externally verified baseline-v1 and MiniLM artifacts to the API template paths. Use `HF_HUB_OFFLINE=1` and leave live Gemini disabled. Validate classifier and embedding readiness with a synthetic offline ticket and indexing query.
3. Keep Postgres and Valkey on loopback, require SCRAM and authenticated Valkey access, and enable Valkey AOF with `appendfsync everysec`. Generate a random UUID for the staging database. Use the name `resolveflow_test_<32 lowercase hex characters>` and database comment `resolveflow-backup-staging-<same hex>`. An administrator installs `vector` before migration. Run `alembic upgrade 0017`, `alembic check` and `python scripts/workflows.py setup` as the migration owner. The runtime role needs connect, schema usage, table DML and sequence usage in `public` and `workflow_checkpoints` and grants for future objects from the migration owner. Keep role administration, extension installation, schema creation and backup administration with operators. Use fresh valkey keys and a distinct queue prefix. Verify Pg/Valkey are reachable only where intended.
4. Use a separate protected operator environment with migration/backup credentials for maintenance. Set `PYTHONPATH=/opt/resolveflow-staging/apps/api/src`. Run `python scripts/erasure_recovery.py initialize` once as the owner of the two empty mode `0700` journal roots after migration. Require correct marker, storage and fencing for future maintenance. Repeat the migration/backup check on disposable data before admitting testers.
5. Install the [service templates](../deploy/staging/) under systemd. Keep `STAGING_HOST` and `STAGING_TESTER_CIDRS` in Caddy's environment. The defaults resolve to a placeholder hostname and a documentation-only test subnet. Confirm the two services bind locally, then start `resolveflow-staging.target`. Keep the Caddy admin interface local and disable request access logs and full URL/query logging in monitoring. Run `caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile` with the intended environment, validate local readiness and dispatch, test both allowed and denied ingress, then admit only the approved network. The browser itself follows the OAuth redirect and inbox links from that network. Verify support for testers with changing IP addresses through a stable approved egress.
6. Keep production signup closed until every gate below is signed off. While no production account origin exists, adding a public full-mode deployment would expose registration, including account creation by Google. A future production deployment needs an explicit release approval and an independently verified signup control covering password registration and new Google identities before any public exposure. Step 6B installs no production code or routes.

The Caddyfile gives restricted same-origin access to the public API health response needed by the web landing page. Other browser API calls use Next.js. Direct API, database and Valkey ports remain private. [Caddy HTTPS](https://caddyserver.com/docs/automatic-https) · [Peer matching](https://caddyserver.com/docs/caddyfile/matchers#remote_ip) · [Next.js self-hosting](https://nextjs.org/docs/app/guides/self-hosting)

## Off-host recovery rehearsal

Use the [Linux recovery entry point](../deploy/staging/recovery.py) with the API virtualenv and operator environment. The regular backup CLI depends on local macOS tooling. This entry point reuses application guards and requires a loopback database with the exact disposable name/comment for its supplied UUID. Restic and PostgreSQL bin paths must resolve to real nonsymlink paths. Recovery stays quarantined.

```sh
python deploy/staging/recovery.py --state /var/lib/resolveflow-backup/control init \
  --repository /var/lib/resolveflow-backup/repository --restic /usr/bin/restic \
  --pg-bin /usr/lib/postgresql/18/bin
python deploy/staging/recovery.py --state /var/lib/resolveflow-backup/control capture \
  --database-id "$STAGING_DB_ID" --quiesced
python deploy/staging/recovery.py --state /var/lib/resolveflow-recovery/control restore \
  --database-id "$EMPTY_RESTORE_DB_ID" --snapshot "$SNAPSHOT_ID" \
  --expected-seal "$AUTHENTICATED_CURRENT_SEAL" --destination /var/lib/resolveflow-recovery/inspect
```

- Stop `resolveflow-staging.target` and any external writers, keep Postgres running, and capture with no other database clients. Test with an encrypted snapshot taken **before** deleting a disposable account.
- With writers still fenced after a deletion window, run `scripts/erasure_recovery.py current-seal` on the authoritative source. Use separate credentials to archive the quiesced encrypted Restic repository and sanitized recovery manifest to a private, versioned Object Lock bucket. Exclude the Restic password, PostgreSQL and OAuth secrets, and live operator environment. Separately encrypt and retain the two journal copies and the current seal. Have the recovery operator independently authenticate and record the latest epoch/seal, capture/repository identity, archive digest, retention and custody receipt. Keep escrowed recovery keys outside the VM and bucket.
- Copy the archived repository to a second isolated host using the read-only recovery credential. Verify the recorded digest, reproduce private `0600` Restic control configuration with that repository's recorded ID, and inject the separately retrieved encryption key. Prepare an empty disposable database with a different UUID/comment and installed PostgreSQL/pgvector binaries. Use a separate synthetic-only operator file targeting this database and the recovered witness copies. Follow the restore command above with the recorded pre-deletion snapshot and authenticated **current** deletion seal.
- Source loss after any deletion that lacks a verified, independently retained current seal remains fail-closed. Old, divergent, unavailable or incomplete records block recovery. A scheduled copy by itself cannot establish completeness. Keep the drill window bounded and keep restored databases isolated. See [deletion recovery and retention rules](BACKUP_OPERATIONS.md#account-deletion-recovery).

## Mandatory staging acceptance gates

| Gate | Run and record |
| --- | --- |
| Ingress and secrets | Allowed and denied networks against IPv4/IPv6; spoofed forwarded-IP header stays denied; cross-origin mutations rejected; ports closed; signed-out API protected; MFA for provider consoles, Secure/HttpOnly cookies; logs, browser bundles and traces exclude credentials, tokens, cookies and callback queries. |
| Email | New password registration, verification, sign-in/reset and subsequent revocation with a designated inbox; ensure stale/used links fail and SPF/DKIM/DMARC align. Verify the dispatcher and worker resume a queued delivery after restart. |
| Google | On the exact domain, test consent, cancel, callback and matching subject; staged inbox verification and subsequent sign-in; replay and superseded callback rejection; signed `auth_time` falling within the deletion ceremony; reused Google session, missing claim and wrong-account proof fail. Verify a successful fresh-sign-in path using disposable accounts within the ceremony window. Google does not force reauthentication. If the client cannot return usable freshness, this gate stays open. |
| Profile and sessions | Display name/avatar updates and two-inbox email change; password change and user-wide session revocation; verify a second browser cannot continue using an invalidated cookie. |
| Deletion and interrupted recovery | Password and Google accounts after valid proof, wrong/stale proof, shared-workspace last-owner refusal and retention of other members' data. Rehearse precommit retry and postcommit missing witness on a disposable database, verify idempotent cleanup and reject stale sessions, provider callbacks and queued jobs. Unknown private files stay held. |
| Off-host restoration | Retrieve archive + key with the source inaccessible. Verify checksums, the current seal, historical UUID history, private objects, unrelated account preservation and continued quarantine. Repeat with missing/stale witness or seal and verify refusal. Record restore time, recovery point and current seal evidence before sign-off. |
| Restart, isolation and capacity | Restart host/API/worker/broker with private staged fixtures. Confirm mail outbox, workflow checkpoints and queued jobs recover without duplicates. Check users in different workspaces cannot read or mutate each other's records or files. Record storage, peak RSS and latency for one concurrent indexing job plus login and retrieval. |

Record date, artifact digest, gate, operator and sanitized evidence per run. Current status for all hosted gates is **pending**. An approved budget/region, staging hostname, tester networks, Google claims, sender DNS/SMTP, off-host credentials and custody are external dependencies.
