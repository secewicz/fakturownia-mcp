"""Approval gate for write operations, based on MCP elicitation.

Every tool that mutates Fakturownia data asks the client to confirm first via
``ctx.elicit()`` — clients with elicitation support (Claude Code, Claude
Desktop, MCP Inspector) show a native approval dialog. Set
``FAKTUROWNIA_SKIP_CONFIRM=1`` to disable the gate, e.g. for automation or
clients without elicitation support.
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import Context
from pydantic import BaseModel, Field

SKIP_ENV = "FAKTUROWNIA_SKIP_CONFIRM"


class WriteConfirmation(BaseModel):
    confirm: bool = Field(default=False, description="Confirm executing this write operation")


class ApprovalDenied(Exception):
    """Raised when the user declines (or cannot be asked) — surfaces as a tool error."""


async def require_approval(ctx: Context, summary: str) -> None:  # type: ignore[type-arg]
    """Return silently when approved; raise :class:`ApprovalDenied` otherwise."""
    if os.environ.get(SKIP_ENV, "").strip() == "1":
        return
    try:
        result = await ctx.elicit(
            message=f"Fakturownia — approve write operation?\n{summary}",
            schema=WriteConfirmation,
        )
    except Exception as exc:
        raise ApprovalDenied(
            f"Could not ask for approval of: {summary}. The MCP client likely lacks "
            f"elicitation support; set {SKIP_ENV}=1 in the server env to disable the gate."
        ) from exc
    if result.action == "accept" and result.data.confirm:
        return
    raise ApprovalDenied(f"Write operation was not approved by the user: {summary}")
