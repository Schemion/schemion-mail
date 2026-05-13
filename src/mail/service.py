from src.delivery.retry import calculate_next_attempt_at
from src.delivery.smtp_client import DeliveryResult
from src.mail.models import MailOutbox
from src.mail.repository import (
    create_delivery_attempt,
    enqueue_mail,
    mark_email_failed,
    mark_email_retry,
    mark_email_sent,
)
from src.mail.templates import build_confirmation_card_message


def enqueue_incoming_smtp_message(
    mail_from: str,
    rcpt_tos: list[str],
    raw_message: bytes,
) -> int:
    formatted_message = build_confirmation_card_message(raw_message)

    return enqueue_mail(
        mail_from=mail_from,
        rcpt_tos=rcpt_tos,
        raw_message=formatted_message,
    )


def process_delivery_result(email: MailOutbox, result: DeliveryResult) -> None:
    create_delivery_attempt(
        email_id=email.id,
        mx_host=result.mx_host,
        smtp_code=result.smtp_code,
        smtp_response=result.smtp_response,
        success=result.success,
        error=result.error,
    )

    if result.success:
        mark_email_sent(email.id)
        return

    error_message = result.error or "Unknown delivery error"

    if result.temporary and email.attempts < email.max_attempts:
        mark_email_retry(
            email_id=email.id,
            error_message=error_message,
            next_attempt_at=calculate_next_attempt_at(email.attempts),
        )
        return

    mark_email_failed(
        email_id=email.id,
        error_message=error_message,
    )
