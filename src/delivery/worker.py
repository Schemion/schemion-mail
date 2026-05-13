import asyncio
import logging

from src.core.config import settings
from src.delivery.smtp_client import deliver_message
from src.mail.repository import claim_emails_for_delivery
from src.mail.service import process_delivery_result


logger = logging.getLogger(__name__)


async def run_delivery_worker() -> None:
    logger.info("Delivery worker started")

    while True:
        try:
            emails = await asyncio.to_thread(
                claim_emails_for_delivery,
                settings.delivery_batch_size,
            )

            if not emails:
                await asyncio.sleep(settings.delivery_poll_interval_seconds)
                continue

            for email in emails:
                logger.info(
                    "Processing email id=%s from=%s to=%s attempt=%s/%s",
                    email.id,
                    email.mail_from,
                    email.rcpt_tos,
                    email.attempts,
                    email.max_attempts,
                )

                result = await asyncio.to_thread(
                    deliver_message,
                    email.mail_from,
                    email.rcpt_tos,
                    email.raw_message,
                )

                await asyncio.to_thread(
                    process_delivery_result,
                    email,
                    result,
                )

                if result.success:
                    logger.info(
                        "Email delivered id=%s mx=%s code=%s",
                        email.id,
                        result.mx_host,
                        result.smtp_code,
                    )
                else:
                    logger.warning(
                        "Email delivery failed id=%s temporary=%s error=%s",
                        email.id,
                        result.temporary,
                        result.error,
                    )

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception("Delivery worker iteration failed")
            await asyncio.sleep(settings.delivery_poll_interval_seconds)