from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


def get_int(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None or value == "":
        return default

    return int(value)


def get_str(name: str, default: str) -> str:
    return os.getenv(name, default)


@dataclass(frozen=True)
class Settings:
    database_url: str = get_str("DATABASE_URL", "postgresql+psycopg://admin:admin@database:5432/schemion")
    smtp_hostname: str = get_str("SMTP_HOSTNAME", "schemion-mail.local")
    smtp_bind_host: str = get_str("SMTP_BIND_HOST", "0.0.0.0")
    smtp_bind_port: int = get_int("SMTP_BIND_PORT", 1025)

    smtp_allowed_networks: str = get_str(
        "SMTP_ALLOWED_NETWORKS",
        "127.0.0.1/32,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16",
    )
    dns_nameservers: str = get_str(
        "DNS_NAMESERVERS",
        "1.1.1.1,8.8.8.8",
    )

    smtp_max_message_bytes: int = get_int("SMTP_MAX_MESSAGE_BYTES", 512 * 1024)
    delivery_batch_size: int = get_int("DELIVERY_BATCH_SIZE", 10)
    delivery_poll_interval_seconds: int = get_int("DELIVERY_POLL_INTERVAL_SECONDS", 5)
    delivery_timeout_seconds: int = get_int("DELIVERY_TIMEOUT_SECONDS", 30)
    delivery_retry_base_seconds: int = get_int("DELIVERY_RETRY_BASE_SECONDS", 60)

settings = Settings()
