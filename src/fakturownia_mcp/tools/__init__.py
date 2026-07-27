"""Tool registration."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import clients, invoices, products


def register_all(mcp: FastMCP) -> None:
    invoices.register(mcp)
    clients.register(mcp)
    products.register(mcp)
