"""Client (contractor) tools."""

from __future__ import annotations

from typing import Annotated, Any

from fakturownia_client.models import Client
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from fakturownia_mcp import config
from fakturownia_mcp.approval import format_fields, require_approval
from fakturownia_mcp.errors import api_call
from fakturownia_mcp.schemas import ClientUpdateFields, ConfirmFlag, Page, PerPage, full_record

TaxNo = Annotated[
    str,
    Field(
        description=(
            "Tax id — Polish NIP as digits only, e.g. 1234567890; "
            "foreign tax ids are passed to the API as-is"
        )
    ),
]

_READ = ToolAnnotations(readOnlyHint=True, openWorldHint=False)


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
    @mcp.tool(annotations=_READ.model_copy(update={"title": "List clients"}))
    async def list_clients(
        name: Annotated[str | None, Field(description="Filter by (partial) name")] = None,
        tax_no: TaxNo | None = None,
        email: Annotated[str | None, Field(description="Filter by e-mail")] = None,
        page: Page = 1,
        per_page: PerPage = 25,
    ) -> dict[str, Any]:
        """Search the account's clients (contractors) and return summaries.

        Call this to find a contractor by (partial) name, tax id (NIP) or e-mail —
        and ALWAYS before create_client or create_invoice with buyer_* fields, to
        avoid creating duplicate contractors. The returned id is what the other
        client tools and create_invoice(client_id=...) expect.

        Returns {"clients": [{id, name, tax_no, email, city, external_id}],
        "page", "has_more"}; use get_client(client_id) for the full record.
        Example: list_clients(tax_no="6762447754").
        """
        client = await config.get_client()
        clients = await api_call(
            client.list_clients(name=name, tax_no=tax_no, email=email, page=page, per_page=per_page)
        )
        return {
            "clients": [_summary(c) for c in clients],
            "page": page,
            "has_more": len(clients) == per_page,
        }

    @mcp.tool(annotations=_READ.model_copy(update={"title": "Get client"}))
    async def get_client(client_id: int) -> dict[str, Any]:
        """Get the full record of one client (contractor).

        Call this when you need details a list_clients summary lacks: full
        address, phone, bank account or notes. client_id is the numeric id from
        list_clients. Returns the complete record as stored in Fakturownia
        (secret share-link fields are removed).
        """
        client = await config.get_client()
        record = await api_call(client.get_client(client_id))
        return full_record(record)

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Create client",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        )
    )
    async def create_client(
        name: Annotated[
            str | None,
            Field(
                min_length=1,
                description="Client/company display name; required for companies",
            ),
        ] = None,
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
        first_name: Annotated[
            str | None,
            Field(description="First name for company=False private-person clients"),
        ] = None,
        last_name: Annotated[
            str | None,
            Field(description="Last name for company=False private-person clients"),
        ] = None,
        confirm: ConfirmFlag = False,
        *,
        ctx: Context,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Create a new client (contractor) in the account.

        First check with list_clients(tax_no=... or name=...) that the contractor
        does not already exist — duplicates pollute the account. The user approves
        the creation (with the values) in a dialog before anything is written.
        For a private person without NIP, pass company=False plus first_name and
        last_name; tax_no is not required in that case.

        Returns a summary with the new client's id, which create_invoice and the
        other client tools accept. Example: create_client(name="ACME Sp. z o.o.",
        tax_no="1234567890", email="biuro@acme.pl").
        """
        if company and not name:
            raise ToolError("Client name is required when company=True.")
        if not company and not (name or (first_name and last_name)):
            raise ToolError(
                "For a private-person client, pass company=False plus first_name "
                "and last_name, or provide name explicitly."
            )
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
            "first_name": first_name,
            "last_name": last_name,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        await require_approval(ctx, f"create client: {format_fields(payload)}", confirm=confirm)
        client = await config.get_client()
        record = await api_call(client.create_client(payload))
        return _summary(record)

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Update client",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    async def update_client(
        client_id: int,
        fields: ClientUpdateFields,
        confirm: ConfirmFlag = False,
        *,
        ctx: Context,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Update selected fields of an existing client (partial update).

        Use this to fix contractor data (e-mail, address, phone) — never
        delete_client for corrections. The user approves the exact field values
        in a dialog first. Returns a summary of the updated client.
        Example: update_client(client_id=5, fields={"email": "new@acme.pl"}).
        """
        await require_approval(
            ctx, f"update client {client_id}: {format_fields(fields)}", confirm=confirm
        )
        client = await config.get_client()
        record = await api_call(client.update_client(client_id, fields))
        return _summary(record)

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Delete client",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    async def delete_client(
        client_id: int,
        confirm: ConfirmFlag = False,
        *,
        ctx: Context,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Permanently delete a client (contractor). Irreversible.

        Use only when the user explicitly asks to remove a contractor. Verify the
        target first with get_client(client_id) and confirm the name with the
        user — deleting the wrong record cannot be undone. Invoices already
        issued to the client are not deleted. For fixing data use update_client
        instead. A declined approval is final — do not retry.

        Returns {"deleted_client_id"} on success.
        """
        client = await config.get_client()
        record = await api_call(client.get_client(client_id))
        await require_approval(
            ctx, f"DELETE client {client_id} ({record.name!r}) — irreversible", confirm=confirm
        )
        await api_call(client.delete_client(client_id))
        return {"deleted_client_id": client_id}
