"""Reusable prompts (slash-command style workflows) exposed by the server."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    @mcp.prompt(title="Monthly summary")
    def monthly_summary(
        month: Annotated[
            str, Field(description="Month as YYYY-MM; empty = the current month")
        ] = "",
    ) -> str:
        """Summarize the account for one month: revenue, costs, unpaid invoices, payments."""
        period = f"month {month}" if month else "the current month"
        return (
            f"Prepare a financial summary of my Fakturownia account for {period}.\n"
            "1. Use list_invoices with date_from/date_to covering the month for sales "
            "invoices, and again with income=false for cost invoices (paginate until "
            "has_more is false).\n"
            "2. Use list_payments(include_invoices=true) to see which money actually "
            "arrived that month.\n"
            "3. Report: total net/gross revenue, total costs, the resulting balance, "
            "a list of unpaid or partially paid sales invoices (number, buyer, amount, "
            "payment_to), and any payments not linked to an invoice.\n"
            "Amounts are strings in the account currency — do not convert them. "
            "Present the summary as a short table plus 2-3 sentences of commentary."
        )

    @mcp.prompt(title="Chase unpaid invoices")
    def chase_unpaid() -> str:
        """Find overdue invoices and prepare (but do not send) payment reminders."""
        return (
            "Find my overdue invoices and prepare payment reminders.\n"
            "1. Use list_invoices(period='all') and keep sales invoices whose status "
            "is not 'paid' and whose payment_to is before today.\n"
            "2. For each, fetch get_invoice to confirm the buyer e-mail and amounts.\n"
            "3. Show me a table: number, buyer, buyer_email, gross amount, days "
            "overdue — ordered by days overdue descending.\n"
            "4. Draft a short, polite reminder e-mail text in Polish for each buyer, "
            "but DO NOT send anything yet. Only after I explicitly pick invoices may "
            "you use send_invoice_by_email, and it will still ask for approval."
        )
