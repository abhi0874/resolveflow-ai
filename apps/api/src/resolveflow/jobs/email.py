"""Hash-only email outbox via the existing RQ queue. Queue payloads are UUIDs only."""

import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select

from resolveflow.core.config import Settings
from resolveflow.db.models import AccountStatus, IdentityEmail, User
from resolveflow.db.session import Database
from resolveflow.jobs.transport import connection, queue
from resolveflow.services.auth import digest, email_proven
from resolveflow.services.email_delivery import SmtpEmailDelivery


def publish(database, settings):
    if settings.email_delivery == "disabled":
        return 0
    count = 0
    with database.sessions() as db, connection(settings) as broker:
        now = datetime.now(UTC)
        rows = db.scalars(
            select(IdentityEmail)
            .where(
                IdentityEmail.status.in_(["pending", "sending"]),
                IdentityEmail.available_at <= now,
                or_(
                    IdentityEmail.last_enqueued_at.is_(None),
                    IdentityEmail.last_enqueued_at < now - timedelta(seconds=60),
                ),
            )
            .order_by(IdentityEmail.available_at)
            .limit(20)
            .with_for_update(skip_locked=True)
        ).all()
        transport = queue(settings, broker)
        for row in rows:
            if row.invalidated_at or row.consumed_at or row.expires_at <= now or row.attempts >= 3:
                row.status = "failed" if row.attempts >= 3 else "cancelled"
                row.error_code = "attempts_exhausted" if row.attempts >= 3 else "link_inactive"
                continue
            if transport.count >= settings.job_queue_capacity:
                break
            transport.enqueue(
                "resolveflow.jobs.email.execute",
                str(row.id),
                job_id="email-" + uuid.uuid4().hex,
                job_timeout=45,
                result_ttl=0,
                failure_ttl=0,
            )
            # A crash between enqueue and commit can duplicate a UUID, not a delivery.
            row.last_enqueued_at = now
            count += 1
        db.commit()
    return count


def process(database, settings, identity, delivery=None):
    # Claim under row lock; concurrent/duplicate messages cannot send within the lease.
    with database.sessions() as db:
        row = db.scalar(select(IdentityEmail).where(IdentityEmail.id == identity).with_for_update())
        now = datetime.now(UTC)
        if not row or row.status not in {"pending", "sending"} or row.available_at > now:
            return
        user = db.get(User, row.user_id)
        if (
            row.invalidated_at
            or row.consumed_at
            or row.expires_at <= now
            or row.attempts >= 3
            or not user
            or user.account_status != AccountStatus.ACTIVE
            or user.email != row.email
            or user.credential_version != row.credential_version
            or (row.purpose == "verify" and email_proven(settings, user))
        ):
            row.status = "failed" if row.attempts >= 3 else "cancelled"
            row.error_code = "attempts_exhausted" if row.attempts >= 3 else "link_inactive"
            db.commit()
            return
        token = secrets.token_urlsafe(32)
        row.token_hash = digest(token)
        row.attempts += 1
        attempt = row.attempts
        row.status = "sending"
        row.available_at = now + timedelta(seconds=120)
        row.delivery_source = settings.email_delivery
        recipient, purpose = row.email, row.purpose
        db.commit()
    adapter = delivery or SmtpEmailDelivery(settings)
    page = "verify-email" if purpose == "verify" else "reset-password"
    # Fragments never reach HTTP access logs, proxy requests or Referer headers.
    link = settings.email_public_origin.rstrip("/") + "/" + page + "#token=" + token
    try:
        send = adapter.send_verification if purpose == "verify" else adapter.send_recovery
        result = send(recipient, link, str(identity))
    except Exception:
        from resolveflow.services.email_delivery import DeliveryResult

        result = DeliveryResult(False, "delivery_unavailable", True)
    with database.sessions() as db:
        row = db.scalar(select(IdentityEmail).where(IdentityEmail.id == identity).with_for_update())
        if row and row.attempts == attempt and row.status == "sending":
            row.status = (
                "sent"
                if result.accepted
                else ("pending" if result.retryable and attempt < 3 else "failed")
            )
            row.error_code = result.code
            row.available_at = datetime.now(UTC) + timedelta(seconds=30 * 2**attempt)
            db.commit()
    logging.getLogger("resolveflow.email").info(
        "identity_email_processed id=%s accepted=%s attempt=%d", identity, result.accepted, attempt
    )


def execute(identifier: str):
    database = None
    try:
        identity = uuid.UUID(identifier)
        settings = Settings()
        database = Database(settings)
        process(database, settings, identity)
    except Exception:
        # Never put SMTP errors, addresses, tokens or credentials into RQ exception storage.
        logging.getLogger("resolveflow.email").warning(
            "identity_email_deferred infrastructure_unavailable"
        )
    finally:
        if database:
            database.dispose()
