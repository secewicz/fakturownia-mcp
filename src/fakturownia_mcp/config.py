"""Environment-driven configuration and the shared API client instance."""

from __future__ import annotations

import os

from fakturownia_client import AsyncFakturowniaClient

ENV_DOMAIN = "FAKTUROWNIA_DOMAIN"
ENV_TOKEN = "FAKTUROWNIA_API_TOKEN"


class ConfigError(RuntimeError):
    """Raised when required environment variables are missing."""


_client: AsyncFakturowniaClient | None = None


def get_client() -> AsyncFakturowniaClient:
    """Return the process-wide async client, creating it from env vars on first use."""
    global _client
    if _client is None:
        domain = os.environ.get(ENV_DOMAIN, "").strip()
        token = os.environ.get(ENV_TOKEN, "").strip()
        missing = [name for name, value in ((ENV_DOMAIN, domain), (ENV_TOKEN, token)) if not value]
        if missing:
            raise ConfigError(
                f"Missing environment variables: {', '.join(missing)}. "
                "Set FAKTUROWNIA_DOMAIN (your account subdomain) and "
                "FAKTUROWNIA_API_TOKEN (Ustawienia -> Ustawienia konta -> Integracja)."
            )
        _client = AsyncFakturowniaClient(domain, token)
    return _client


def set_client(client: AsyncFakturowniaClient | None) -> None:
    """Inject a client instance (used by tests)."""
    global _client
    _client = client
