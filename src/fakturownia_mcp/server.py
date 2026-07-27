"""FastMCP server entry point (stdio transport)."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from fakturownia_mcp.tools import register_all

mcp = FastMCP(
    "fakturownia",
    instructions=(
        "Tools for the Fakturownia (InvoiceOcean) invoicing account configured via "
        "FAKTUROWNIA_DOMAIN and FAKTUROWNIA_API_TOKEN. List tools return summaries; "
        "fetch full records with the get_* tools. There is deliberately no tool for "
        "deleting invoices — change their status instead."
    ),
)
register_all(mcp)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
