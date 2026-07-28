import json
from collections.abc import Iterator

import httpx
import pytest
from fakturownia_client import AsyncFakturowniaClient

from fakturownia_mcp import config

INVOICE = {
    "id": 1,
    "number": "2026/07/01",
    "kind": "vat",
    "status": "issued",
    "issue_date": "2026-07-15",
    "buyer_name": "ACME Sp. z o.o.",
    "price_net": "100.0",
    "price_gross": "123.0",
    "currency": "PLN",
    "token": "secret-share-token",
    "view_url": "https://x.fakturownia.net/f/abc",
}
CLIENT = {
    "id": 5,
    "name": "ACME Sp. z o.o.",
    "tax_no": "1234567890",
    "email": "a@acme.pl",
    "token": "secret-client-token",
    "panel_url": "https://x.fakturownia.pl/panel/abc",
}
PRODUCT = {"id": 9, "name": "Abonament", "price_net": "89.0", "tax": "23"}

RECORDED: list[httpx.Request] = []


def _handler(request: httpx.Request) -> httpx.Response:
    RECORDED.append(request)
    path = request.url.path
    method = request.method
    routes = {
        ("GET", "/invoices.json"): [INVOICE],
        ("GET", "/invoices/1.json"): INVOICE,
        ("POST", "/invoices.json"): {**INVOICE, "id": 2},
        ("PUT", "/invoices/1.json"): INVOICE,
        ("POST", "/invoices/1/change_status.json"): {"code": "success"},
        ("GET", "/clients.json"): [CLIENT],
        ("GET", "/clients/5.json"): CLIENT,
        ("POST", "/clients.json"): CLIENT,
        ("PUT", "/clients/5.json"): CLIENT,
        ("DELETE", "/clients/5.json"): {},
        ("GET", "/products.json"): [PRODUCT],
        ("GET", "/products/9.json"): PRODUCT,
        ("POST", "/products.json"): PRODUCT,
        ("PUT", "/products/9.json"): PRODUCT,
    }
    if (method, path) == ("GET", "/invoices/1.pdf"):
        return httpx.Response(200, content=b"%PDF-1.7 fake")
    if (method, path) in routes:
        return httpx.Response(200, json=routes[(method, path)])
    return httpx.Response(404, json={"code": "error", "message": f"no route {method} {path}"})


@pytest.fixture(autouse=True)
def fake_client() -> Iterator[AsyncFakturowniaClient]:
    RECORDED.clear()
    client = AsyncFakturowniaClient(
        "testfirma", "secret-token", max_retries=0, transport=httpx.MockTransport(_handler)
    )
    config.set_client(client)
    yield client
    config.set_client(None)


def tool_fn(name: str):  # noqa: ANN201 - test helper
    """Return the plain function behind a registered FastMCP tool."""
    from fakturownia_mcp.server import mcp

    return mcp._tool_manager.get_tool(name).fn


def elicitation_cb(action: str = "accept", confirm: bool = True):  # noqa: ANN201
    """Build a client-side elicitation callback with a fixed answer."""
    from mcp.types import ElicitResult

    async def cb(context, params):  # noqa: ANN001, ANN202
        if action == "accept":
            return ElicitResult(action="accept", content={"confirm": confirm})
        return ElicitResult(action=action)

    return cb


async def call_tool(name: str, args: dict, elicitation_callback=None):  # noqa: ANN001, ANN201
    """Round-trip a tool call through an in-memory MCP session."""
    from mcp.shared.memory import (
        create_connected_server_and_client_session as client_session,
    )

    from fakturownia_mcp.server import mcp

    async with client_session(
        mcp._mcp_server, elicitation_callback=elicitation_callback
    ) as session:
        return await session.call_tool(name, args)


def result_text(result) -> str:  # noqa: ANN001
    return "".join(block.text for block in result.content if block.type == "text")


def last_request_params(path: str) -> dict:
    """Query params of the most recent recorded request to the given path."""
    for request in reversed(RECORDED):
        if request.url.path == path:
            return dict(request.url.params)
    raise AssertionError(
        f"no recorded request to {path}: {json.dumps([str(r.url) for r in RECORDED])}"
    )
