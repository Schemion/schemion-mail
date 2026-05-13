import asyncio
import logging

from src.core.logging import setup_logging
from src.persistence.session import check_db_connection
from src.delivery.worker import run_delivery_worker
from src.smtp.server import run_smtp_server


logger = logging.getLogger(__name__)


async def main() -> None:
    setup_logging()

    logger.info("Starting schemion-mail service")

    if not check_db_connection():
        raise RuntimeError("Database connection failed")

    logger.info("Database connection OK")

    smtp_task = asyncio.create_task(
        run_smtp_server(),
        name="smtp-server",
    )

    delivery_task = asyncio.create_task(
        run_delivery_worker(),
        name="delivery-worker",
    )

    tasks = {
        smtp_task,
        delivery_task,
    }

    done, pending = await asyncio.wait(
        tasks,
        return_when=asyncio.FIRST_EXCEPTION,
    )

    for task in done:
        exception = task.exception()

        if exception is not None:
            logger.exception(
                "Task %s failed",
                task.get_name(),
                exc_info=exception,
            )

    for task in pending:
        task.cancel()

    await asyncio.gather(
        *pending,
        return_exceptions=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
