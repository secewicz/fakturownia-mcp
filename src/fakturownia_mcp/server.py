"""FastMCP server entry point (stdio transport)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from fakturownia_mcp import config
from fakturownia_mcp.tools import register_all

INSTRUCTIONS = """\
Tools for ONE Fakturownia (InvoiceOcean) invoicing account, configured via
FAKTUROWNIA_DOMAIN and FAKTUROWNIA_API_TOKEN.

Conventions: dates are YYYY-MM-DD; amounts are strings in the account
currency (typically PLN); ids are numeric and come from list_* tools —
printed document numbers like '15/2025' are NOT ids.

Workflow: list_* tools return compact summaries (fetch details with get_*).
Before creating a client or invoicing by buyer_* fields, search with
list_clients (by tax_no/name) and prefer create_invoice(client_id=...) to
avoid duplicate contractors. Expenses are invoices with income=False.

Writes (create_*, update_*, delete_client, change_invoice_status) ask the
user for approval via an elicitation dialog before touching the API. On
clients without elicitation the first call is rejected with instructions:
present the operation to the user and re-call with confirm=true ONLY after
they explicitly agree in conversation. If the user declines (dialog or
conversation), the operation is cancelled — do NOT retry it; ask the user
how to proceed. There is deliberately no tool for deleting invoices — use
change_invoice_status instead.
"""


@asynccontextmanager
async def _lifespan(_server: FastMCP) -> AsyncIterator[None]:
    try:
        yield
    finally:
        await config.aclose_client()


mcp = FastMCP("fakturownia", instructions=INSTRUCTIONS, lifespan=_lifespan)
register_all(mcp)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
