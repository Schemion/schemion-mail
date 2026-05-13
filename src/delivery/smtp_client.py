from collections import defaultdict
from dataclasses import dataclass
import logging
import smtplib
import ssl

from src.core.config import settings
from src.delivery.mx_resolver import extract_domain, resolve_mx_hosts
from src.delivery.retry import is_temporary_smtp_code


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeliveryResult:
    success: bool
    temporary: bool
    mx_host: str | None = None
    smtp_code: int | None = None
    smtp_response: str | None = None
    error: str | None = None


def decode_response(response: bytes | str | None) -> str | None:
    if response is None:
        return None

    if isinstance(response, bytes):
        return response.decode("utf-8", errors="replace")

    return str(response)


def deliver_message(
    mail_from: str,
    rcpt_tos: list[str],
    raw_message: bytes,
) -> DeliveryResult:
    recipients_by_domain: dict[str, list[str]] = defaultdict(list)

    for rcpt in rcpt_tos:
        domain = extract_domain(rcpt)
        recipients_by_domain[domain].append(rcpt)

    last_result: DeliveryResult | None = None

    for domain, domain_recipients in recipients_by_domain.items():
        result = deliver_to_domain(
            domain=domain,
            mail_from=mail_from,
            rcpt_tos=domain_recipients,
            raw_message=raw_message,
        )

        if not result.success:
            return result

        last_result = result

    return last_result or DeliveryResult(
        success=False,
        temporary=False,
        error="No recipients",
    )


def deliver_to_domain(
    domain: str,
    mail_from: str,
    rcpt_tos: list[str],
    raw_message: bytes,
) -> DeliveryResult:
    mx_hosts = resolve_mx_hosts(domain)

    last_error: str | None = None

    for mx_host in mx_hosts:
        logger.info("Trying MX %s for domain %s", mx_host, domain)

        try:
            return deliver_to_mx(
                mx_host=mx_host,
                mail_from=mail_from,
                rcpt_tos=rcpt_tos,
                raw_message=raw_message,
            )

        except smtplib.SMTPResponseException as exc:
            code = int(exc.smtp_code)
            response = decode_response(exc.smtp_error)

            last_error = f"SMTP error {code}: {response}"

            logger.warning(
                "SMTP response error via mx=%s code=%s response=%s",
                mx_host,
                code,
                response,
            )

            if is_temporary_smtp_code(code):
                continue

            return DeliveryResult(
                success=False,
                temporary=False,
                mx_host=mx_host,
                smtp_code=code,
                smtp_response=response,
                error=last_error,
            )

        except Exception as exc:
            last_error = str(exc)

            logger.warning(
                "Delivery attempt failed via mx=%s error=%s",
                mx_host,
                exc,
            )

            continue

    return DeliveryResult(
        success=False,
        temporary=True,
        mx_host=mx_hosts[-1] if mx_hosts else None,
        error=last_error or "All MX hosts failed",
    )


def deliver_to_mx(
    mx_host: str,
    mail_from: str,
    rcpt_tos: list[str],
    raw_message: bytes,
) -> DeliveryResult:
    with smtplib.SMTP(
        host=mx_host,
        port=25,
        timeout=settings.delivery_timeout_seconds,
        local_hostname=settings.smtp_hostname,
    ) as smtp:
        smtp.ehlo_or_helo_if_needed()

        if smtp.has_extn("STARTTLS"):
            context = ssl.create_default_context()
            smtp.starttls(context=context)
            smtp.ehlo()

        code, response = smtp.mail(mail_from)

        if code >= 400:
            raise smtplib.SMTPResponseException(code, response)

        accepted_recipients: list[str] = []
        last_rcpt_code: int | None = None
        last_rcpt_response: str | None = None

        for rcpt in rcpt_tos:
            code, response = smtp.rcpt(rcpt)
            last_rcpt_code = code
            last_rcpt_response = decode_response(response)

            if code < 400:
                accepted_recipients.append(rcpt)
            else:
                logger.warning(
                    "Recipient rejected rcpt=%s code=%s response=%s",
                    rcpt,
                    code,
                    last_rcpt_response,
                )

        if not accepted_recipients:
            return DeliveryResult(
                success=False,
                temporary=is_temporary_smtp_code(last_rcpt_code),
                mx_host=mx_host,
                smtp_code=last_rcpt_code,
                smtp_response=last_rcpt_response,
                error="No recipients accepted by remote MX",
            )

        code, response = smtp.data(raw_message)
        response_text = decode_response(response)

        if code >= 400:
            return DeliveryResult(
                success=False,
                temporary=is_temporary_smtp_code(code),
                mx_host=mx_host,
                smtp_code=code,
                smtp_response=response_text,
                error=f"DATA rejected: {code} {response_text}",
            )

        return DeliveryResult(
            success=True,
            temporary=False,
            mx_host=mx_host,
            smtp_code=code,
            smtp_response=response_text,
            error=None,
        )