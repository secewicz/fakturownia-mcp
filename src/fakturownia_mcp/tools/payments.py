"""Banking payment tools."""

from __future__ import annotations

from typing import Annotated, Any

from fakturownia_client.models import Payment
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from fakturownia_mcp import config
from fakturownia_mcp.approval import require_approval
from fakturownia_mcp.errors import api_call
from fakturownia_mcp.schemas import ConfirmFlag, Page, PerPage

_READ = ToolAnnotations(readOnlyHint=True, openWorldHint=False)


def _summary(payment: Payment) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": payment.id,
        "name": payment.name,
        "price": payment.price,
        "currency": payment.currency,
        "paid": payment.paid,
        "kind": payment.kind,
        "invoice_id": payment.invoice_id,
    }
    if payment.invoices is not None:
        data["invoices"] = [
            {"id": inv.id, "number": inv.number, "price_gross": inv.price_gross}
            for inv in payment.invoices
        ]
    return data


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=_READ.model_copy(update={"title": "List payments"}))
    async def list_payments(
        include_invoices: Annotated[
            bool, Field(description="Embed the invoices each payment is linked to")
        ] = False,
        page: Page = 1,
        per_page: PerPage = 25,
    ) -> dict[str, Any]:
        """List banking payments recorded on the account (newest first).

        Call this to check incoming money: which payments arrived, what amounts,
        and which invoices they settle (pass include_invoices=true to embed the
        linked invoices). Note that an invoice can also be marked paid without a
        payment record — for a single invoice's payment status prefer
        get_invoice and its 'paid'/'status' fields.

        Returns {"payments": [summaries], "page", "has_more"}; each summary has
        id, name, price, currency, paid, kind and invoice_id. has_more is
        optimistic: a result set exactly equal to per_page reports True even on
        the last page. Example: list_payments(include_invoices=true, per_page=50).
        """
        client = await config.get_client()
        payments = await api_call(
            client.list_payments(page=page, per_page=per_page, include_invoices=include_invoices)
        )
        return {
            "payments": [_summary(p) for p in payments],
            "page": page,
            "has_more": len(payments) == per_page,
        }

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Create payment",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        )
    )
    async def create_payment(
        price: Annotated[
            float | str, Field(description="Payment amount (positive), e.g. 500.0 or '500.00'")
        ],
        name: Annotated[
            str | None, Field(description="Payment title, e.g. 'Transfer FV 12/2026'")
        ] = None,
        invoice_id: Annotated[
            int | None,
            Field(
                description=(
                    "Invoice this payment settles (from list_invoices). "
                    "Mutually exclusive with invoice_ids — pass at most one of them."
                )
            ),
        ] = None,
        invoice_ids: Annotated[
            list[int] | None,
            Field(
                description=(
                    "Multiple invoices to settle, in array order. "
                    "Mutually exclusive with invoice_id — pass at most one of them."
                )
            ),
        ] = None,
        currency: Annotated[str | None, Field(description="Currency code, e.g. PLN")] = None,
        paid: Annotated[bool, Field(description="Mark the payment as received")] = True,
        confirm: ConfirmFlag = False,
        *,
        ctx: Context,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Record a banking payment, optionally settling one or more invoices.

        Call this when the user says money arrived for an invoice ("zaksięguj
        wpłatę 500 zł do faktury X") — link it with invoice_id, or invoice_ids
        for several invoices settled in array order. The user approves the
        amount and target invoice in a dialog first. This creates a payment
        record; to only flip an invoice's status without recording money, use
        change_invoice_status(status='paid') instead.

        Returns a summary of the created payment (id, name, price, invoice_id).
        Example: create_payment(price=500.0, invoice_id=123, name="Przelew mBank").
        """
        if invoice_id is not None and invoice_ids is not None:
            raise ToolError(
                "Pass either invoice_id or invoice_ids, not both. Example: "
                "create_payment(price=500.0, invoice_id=123) for one invoice, or "
                "create_payment(price=500.0, invoice_ids=[123, 124]) to settle "
                "several in order."
            )
        try:
            if float(price) <= 0:
                raise ToolError("price must be a positive amount, e.g. 500.0 or '500.00'.")
        except ValueError:
            raise ToolError(
                f"price {price!r} is not a number — pass e.g. 500.0 or '500.00'."
            ) from None
        target = (
            f"invoice {invoice_id}"
            if invoice_id
            else f"invoices {invoice_ids}"
            if invoice_ids
            else "no invoice (unassigned)"
        )
        await require_approval(
            ctx,
            f"record payment of {price} {currency or ''} for {target}"
            + (f" ({name!r})" if name else ""),
            confirm=confirm,
        )
        payload: dict[str, Any] = {
            "name": name,
            "price": price,
            "invoice_id": invoice_id,
            "invoice_ids": invoice_ids,
            "currency": currency,
            "paid": paid,
            "kind": "api",
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        client = await config.get_client()
        payment = await api_call(client.create_payment(payload))
        return _summary(payment)

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Delete payment",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    async def delete_payment(
        payment_id: int,
        confirm: ConfirmFlag = False,
        *,
        ctx: Context,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Permanently delete a payment record. Irreversible.

        Use only to correct a mistakenly recorded payment (wrong amount or wrong
        invoice) when the user explicitly asks — the linked invoice itself is
        not deleted, but its settled amount changes. The payment's name and
        amount are shown in the approval dialog; a declined approval is final,
        do not retry. To fix other details prefer creating a corrected payment.

        Returns {"deleted_payment_id"} on success.
        """
        client = await config.get_client()
        payment = await api_call(client.get_payment(payment_id))
        await require_approval(
            ctx,
            f"DELETE payment {payment_id} ({payment.name!r}, {payment.price} "
            f"{payment.currency or ''}) — irreversible",
            confirm=confirm,
        )
        await api_call(client.delete_payment(payment_id))
        return {"deleted_payment_id": payment_id}
