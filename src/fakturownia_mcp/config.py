"""Environment-driven configuration and the shared API client instance."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from fakturownia_client import AsyncFakturowniaClient

ENV_DOMAIN = "FAKTUROWNIA_DOMAIN"
ENV_TOKEN = "FAKTUROWNIA_API_TOKEN"
ENV_TIMEOUT = "FAKTUROWNIA_TIMEOUT"
ENV_DOWNLOAD_DIR = "FAKTUROWNIA_DOWNLOAD_DIR"
ENV_SKIP_CONFIRM = "FAKTUROWNIA_SKIP_CONFIRM"

# Every variable also works with the INVOICEOCEAN_ prefix (international brand);
# the FAKTUROWNIA_ form wins when both are set.
_ENV_PREFIXES = ("FAKTUROWNIA_", "INVOICEOCEAN_")


def _env(suffix: str) -> str:
    for prefix in _ENV_PREFIXES:
        value = os.environ.get(prefix + suffix, "").strip()
        if value:
            return value
    return ""


class ConfigError(RuntimeError):
    """Raised when required environment variables are missing or invalid."""


_client: AsyncFakturowniaClient | None = None
_owned = False
_lock = asyncio.Lock()


def _build_client() -> AsyncFakturowniaClient:
    domain = _env("DOMAIN")
    token = _env("API_TOKEN")
    missing = [name for name, value in ((ENV_DOMAIN, domain), (ENV_TOKEN, token)) if not value]
    if missing:
        raise ConfigError(
            f"Missing environment variables: {', '.join(missing)}. Set {ENV_DOMAIN} "
            f"(account subdomain or full domain) and {ENV_TOKEN} (API authorization "
            "code from account settings, Integration section); the INVOICEOCEAN_ "
            "prefix works too. This is a server configuration problem the user must "
            "fix — do not retry the tool call."
        )
    raw_timeout = _env("TIMEOUT")
    try:
        timeout = float(raw_timeout) if raw_timeout else 30.0
    except ValueError as exc:
        raise ConfigError(
            f"{ENV_TIMEOUT} must be a number of seconds, got {raw_timeout!r}"
        ) from exc
    return AsyncFakturowniaClient(domain, token, timeout=timeout)


async def get_client() -> AsyncFakturowniaClient:
    """Return the process-wide async client, creating it from env vars on first use."""
    global _client, _owned
    if _client is None:
        async with _lock:
            if _client is None:
                _client = _build_client()
                _owned = True
    return _client


def set_client(client: AsyncFakturowniaClient | None) -> None:
    """Inject a client instance (used by tests); its lifecycle stays with the caller."""
    global _client, _owned
    _client = client
    _owned = False


async def aclose_client() -> None:
    """Close the shared client if this module created it (server lifespan hook)."""
    global _client, _owned
    if _client is not None and _owned:
        await _client.close()
        _client = None
        _owned = False


def download_dir() -> Path:
    """Directory PDF downloads are confined to (default: ~/Downloads)."""
    return Path(_env("DOWNLOAD_DIR") or "~/Downloads").expanduser()


def skip_confirm() -> bool:
    return _env("SKIP_CONFIRM") == "1"
