import json
from collections.abc import Iterator

import httpx
import pytest
from fakturownia_client import FakturowniaClient

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
}
CLIENT = {"id": 5, "name": "ACME Sp. z o.o.", "tax_no": "1234567890", "email": "a@acme.pl"}
PRODUCT = {"id": 9, "name": "Abonament", "price_net": "89.0", "tax": "23"}


def _handler(request: httpx.Request) -> httpx.Response:
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
def fake_client() -> Iterator[FakturowniaClient]:
    client = FakturowniaClient("testfirma", "secret-token", transport=httpx.MockTransport(_handler))
    config.set_client(client)
    yield client
    config.set_client(None)


def tool_fn(name: str):  # noqa: ANN201 - test helper
    """Return the plain function behind a registered FastMCP tool."""
    from fakturownia_mcp.server import mcp

    return mcp._tool_manager.get_tool(name).fn


def parse_result_text(result) -> object:  # noqa: ANN001 - mcp CallToolResult
    text = "".join(block.text for block in result.content if block.type == "text")
    return json.loads(text) if text else None
