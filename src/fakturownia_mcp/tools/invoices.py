"""Invoice tools."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fakturownia_client.models import Invoice
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from fakturownia_mcp import config
from fakturownia_mcp.approval import format_fields, require_approval
from fakturownia_mcp.errors import api_call
from fakturownia_mcp.schemas import (
    ConfirmFlag,
    CostApprovalStatus,
    DateStr,
    EmailList,
    InvoiceNumber,
    InvoiceOrder,
    InvoiceStatus,
    InvoiceUpdateFields,
    KindStr,
    Page,
    PeriodStr,
    PerPage,
    PositionInput,
    PrintOption,
    full_record,
)

_READ = ToolAnnotations(readOnlyHint=True, openWorldHint=False)


def _summary(invoice: Invoice, *, include_positions: bool = False) -> dict[str, Any]:
    summary = {
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
        "approval_status": getattr(invoice, "approval_status", None),
    }
    if include_positions:
        summary["positions"] = [
            position.model_dump(mode="json", exclude_none=True)
            for position in (invoice.positions or [])
        ]
    return summary


def _is_cost_invoice(invoice: Invoice) -> bool:
    income = getattr(invoice, "income", None)
    return income is False or income in (0, "0", "false", "no")


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=_READ.model_copy(update={"title": "List invoices"}))
    async def list_invoices(
        period: PeriodStr | None = None,
        date_from: DateStr | None = None,
        date_to: DateStr | None = None,
        client_id: Annotated[
            int | None, Field(description="Filter by client id (from list_clients)")
        ] = None,
        number: InvoiceNumber | None = None,
        kind: KindStr | None = None,
        income: Annotated[
            bool | None,
            Field(
                description=(
                    "True/omitted = sales (income) invoices; False = cost/expense "
                    "invoices (faktury kosztowe)"
                )
            ),
        ] = None,
        include_positions: Annotated[
            bool,
            Field(
                description=(
                    "Include every invoice line item in each summary. Useful for exports and "
                    "cost analysis; leave false when compact totals are enough."
                )
            ),
        ] = False,
        order: Annotated[
            InvoiceOrder | None,
            Field(
                description=(
                    "API sort order: a field such as issue_date for ascending, or the same "
                    "field with .desc such as issue_date.desc for descending"
                )
            ),
        ] = None,
        page: Page = 1,
        per_page: PerPage = 25,
    ) -> dict[str, Any]:
        """Search the account's invoices and return one summary per invoice.

        Call this to find invoices by period, date range, client, number or kind,
        and to obtain invoice ids for the other invoice tools. Sales invoices are
        returned by default; pass income=False for cost/expense documents. When
        searching by number or client_id across history, also pass period='all' —
        without a date filter the API may limit results to a recent period.

        Use period='all' and follow pages until has_more is false to read the
        complete history. Set include_positions=true to extract all line items
        directly from every returned invoice without invoking any KSeF service.

        Returns {"invoices": [summaries], "page", "has_more"}; each summary has id,
        number, kind, status, approval_status, issue_date, payment_to, buyer_name,
        price_net, price_gross and currency. Positions are included only when
        requested. has_more is optimistic: a
        result set exactly equal to per_page reports True even on the last page.
        Example: list_invoices(period="last_month", income=False, per_page=50).
        """
        client = await config.get_client()
        invoices = await api_call(
            client.list_invoices(
                period=period,
                date_from=date_from,
                date_to=date_to,
                client_id=client_id,
                number=number,
                kind=kind,
                income=income,
                include_positions=include_positions,
                order=order,
                page=page,
                per_page=per_page,
            )
        )
        return {
            "invoices": [_summary(inv, include_positions=include_positions) for inv in invoices],
            "page": page,
            "has_more": len(invoices) == per_page,
        }

    @mcp.tool(annotations=_READ.model_copy(update={"title": "Get invoice"}))
    async def get_invoice(invoice_id: int) -> dict[str, Any]:
        """Get the full record of one invoice, including positions (line items).

        Call this when you need details a list_invoices summary lacks: line items,
        seller/buyer addresses, payment info or accounting fields. invoice_id is
        the numeric id from list_invoices — not the printed invoice number.

        Returns the complete invoice as stored in Fakturownia (can be large;
        secret share-link fields are removed). Do not call it in a loop over many
        invoices when the summaries already answer the question.
        """
        client = await config.get_client()
        invoice = await api_call(client.get_invoice(invoice_id))
        return full_record(invoice)

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Create invoice",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        )
    )
    async def create_invoice(
        buyer_name: Annotated[
            str | None, Field(description="Buyer name (or pass client_id instead)")
        ] = None,
        buyer_tax_no: Annotated[str | None, Field(description="Buyer tax id (NIP)")] = None,
        buyer_email: Annotated[str | None, Field(description="Buyer e-mail")] = None,
        buyer_company: Annotated[
            bool | None,
            Field(description="True for a company, False for a private person without NIP"),
        ] = None,
        buyer_first_name: Annotated[
            str | None,
            Field(description="Buyer first name; use with buyer_company=False"),
        ] = None,
        buyer_last_name: Annotated[
            str | None,
            Field(description="Buyer last name; use with buyer_company=False"),
        ] = None,
        buyer_street: Annotated[
            str | None, Field(description="Buyer street and building number")
        ] = None,
        buyer_post_code: Annotated[
            str | None, Field(description="Buyer postal code, e.g. 30-001")
        ] = None,
        buyer_city: Annotated[str | None, Field(description="Buyer city")] = None,
        buyer_country: Annotated[
            str | None, Field(description="Buyer country code, e.g. PL")
        ] = None,
        client_id: Annotated[
            int | None, Field(description="Existing client id to bill (fills buyer data)")
        ] = None,
        kind: KindStr = "vat",
        issue_date: DateStr | None = None,
        sell_date: DateStr | None = None,
        payment_to: DateStr | None = None,
        positions: Annotated[
            list[PositionInput] | None,
            Field(
                description=(
                    "Invoice line items. Each needs a name plus price_net or "
                    'total_price_gross for a non-zero amount, e.g. {"name": "Consulting", '
                    '"quantity": 10, "price_net": 150, "tax": 23} or {"name": "Usługa", '
                    '"total_price_gross": 1230.00, "tax": 23}.'
                )
            ),
        ] = None,
        confirm: ConfirmFlag = False,
        *,
        ctx: Context,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Create a new invoice (default kind 'vat') in the account.

        The user approves via a confirmation dialog before anything is created;
        if they decline, do not retry — ask them instead. Either client_id or
        buyer_name is required. Prefer billing an existing contractor: find them
        with list_clients(tax_no=...) and pass client_id, which fills the buyer
        data and avoids duplicate contractors; use buyer_* fields only for
        one-off buyers. For a private person without NIP, pass
        buyer_company=False plus buyer_first_name and buyer_last_name; do not put
        buyer data inside positions. Each position needs a name plus price_net or
        total_price_gross; issue_date defaults to today on the server side. Do
        not use this to modify an existing invoice — that is update_invoice /
        change_invoice_status.

        Returns a summary of the created invoice: its id (for later tool calls)
        and the assigned number. Example: create_invoice(client_id=123,
        positions=[{"name": "Consulting", "quantity": 10, "price_net": 150, "tax": 23}]).
        """
        if client_id is None and not buyer_name:
            raise ToolError(
                "Either client_id or buyer_name is required. Find an existing "
                "contractor with list_clients(tax_no=... or name=...) and pass "
                "client_id, e.g. create_invoice(client_id=123, positions=[...]); "
                "use buyer_name only for a one-off buyer."
            )
        buyer = buyer_name or f"client_id={client_id}"
        described = ", ".join(
            f"{p.quantity} x {p.name} ({p.total_price_gross or p.price_net})"
            for p in (positions or [])
        )
        await require_approval(
            ctx,
            f"create {kind} invoice for {buyer}; positions: {described or '(none)'}",
            confirm=confirm,
        )
        payload: dict[str, Any] = {
            "kind": kind,
            "buyer_name": buyer_name,
            "buyer_tax_no": buyer_tax_no,
            "buyer_email": buyer_email,
            "buyer_company": buyer_company,
            "buyer_first_name": buyer_first_name,
            "buyer_last_name": buyer_last_name,
            "buyer_street": buyer_street,
            "buyer_post_code": buyer_post_code,
            "buyer_city": buyer_city,
            "buyer_country": buyer_country,
            "client_id": client_id,
            "issue_date": issue_date,
            "sell_date": sell_date,
            "payment_to": payment_to,
            "positions": [p.model_dump(exclude_none=True) for p in (positions or [])],
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        client = await config.get_client()
        invoice = await api_call(client.create_invoice(payload))
        return _summary(invoice)

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Update invoice",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    async def update_invoice(
        invoice_id: int,
        fields: InvoiceUpdateFields,
        confirm: ConfirmFlag = False,
        *,
        ctx: Context,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Update selected fields of an existing invoice (partial update).

        Call this to correct invoice data such as buyer_email, payment_to or
        description; the user approves the exact field values in a dialog first.
        Do not use it to change the payment status ('paid' etc.) — that is
        change_invoice_status — and prefer create_invoice for new documents.

        Returns a summary (id, number, status, amounts) of the updated invoice.
        Example: update_invoice(invoice_id=123, fields={"buyer_email": "x@y.pl"}).
        """
        if "approval_status" in fields:
            raise ToolError(
                "approval_status cannot be changed through update_invoice. Use "
                "change_cost_invoice_approval_status, which first verifies that the target "
                "is a cost invoice."
            )
        await require_approval(
            ctx, f"update invoice {invoice_id}: {format_fields(fields)}", confirm=confirm
        )
        client = await config.get_client()
        invoice = await api_call(client.update_invoice(invoice_id, fields))
        return _summary(invoice)

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Change invoice status",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    async def change_invoice_status(
        invoice_id: int,
        status: InvoiceStatus,
        confirm: ConfirmFlag = False,
        *,
        ctx: Context,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Set the payment status of an invoice: issued, sent, paid, partial or rejected.

        Call this when the user says an invoice was paid, sent or rejected — it is
        also the sanctioned alternative to deleting an invoice (there is no delete
        tool by design). The user approves the change in a dialog first. The
        invoice_id comes from list_invoices; the operation fails on the API side
        if the transition is not allowed for the document.

        Returns {"invoice_id", "status"} after the API confirms the change.
        """
        await require_approval(
            ctx, f"change status of invoice {invoice_id} to '{status}'", confirm=confirm
        )
        client = await config.get_client()
        await api_call(client.change_invoice_status(invoice_id, status))
        return {"invoice_id": invoice_id, "status": status}

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Change cost invoice approval status",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    async def change_cost_invoice_approval_status(
        invoice_id: int,
        approval_status: Annotated[
            CostApprovalStatus,
            Field(
                description=(
                    "Cost workflow state: received (otrzymana), accepted (zatwierdzona), "
                    "or rejected (odrzucona)"
                )
            ),
        ],
        confirm: ConfirmFlag = False,
        *,
        ctx: Context,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Set the approval workflow state of a cost/expense invoice.

        The tool first reads the invoice and refuses sales/income documents, so
        this workflow cannot be applied to an issued sales invoice accidentally.
        It maps received to "otrzymana", accepted to "zatwierdzona", and rejected
        to "odrzucona" in the Polish UI. The user approves the exact transition
        before the API update is sent.

        Returns the updated invoice summary, including approval_status.
        """
        client = await config.get_client()
        invoice = await api_call(client.get_invoice(invoice_id))
        if not _is_cost_invoice(invoice):
            raise ToolError(
                f"Invoice {invoice_id} is not confirmed as a cost invoice. "
                "Use list_invoices(income=False, period='all') to select a cost invoice id."
            )
        await require_approval(
            ctx,
            f"change cost invoice {invoice_id} approval_status to '{approval_status}'",
            confirm=confirm,
        )
        updated = await api_call(
            client.update_invoice(invoice_id, {"approval_status": approval_status})
        )
        return _summary(updated)

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Send invoice by e-mail",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=True,
        )
    )
    async def send_invoice_by_email(
        invoice_id: int,
        email_to: Annotated[
            EmailList | None,
            Field(description="Recipients; omit to send to the invoice's buyer e-mail"),
        ] = None,
        email_cc: Annotated[EmailList | None, Field(description="CC recipients")] = None,
        print_option: Annotated[
            PrintOption | None,
            Field(description="Document variant to send; server default is the original"),
        ] = None,
        confirm: ConfirmFlag = False,
        *,
        ctx: Context,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """E-mail an invoice (with its PDF attached) to the buyer or given recipients.

        Call this when the user wants an invoice delivered to their client
        ("wyślij fakturę X mailem"). Omitting email_to sends to the buyer's
        e-mail stored on the invoice — check it first with get_invoice and
        confirm with the user, because the message goes out immediately and
        cannot be recalled. The user approves the recipients in a dialog first;
        sending again produces a second e-mail, so never retry after success or
        a declined approval. To only produce the file locally use
        download_invoice_pdf instead.

        Returns {"invoice_id", "sent_to"} after the API accepts the send.
        Example: send_invoice_by_email(invoice_id=123, email_to=["client@acme.pl"]).
        """
        recipients = ", ".join(email_to) if email_to else "the buyer e-mail on the invoice"
        cc = f" (cc: {', '.join(email_cc)})" if email_cc else ""
        await require_approval(
            ctx,
            f"SEND invoice {invoice_id} by e-mail to {recipients}{cc} — goes out immediately",
            confirm=confirm,
        )
        client = await config.get_client()
        await api_call(
            client.send_invoice_by_email(
                invoice_id,
                email_to=email_to,
                email_cc=email_cc,
                email_pdf=True,
                print_option=print_option,
            )
        )
        return {"invoice_id": invoice_id, "sent_to": email_to or "buyer_email"}

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Download invoice PDF",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        )
    )
    async def download_invoice_pdf(
        invoice_id: int,
        output_path: Annotated[
            str | None,
            Field(
                description=(
                    "Optional file path INSIDE the allowed download directory "
                    "(FAKTUROWNIA_DOWNLOAD_DIR, default ~/Downloads); defaults to "
                    "faktura-<number>.pdf there"
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Download an invoice PDF and save it to the local download directory.

        This writes a file on the user's machine (never overwrites — an existing
        name gets a numeric suffix) and is restricted to the configured download
        directory; paths outside it are rejected. Use it when the user wants the
        document itself; for reading invoice data use get_invoice instead.

        Returns {"path", "size_bytes"} of the saved file.
        """
        client = await config.get_client()
        invoice = await api_call(client.get_invoice(invoice_id))
        number = invoice.number or str(invoice_id)
        target = _resolve_download_target(number, output_path)
        pdf = await api_call(client.download_invoice_pdf(invoice_id))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(pdf)
        return {"path": str(target), "size_bytes": len(pdf)}


def _resolve_download_target(number: str, output_path: str | None) -> Path:
    """Confine the write to the allowed directory and never overwrite."""
    base = config.download_dir().resolve()
    if output_path:
        raw = Path(output_path).expanduser()
        candidate = raw if raw.is_absolute() else base / raw
    else:
        candidate = base / f"faktura-{number.replace('/', '-')}.pdf"
    resolved = candidate.resolve()
    if not resolved.is_relative_to(base):
        raise ToolError(
            f"Refusing to write outside the allowed download directory ({base}). "
            "Pass a relative filename or a path inside that directory, or ask the "
            "user to change FAKTUROWNIA_DOWNLOAD_DIR."
        )
    unique = resolved
    counter = 1
    while unique.exists():
        unique = resolved.with_stem(f"{resolved.stem}-{counter}")
        counter += 1
    return unique
