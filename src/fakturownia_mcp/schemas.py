"""Shared Pydantic parameter types for tool signatures.

FastMCP turns these annotations into the tools' JSON Schema, so clients
validate arguments before the server is even called.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

InvoiceStatus = Literal["issued", "sent", "paid", "partial", "rejected"]

DateStr = Annotated[
    str,
    Field(
        description="Date in YYYY-MM-DD format",
        pattern=r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$",
    ),
]

Page = Annotated[int, Field(ge=1, description="Page number (1-based)")]
PerPage = Annotated[int, Field(ge=1, le=100, description="Items per page (max 100)")]

PeriodStr = Annotated[
    str,
    Field(
        description=(
            "Predefined period: this_month, last_month, this_year, last_year, "
            "last_30_days, all. Set to 'more' (or just pass date_from/date_to) "
            "for an explicit date range."
        )
    ),
]

KindStr = Annotated[
    str,
    Field(
        description="Document kind: vat, proforma, correction, receipt, advance, final, estimate"
    ),
]

TaxRate = Annotated[
    float | str,
    Field(description="VAT rate, e.g. 23, 8, 0, or 'zw' (exempt) / 'np' (not applicable)"),
]

ConfirmFlag = Annotated[
    bool,
    Field(
        description=(
            "Set true ONLY after the user explicitly approved this exact operation in "
            "conversation. Needed when the client has no native approval dialogs "
            "(e.g. Claude Desktop); dialog-capable clients ignore it."
        )
    ),
]

InvoiceNumber = Annotated[
    str,
    Field(description="Full or partial invoice number as printed, e.g. '15/2025' or 'P1/07/2026'"),
]

EmailList = Annotated[
    list[Annotated[str, Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]],
    Field(
        min_length=1,
        max_length=5,
        description="E-mail addresses (the API caps recipients at 5)",
    ),
]

PrintOption = Literal["original", "copy", "original_and_copy", "duplicate"]

InvoiceUpdateFields = Annotated[
    dict[str, Any],
    Field(
        min_length=1,
        description=(
            "Only the fields to change, using Fakturownia API names. Common ones: "
            "buyer_name, buyer_tax_no, buyer_email, issue_date, sell_date, payment_to, "
            "description, payment_type, approval_status. Do NOT change 'status' here — "
            "use change_invoice_status. Updating 'positions' has special semantics "
            "(existing lines need their 'id'; removal needs {'id': ..., '_destroy': 1})."
        ),
    ),
]

ClientUpdateFields = Annotated[
    dict[str, Any],
    Field(
        min_length=1,
        description=(
            "Only the fields to change, using Fakturownia API names. Common ones: "
            "name, tax_no, email, phone, street, city, post_code, country, note, "
            "external_id, company."
        ),
    ),
]

ProductUpdateFields = Annotated[
    dict[str, Any],
    Field(
        min_length=1,
        description=(
            "Only the fields to change, using Fakturownia API names. Common ones: "
            "name, code, price_net, price_gross, tax, currency, quantity_unit, "
            "description, disabled. Caveat: to change the price you MUST send "
            "price_net and price_gross together — a lone price_net is ignored."
        ),
    ),
]


class PositionInput(BaseModel):
    """One invoice line item; give total_price_gross or price_net."""

    model_config = ConfigDict(extra="allow")

    name: Annotated[str, Field(min_length=1, description="Line item name")]
    quantity: Annotated[float, Field(gt=0, description="Quantity")] = 1
    tax: TaxRate = 23
    price_net: Annotated[float | str | None, Field(description="Unit net price")] = None
    total_price_gross: Annotated[
        float | str | None, Field(description="Total gross price for the line")
    ] = None
    product_id: Annotated[
        int | None, Field(description="Existing product id to link this line to")
    ] = None


_SECRET_FIELDS = ("token", "view_url", "panel_url", "payment_url")


def full_record(model: BaseModel) -> dict[str, Any]:
    """Full JSON dump minus secret-bearing fields (public share links, tokens)."""
    data = model.model_dump(mode="json", exclude_none=True)
    for key in _SECRET_FIELDS:
        data.pop(key, None)
    return data
