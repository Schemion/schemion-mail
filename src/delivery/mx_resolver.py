from email.utils import parseaddr
import logging

import dns.resolver

from src.core.config import settings


logger = logging.getLogger(__name__)


def extract_domain(email: str) -> str:
    _, addr = parseaddr(email)

    if "@" not in addr:
        raise ValueError(f"Invalid email address: {email}")

    return addr.rsplit("@", 1)[1].lower()


def build_resolver() -> dns.resolver.Resolver:
    resolver = dns.resolver.Resolver(configure=False)

    nameservers = [
        item.strip()
        for item in settings.dns_nameservers.split(",")
        if item.strip()
    ]

    if not nameservers:
        nameservers = ["1.1.1.1", "8.8.8.8"]

    resolver.nameservers = nameservers
    resolver.timeout = 5
    resolver.lifetime = 10

    return resolver


def resolve_mx_hosts(domain: str) -> list[str]:
    resolver = build_resolver()

    try:
        answers = resolver.resolve(domain, "MX")

        records = sorted(
            [
                (
                    int(record.preference),
                    str(record.exchange).rstrip("."),
                )
                for record in answers
            ],
            key=lambda item: item[0],
        )

        mx_hosts = [host for _, host in records]

        logger.info("Resolved MX domain=%s hosts=%s", domain, mx_hosts)

        return mx_hosts

    except dns.resolver.NXDOMAIN:
        logger.warning("Domain does not exist: %s", domain)
        return []

    except dns.resolver.NoAnswer:
        logger.warning("No MX records for domain=%s, fallback to domain", domain)
        return [domain]

    except dns.resolver.NoNameservers as exc:
        logger.warning("No nameservers could resolve domain=%s error=%s", domain, exc)
        return []

    except dns.resolver.LifetimeTimeout as exc:
        logger.warning("DNS lookup timeout domain=%s error=%s", domain, exc)
        return []

    except Exception as exc:
        logger.warning("DNS lookup failed domain=%s error=%s", domain, exc)
        return []