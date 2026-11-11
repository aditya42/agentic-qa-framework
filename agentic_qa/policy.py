"""Deterministic target policy for untrusted generated browser tests."""
import os
from urllib.parse import urlparse

def validate_target(target: str, allowed_hosts: str | None = None) -> str:
    parsed = urlparse(target)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("BASE_URL must be an HTTPS URL without embedded credentials")
    if parsed.port not in (None, 443):
        raise ValueError("Nonstandard HTTPS ports require a reviewed policy change")
    if parsed.query or parsed.fragment:
        raise ValueError("BASE_URL must not include query parameters or fragments")
    hosts = allowed_hosts if allowed_hosts is not None else os.getenv("QA_ALLOWED_HOSTS", "")
    approved = {host.strip().lower() for host in hosts.split(",") if host.strip()}
    if not approved:
        raise ValueError("QA_ALLOWED_HOSTS must explicitly list approved test hosts")
    if parsed.hostname.lower() not in approved:
        raise ValueError("BASE_URL host is not approved by QA_ALLOWED_HOSTS")
    return target
