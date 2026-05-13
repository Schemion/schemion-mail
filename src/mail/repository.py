from datetime import datetime, timezone

from sqlalchemy import select

from src.mail.enums import MailStatus
from src.mail.models import MailDeliveryAttempt, MailOutbox
from src.persistence.session import get_db_session


class MailRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory
        
    def _utcnow(self):
        return datetime.now(timezone.utc)
    
    def enqueue_mail(self, mail_from: str, rcpt_tos: list[str], raw_message: bytes) -> int:
        with self.session_factory() as session:
            email = MailOutbox()
            email.mail_from = mail_from
            email.rcpt_tos = rcpt_tos
            email.raw_message = raw_message
            email.status = MailStatus.QUEUED.value
            session.add(email)
            session.flush()

            return int(email.id)

    def claim_mail_for_delivery(self, batch_size: int) -> list[MailOutbox]:
        now = self._utcnow()

        with self.session_factory() as session:
            stmt = (
                select(MailOutbox).where(
                    MailOutbox.status.in_([MailStatus.QUEUED.value, MailStatus.RETRY.value]),
                    MailOutbox.next_attempt_at <= now,
                    MailOutbox.attempts < MailOutbox.max_attempts,
                ).order_by(MailOutbox.id.asc()).limit(batch_size).with_for_update(skip_locked=True)
            )

            emails = list(session.scalars(stmt).all())

            for email in emails:
                email.status = MailStatus.SENDING.value
                email.attempts += 1
                email.updated_at = now

            session.flush()
            return emails
    
    def mark_email_sent(self, email_id: int) -> None:
        now = self._utcnow()

        with self.session_factory() as session:
            email = session.get(MailOutbox, email_id)
            if email:
                email.status = MailStatus.SENT.value
                email.sent_at = now
                email.updated_at = now
                email.last_error = None


    def mark_email_retry(self, email_id: int, error_message: str, next_attempt_at: datetime) -> None:
        now = self._utcnow()

        with self.session_factory() as session:
            email = session.get(MailOutbox, email_id)
            if email:
                email.status = MailStatus.RETRY.value
                email.next_attempt_at = next_attempt_at
                email.updated_at = now
                email.last_error = error_message[:2000]

    def mark_email_failed(self, email_id: int, error_message: str) -> None:
        now = self._utcnow()

        with self.session_factory() as session:
            email = session.get(MailOutbox, email_id)
            if email:
                email.status = MailStatus.FAILED.value
                email.updated_at = now
                email.last_error = error_message[:2000]

    def create_delivery_attempt(self, email_id: int, mx_host: str | None,
                                smtp_code: int | None, smtp_response: str | None,
                                error: str | None, success: bool) -> None:
        
        with self.session_factory() as session:
            attempt = MailDeliveryAttempt()
            attempt.email_id = email_id
            attempt.mx_host = mx_host
            attempt.smtp_code = smtp_code
            attempt.smtp_response = smtp_response
            attempt.error = error[:2000] if error else None
            attempt.success = success

            session.add(attempt)


mail_repository = MailRepository(get_db_session)


def enqueue_mail(mail_from: str, rcpt_tos: list[str], raw_message: bytes) -> int:
    return mail_repository.enqueue_mail(
        mail_from=mail_from,
        rcpt_tos=rcpt_tos,
        raw_message=raw_message,
    )


def claim_emails_for_delivery(batch_size: int) -> list[MailOutbox]:
    return mail_repository.claim_mail_for_delivery(batch_size=batch_size)


def mark_email_sent(email_id: int) -> None:
    mail_repository.mark_email_sent(email_id=email_id)


def mark_email_retry(email_id: int, error_message: str, next_attempt_at: datetime) -> None:
    mail_repository.mark_email_retry(
        email_id=email_id,
        error_message=error_message,
        next_attempt_at=next_attempt_at,
    )


def mark_email_failed(email_id: int, error_message: str) -> None:
    mail_repository.mark_email_failed(
        email_id=email_id,
        error_message=error_message,
    )


def create_delivery_attempt(
    email_id: int,
    mx_host: str | None,
    smtp_code: int | None,
    smtp_response: str | None,
    error: str | None,
    success: bool,
) -> None:
    mail_repository.create_delivery_attempt(
        email_id=email_id,
        mx_host=mx_host,
        smtp_code=smtp_code,
        smtp_response=smtp_response,
        error=error,
        success=success,
    )
