from datetime import datetime, timedelta, timezone

from src.core.config import settings


def calculate_next_attempt_at(attempts: int) -> datetime:
    delays = [
        settings.delivery_retry_base_seconds,
        settings.delivery_retry_base_seconds * 5,
        settings.delivery_retry_base_seconds * 15,
        settings.delivery_retry_base_seconds * 60,
    ]

    index = max(0, min(attempts - 1, len(delays) - 1))
    delay_seconds = delays[index]

    return datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)


def is_temporary_smtp_code(code: int | None) -> bool:
    if code is None:
        return True

    return 400 <= code < 500


def is_permanent_smtp_code(code: int | None) -> bool:
    if code is None:
        return False

    return code >= 500