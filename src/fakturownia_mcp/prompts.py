"""Reusable prompts (slash-command style workflows) exposed by the server.

The template strings below are the SINGLE SOURCE OF TRUTH shared with
``mcpb/manifest.json`` (test-enforced). Claude Desktop validates the text a
bundle server returns from prompts/get against the manifest declaration
(after substituting ``${arguments.KEY}``) and rejects any mismatch as
potential prompt injection — so the server must return exactly the declared
template with plain placeholder substitution, no extra logic.
"""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

MONTHLY_SUMMARY_TEXT = (
    "Prepare a financial summary of my Fakturownia account for month "
    "'${arguments.month}' (if empty, use the current month). "
    "1) Use list_invoices with date_from/date_to covering the month for sales "
    "invoices, and again with income=false for cost invoices; paginate until "
    "has_more is false. "
    "2) Use list_payments(include_invoices=true) to see which money actually "
    "arrived that month. "
    "3) Report: total net/gross revenue, total costs, the resulting balance, "
    "unpaid or partially paid sales invoices (number, buyer, amount, "
    "payment_to), and payments not linked to any invoice. "
    "Amounts are strings in the account currency - do not convert them. "
    "Present the summary as a short table plus 2-3 sentences of commentary."
)

CHASE_UNPAID_TEXT = (
    "Find my overdue invoices and prepare payment reminders. "
    "1) Use list_invoices(period='all') and keep sales invoices whose status "
    "is not 'paid' and whose payment_to is before today. "
    "2) For each, fetch get_invoice to confirm the buyer e-mail and amounts. "
    "3) Show a table: number, buyer, buyer_email, gross amount, days overdue "
    "- ordered by days overdue descending. "
    "4) Draft a short, polite reminder e-mail in Polish for each buyer, but "
    "DO NOT send anything yet. Only after I explicitly pick invoices may you "
    "use send_invoice_by_email, and it will still ask for approval."
)

MONTHLY_SUMMARY_DESCRIPTION = "Revenue, costs, unpaid invoices and payments for one month"
CHASE_UNPAID_DESCRIPTION = (
    "Find overdue invoices and draft payment reminders (nothing is sent without approval)"
)


def register(mcp: FastMCP) -> None:
    @mcp.prompt(title="Monthly summary", description=MONTHLY_SUMMARY_DESCRIPTION)
    def monthly_summary(
        month: Annotated[
            str, Field(description="Month as YYYY-MM; empty = the current month")
        ] = "",
    ) -> str:
        return MONTHLY_SUMMARY_TEXT.replace("${arguments.month}", month)

    @mcp.prompt(title="Chase unpaid invoices", description=CHASE_UNPAID_DESCRIPTION)
    def chase_unpaid() -> str:
        return CHASE_UNPAID_TEXT
