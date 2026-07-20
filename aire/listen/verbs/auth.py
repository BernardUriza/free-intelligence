"""Verb gate: constant-time token check + IP validation."""

import ipaddress
import secrets

from ..config import VERB_TOKEN


def token_ok(token: str) -> bool:
    return bool(VERB_TOKEN) and secrets.compare_digest(token, VERB_TOKEN)


def valid_ip(ip: str) -> bool:
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False
