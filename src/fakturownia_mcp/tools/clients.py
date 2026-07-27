"""Client (contractor) tools."""

from __future__ import annotations

from typing import Annotated, Any

from fakturownia_client.models import Client
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field

from fakturownia_mcp import config
from fakturownia_mcp.approval import require_approval
from fakturownia_mcp.schemas import Page, PerPage, UpdateFields

TaxNo = Annotated[str, Field(description="Tax id (NIP), digits only, e.g. 1234567890")]


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
        name: Annotated[str | None, Field(description="Filter by (partial) name")] = None,
        tax_no: TaxNo | None = None,
        email: Annotated[str | None, Field(description="Filter by e-mail")] = None,
        page: Page = 1,
        per_page: PerPage = 25,
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
        name: Annotated[str, Field(min_length=1, description="Client name")],
        tax_no: TaxNo | None = None,
        email: Annotated[str | None, Field(description="E-mail address")] = None,
        phone: Annotated[str | None, Field(description="Phone number")] = None,
        street: Annotated[str | None, Field(description="Street and building number")] = None,
        city: Annotated[str | None, Field(description="City")] = None,
        post_code: Annotated[str | None, Field(description="Postal code, e.g. 30-001")] = None,
        country: Annotated[str | None, Field(description="Country code, e.g. PL")] = None,
        company: Annotated[
            bool, Field(description="True for a company, False for a person")
        ] = True,
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
        fields: UpdateFields,
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
