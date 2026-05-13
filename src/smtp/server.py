import asyncio
import logging

from src.core.config import settings
from src.smtp.protocol import handle_client


logger = logging.getLogger(__name__)


async def run_smtp_server() -> None:
    server = await asyncio.start_server(
        handle_client,
        host=settings.smtp_bind_host,
        port=settings.smtp_bind_port,
    )

    logger.info(
        "SMTP server started on %s:%s",
        settings.smtp_bind_host,
        settings.smtp_bind_port,
    )

    async with server:
        await server.serve_forever()