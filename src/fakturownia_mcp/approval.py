"""Approval gate for write operations, based on MCP elicitation.

Every tool that mutates Fakturownia data asks the user to confirm first via
``ctx.elicit()`` — clients with elicitation support (Claude Code, Claude
Desktop, MCP Inspector) show a native approval dialog describing the exact
operation, including the values being written. Set
``FAKTUROWNIA_SKIP_CONFIRM=1`` to disable the gate for trusted automation.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context
from mcp.types import ClientCapabilities, ElicitationCapability
from pydantic import BaseModel, Field

from fakturownia_mcp import config


class WriteConfirmation(BaseModel):
    confirm: bool = Field(default=False, description="Confirm executing this write operation")


class ApprovalDenied(Exception):
    """Raised when the user declines (or cannot be asked) — surfaces as a tool error."""


def format_fields(fields: dict[str, Any], *, max_value: int = 80, max_total: int = 500) -> str:
    """Render field=value pairs so the user sees WHAT is being written."""
    parts = []
    for key, value in fields.items():
        text = repr(value)
        if len(text) > max_value:
            text = text[: max_value - 1] + "…"
        parts.append(f"{key}={text}")
    rendered = ", ".join(parts)
    return rendered if len(rendered) <= max_total else rendered[: max_total - 1] + "…"


async def require_approval(ctx: Context, summary: str) -> None:  # type: ignore[type-arg]
    """Return silently when approved; raise :class:`ApprovalDenied` otherwise."""
    if config.skip_confirm():
        return
    supports_elicitation = ctx.session.check_client_capability(
        ClientCapabilities(elicitation=ElicitationCapability())
    )
    if not supports_elicitation:
        raise ApprovalDenied(
            f"Cannot ask the user to approve: {summary}. The connected MCP client does "
            "not support elicitation. Ask the user to confirm in conversation and, if "
            f"they trust this setup, to set {config.ENV_SKIP_CONFIRM}=1 in the server env."
        )
    result = await ctx.elicit(
        message=f"Fakturownia — approve write operation?\n{summary}",
        schema=WriteConfirmation,
    )
    if result.action == "accept" and result.data.confirm:
        return
    raise ApprovalDenied(
        f"The user did not approve this operation: {summary}. Do not retry it — "
        "tell the user it was cancelled and ask how they want to proceed."
    )
