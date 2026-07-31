"""Tool registration."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import clients, invoices, payments, products


def register_all(mcp: FastMCP) -> None:
    invoices.register(mcp)
    clients.register(mcp)
    payments.register(mcp)
    products.register(mcp)
