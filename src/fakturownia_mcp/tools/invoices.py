"""Invoice tools."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fakturownia_client.models import Invoice
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field

from fakturownia_mcp import config
from fakturownia_mcp.approval import require_approval
from fakturownia_mcp.schemas import (
    DateStr,
    InvoiceStatus,
    KindStr,
    Page,
    PeriodStr,
    PerPage,
    PositionInput,
    UpdateFields,
)


def _summary(invoice: Invoice) -> dict[str, Any]:
    return {
        "id": invoice.id,
        "number": invoice.number,
        "kind": invoice.kind,
        "status": invoice.status,
        "issue_date": str(invoice.issue_date) if invoice.issue_date else None,
        "payment_to": str(invoice.payment_to) if invoice.payment_to else None,
        "buyer_name": invoice.buyer_name,
        "price_net": invoice.price_net,
        "price_gross": invoice.price_gross,
        "currency": invoice.currency,
    }


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_invoices(
        period: PeriodStr | None = None,
        date_from: DateStr | None = None,
        date_to: DateStr | None = None,
        client_id: Annotated[int | None, Field(description="Filter by client id")] = None,
        number: Annotated[int | str | None, Field(description="Filter by invoice number")] = None,
        kind: KindStr | None = None,
        page: Page = 1,
        per_page: PerPage = 25,
    ) -> dict[str, Any]:
        """List/search invoices. Returns summaries; use get_invoice for full details."""
        invoices = await config.get_client().list_invoices(
            period=period,
            date_from=date_from,
            date_to=date_to,
            client_id=client_id,
            number=str(number) if number is not None else None,
            kind=kind,
            page=page,
            per_page=per_page,
        )
        return {
            "invoices": [_summary(inv) for inv in invoices],
            "page": page,
            "has_more": len(invoices) == per_page,
        }

    @mcp.tool()
    async def get_invoice(invoice_id: int) -> dict[str, Any]:
        """Get full invoice details including positions (line items)."""
        invoice = await config.get_client().get_invoice(invoice_id)
        return invoice.model_dump(mode="json", exclude_none=True)

    @mcp.tool()
    async def create_invoice(
        buyer_name: Annotated[
            str | None, Field(description="Buyer name (or pass client_id instead)")
        ] = None,
        buyer_tax_no: Annotated[str | None, Field(description="Buyer tax id (NIP)")] = None,
        buyer_email: Annotated[str | None, Field(description="Buyer e-mail")] = None,
        client_id: Annotated[
            int | None, Field(description="Existing client id to bill (fills buyer data)")
        ] = None,
        kind: KindStr = "vat",
        issue_date: DateStr | None = None,
        sell_date: DateStr | None = None,
        payment_to: DateStr | None = None,
        positions: Annotated[
            list[PositionInput] | None, Field(description="Invoice line items")
        ] = None,
        *,
        ctx: Context,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Create an invoice. Identify the buyer by client_id or buyer_* fields.

        issue_date defaults to today on the server side.
        """
        buyer = buyer_name or (f"client_id={client_id}" if client_id else "unknown buyer")
        names = ", ".join(p.name for p in (positions or []))
        await require_approval(
            ctx, f"create {kind} invoice for {buyer} with positions: {names or '(none)'}"
        )
        payload: dict[str, Any] = {
            "kind": kind,
            "buyer_name": buyer_name,
            "buyer_tax_no": buyer_tax_no,
            "buyer_email": buyer_email,
            "client_id": client_id,
            "issue_date": issue_date,
            "sell_date": sell_date,
            "payment_to": payment_to,
            "positions": [p.model_dump(exclude_none=True) for p in (positions or [])],
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        invoice = await config.get_client().create_invoice(payload)
        return invoice.model_dump(mode="json", exclude_none=True)

    @mcp.tool()
    async def update_invoice(
        invoice_id: int,
        fields: UpdateFields,
        *,
        ctx: Context,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Update selected fields of an invoice, e.g. {"buyer_email": "x@y.pl"}."""
        await require_approval(
            ctx, f"update invoice {invoice_id}, fields: {', '.join(sorted(fields))}"
        )
        invoice = await config.get_client().update_invoice(invoice_id, fields)
        return invoice.model_dump(mode="json", exclude_none=True)

    @mcp.tool()
    async def change_invoice_status(
        invoice_id: int,
        status: InvoiceStatus,
        *,
        ctx: Context,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Change invoice status: issued, sent, paid, partial or rejected."""
        await require_approval(ctx, f"change status of invoice {invoice_id} to '{status}'")
        await config.get_client().change_invoice_status(invoice_id, status)
        return {"invoice_id": invoice_id, "status": status}

    @mcp.tool()
    async def download_invoice_pdf(
        invoice_id: int,
        output_path: Annotated[
            str | None,
            Field(description="Target file path; defaults to ~/Downloads/faktura-<number>.pdf"),
        ] = None,
    ) -> dict[str, Any]:
        """Download the invoice PDF to disk."""
        client = config.get_client()
        pdf = await client.download_invoice_pdf(invoice_id)
        if output_path:
            target = Path(output_path).expanduser()
        else:
            number = (await client.get_invoice(invoice_id)).number or str(invoice_id)
            target = Path.home() / "Downloads" / f"faktura-{number.replace('/', '-')}.pdf"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(pdf)
        return {"path": str(target), "size_bytes": len(pdf)}
