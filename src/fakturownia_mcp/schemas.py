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
    Field(description="Date in YYYY-MM-DD format", pattern=r"^\d{4}-\d{2}-\d{2}$"),
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

UpdateFields = Annotated[
    dict[str, Any],
    Field(
        min_length=1,
        description='Partial update: only the fields to change, e.g. {"buyer_email": "x@y.pl"}',
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
