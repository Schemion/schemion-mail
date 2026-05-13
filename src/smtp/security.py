import ipaddress

from src.core.config import settings


def is_client_allowed(ip: str) -> bool:
    try:
        client_ip = ipaddress.ip_address(ip)
    except ValueError:
        return False

    for raw_network in settings.smtp_allowed_networks.split(","):
        raw_network = raw_network.strip()

        if not raw_network:
            continue

        network = ipaddress.ip_network(raw_network, strict=False)

        if client_ip in network:
            return True

    return False