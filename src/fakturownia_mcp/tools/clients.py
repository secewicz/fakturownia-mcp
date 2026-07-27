"""Client (contractor) tools."""

from __future__ import annotations

from typing import Any

from fakturownia_client.models import Client
from mcp.server.fastmcp import Context, FastMCP

from fakturownia_mcp import config
from fakturownia_mcp.approval import require_approval


def _summary(client: Client) -> dict[str, Any]:
    return {
        "id": client.id,
        "name": client.name,
        "tax_no": client.tax_no,
        "email": client.email,
        "city": client.city,
        "external_id": client.external_id,
    }


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_clients(
        name: str | None = None,
        tax_no: str | None = None,
        email: str | None = None,
        page: int = 1,
        per_page: int = 25,
    ) -> dict[str, Any]:
        """List/search clients (contractors). Returns summaries; use get_client for details."""
        clients = await config.get_client().list_clients(
            name=name, tax_no=tax_no, email=email, page=page, per_page=per_page
        )
        return {
            "clients": [_summary(c) for c in clients],
            "page": page,
            "has_more": len(clients) == per_page,
        }

    @mcp.tool()
    async def get_client(client_id: int) -> dict[str, Any]:
        """Get full client details."""
        client = await config.get_client().get_client(client_id)
        return client.model_dump(mode="json", exclude_none=True)

    @mcp.tool()
    async def create_client(
        name: str,
        tax_no: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        street: str | None = None,
        city: str | None = None,
        post_code: str | None = None,
        country: str | None = None,
        company: bool = True,
        *,
        ctx: Context,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Create a client (contractor)."""
        await require_approval(ctx, f"create client '{name}'")
        payload: dict[str, Any] = {
            "name": name,
            "tax_no": tax_no,
            "email": email,
            "phone": phone,
            "street": street,
            "city": city,
            "post_code": post_code,
            "country": country,
            "company": company,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        client = await config.get_client().create_client(payload)
        return client.model_dump(mode="json", exclude_none=True)

    @mcp.tool()
    async def update_client(
        client_id: int,
        fields: dict[str, Any],
        *,
        ctx: Context,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Update selected fields of a client, e.g. {"email": "x@y.pl"}."""
        await require_approval(
            ctx, f"update client {client_id}, fields: {', '.join(sorted(fields))}"
        )
        client = await config.get_client().update_client(client_id, fields)
        return client.model_dump(mode="json", exclude_none=True)

    @mcp.tool()
    async def delete_client(
        client_id: int,
        *,
        ctx: Context,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Delete a client (contractor). Irreversible."""
        await require_approval(ctx, f"DELETE client {client_id} (irreversible)")
        await config.get_client().delete_client(client_id)
        return {"deleted_client_id": client_id}
