"""Provider-independent identity email contract; SMTP details stay in this adapter."""

import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol


@dataclass(frozen=True)
class DeliveryResult:
    accepted: bool
    code: str | None = None
    retryable: bool = False


class EmailDelivery(Protocol):
    def send_verification(self, recipient: str, link: str, message_id: str) -> DeliveryResult: ...
    def send_recovery(self, recipient: str, link: str, message_id: str) -> DeliveryResult: ...


class SmtpEmailDelivery:
    def __init__(self, settings):
        self.settings = settings

    def send_verification(self, recipient, link, message_id):
        return self._send(
            recipient,
            link,
            message_id,
            "Verify your ResolveFlow email",
            "Confirm your email address",
        )

    def send_recovery(self, recipient, link, message_id):
        return self._send(
            recipient, link, message_id, "Reset your ResolveFlow password", "Choose a new password"
        )

    def _send(self, recipient, link, message_id, subject, action):
        config = self.settings
        if config.email_delivery == "disabled":
            return DeliveryResult(False, "delivery_disabled")
        message = EmailMessage()
        message["From"] = config.email_from
        message["To"] = recipient
        message["Subject"] = subject
        message["Message-ID"] = f"<{message_id}@resolveflow.invalid>"
        message.set_content(
            f"{action}:\n\n{link}\n\nThis link expires and works once. "
            "If you did not request it, ignore this email.\n"
        )
        client = None
        try:
            context = ssl.create_default_context()
            if config.smtp_tls == "ssl":
                client = smtplib.SMTP_SSL(
                    config.smtp_host,
                    config.smtp_port,
                    timeout=config.smtp_timeout_seconds,
                    context=context,
                )
            else:
                client = smtplib.SMTP(
                    config.smtp_host, config.smtp_port, timeout=config.smtp_timeout_seconds
                )
                if config.smtp_tls == "starttls":
                    client.starttls(context=context)
            if config.email_delivery == "smtp":
                client.login(config.smtp_username, config.smtp_password.get_secret_value())
            refused = client.send_message(message)
            return DeliveryResult(not refused, "recipient_rejected" if refused else None)
        except smtplib.SMTPAuthenticationError:
            return DeliveryResult(False, "smtp_authentication")
        except smtplib.SMTPResponseException as exc:
            return DeliveryResult(False, "smtp_rejected", 400 <= exc.smtp_code < 500)
        except OSError, smtplib.SMTPException:
            return DeliveryResult(False, "smtp_unavailable", True)
        finally:
            # A failed QUIT after DATA acceptance must not cause an unnecessary retry.
            if client is not None:
                client.close()
