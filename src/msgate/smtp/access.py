"""IP allowlist helpers for anonymous SMTP relay."""

from __future__ import annotations

import ipaddress


def ip_allowed(client_ip: str, allowed: list[str]) -> bool:
    """Return True if client_ip matches any host or CIDR in allowed."""
    try:
        addr = ipaddress.ip_address(client_ip)
    except ValueError:
        return False

    for entry in allowed:
        entry = entry.strip()
        if not entry:
            continue
        try:
            if "/" in entry:
                if addr in ipaddress.ip_network(entry, strict=False):
                    return True
            elif addr == ipaddress.ip_address(entry):
                return True
        except ValueError:
            continue
    return False
