"""Translate client-library exceptions into agent-steering tool errors."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import TypeVar

from fakturownia_client import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    TransportError,
    ValidationError,
)
from mcp.server.fastmcp.exceptions import ToolError

T = TypeVar("T")

_DEFAULT_NOT_FOUND = (
    "That id does not exist. Ids come from the corresponding list_* tool "
    "(the numeric 'id' field) — they are NOT invoice/document numbers like '15/2025'."
)


async def api_call(operation: Awaitable[T], *, not_found: str | None = None) -> T:
    """Await a fakturownia-client call, rephrasing failures so the agent can recover."""
    try:
        return await operation
    except NotFoundError as exc:
        raise ToolError(f"{exc} — {not_found or _DEFAULT_NOT_FOUND}") from exc
    except ValidationError as exc:
        raise ToolError(
            f"{exc} — the API rejected the payload. Field names must be Fakturownia "
            "API names (snake_case, e.g. buyer_name, price_net). Fix the named field "
            "and retry once; if unclear, show the error to the user."
        ) from exc
    except AuthenticationError as exc:
        raise ToolError(
            f"{exc} — the configured FAKTUROWNIA_DOMAIN or FAKTUROWNIA_API_TOKEN is "
            "wrong. This is a server configuration problem; ask the user to fix it. "
            "Do not retry."
        ) from exc
    except RateLimitError as exc:
        raise ToolError(
            f"{exc} — still rate-limited after automatic retries. Wait before calling "
            "Fakturownia tools again; do not retry immediately."
        ) from exc
    except TransportError as exc:
        raise ToolError(
            f"{exc} — network problem reaching Fakturownia. Retry once; if it "
            "persists, report it to the user."
        ) from exc
