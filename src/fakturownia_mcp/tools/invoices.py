"""Invoice tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fakturownia_client.models import Invoice
from mcp.server.fastmcp import FastMCP

from fakturownia_mcp import config

VALID_STATUSES = ("issued", "sent", "paid", "partial", "rejected")


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
    def list_invoices(
        period: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        client_id: int | None = None,
        number: str | None = None,
        kind: str | None = None,
        page: int = 1,
        per_page: int = 25,
    ) -> dict[str, Any]:
        """List/search invoices. Returns summaries; use get_invoice for full details.

        period: this_month, last_month, this_year, last_30_days, all... Giving
        date_from/date_to (YYYY-MM-DD) automatically switches to a date range.
        """
        invoices = config.get_client().list_invoices(
            period=period,
            date_from=date_from,
            date_to=date_to,
            client_id=client_id,
            number=number,
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
    def get_invoice(invoice_id: int) -> dict[str, Any]:
        """Get full invoice details including positions (line items)."""
        invoice = config.get_client().get_invoice(invoice_id)
        return invoice.model_dump(mode="json", exclude_none=True)

    @mcp.tool()
    def create_invoice(
        buyer_name: str | None = None,
        buyer_tax_no: str | None = None,
        buyer_email: str | None = None,
        client_id: int | None = None,
        kind: str = "vat",
        issue_date: str | None = None,
        sell_date: str | None = None,
        payment_to: str | None = None,
        positions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create an invoice. Identify the buyer by client_id or buyer_* fields.

        Each position is a dict like {"name": "...", "quantity": 1, "tax": 23,
        "total_price_gross": 123.00} (or price_net instead of total_price_gross).
        Dates are YYYY-MM-DD; issue_date defaults to today on the server side.
        """
        payload: dict[str, Any] = {
            "kind": kind,
            "buyer_name": buyer_name,
            "buyer_tax_no": buyer_tax_no,
            "buyer_email": buyer_email,
            "client_id": client_id,
            "issue_date": issue_date,
            "sell_date": sell_date,
            "payment_to": payment_to,
            "positions": positions or [],
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        invoice = config.get_client().create_invoice(payload)
        return invoice.model_dump(mode="json", exclude_none=True)

    @mcp.tool()
    def update_invoice(invoice_id: int, fields: dict[str, Any]) -> dict[str, Any]:
        """Update selected fields of an invoice, e.g. {"buyer_email": "x@y.pl"}."""
        invoice = config.get_client().update_invoice(invoice_id, fields)
        return invoice.model_dump(mode="json", exclude_none=True)

    @mcp.tool()
    def change_invoice_status(invoice_id: int, status: str) -> dict[str, Any]:
        """Change invoice status: issued, sent, paid, partial or rejected."""
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status {status!r}; expected one of {VALID_STATUSES}")
        config.get_client().change_invoice_status(invoice_id, status)  # type: ignore[arg-type]
        return {"invoice_id": invoice_id, "status": status}

    @mcp.tool()
    def download_invoice_pdf(invoice_id: int, output_path: str | None = None) -> dict[str, Any]:
        """Download the invoice PDF to disk (default: ~/Downloads/faktura-<number>.pdf)."""
        client = config.get_client()
        pdf = client.download_invoice_pdf(invoice_id)
        if output_path:
            target = Path(output_path).expanduser()
        else:
            number = client.get_invoice(invoice_id).number or str(invoice_id)
            target = Path.home() / "Downloads" / f"faktura-{number.replace('/', '-')}.pdf"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(pdf)
        return {"path": str(target), "size_bytes": len(pdf)}
