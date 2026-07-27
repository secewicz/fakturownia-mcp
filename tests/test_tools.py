from pathlib import Path

import pytest

from fakturownia_mcp import config
from fakturownia_mcp.approval import SKIP_ENV
from fakturownia_mcp.config import ConfigError
from tests.conftest import call_tool, elicitation_cb, tool_fn

APPROVE = elicitation_cb()

# -- read tools (no approval gate) --------------------------------------------


async def test_list_invoices_returns_summaries_with_paging() -> None:
    result = await tool_fn("list_invoices")(period="this_month", per_page=25)

    assert result["page"] == 1
    assert result["has_more"] is False  # 1 item < per_page
    (summary,) = result["invoices"]
    assert summary["number"] == "2026/07/01"
    assert summary["buyer_name"] == "ACME Sp. z o.o."
    assert "positions" not in summary  # summaries stay small


async def test_get_invoice_returns_full_record() -> None:
    invoice = await tool_fn("get_invoice")(invoice_id=1)

    assert invoice["id"] == 1
    assert invoice["price_gross"] == "123.0"


async def test_download_invoice_pdf_writes_file(tmp_path: Path) -> None:
    target = tmp_path / "faktura.pdf"

    result = await tool_fn("download_invoice_pdf")(invoice_id=1, output_path=str(target))

    assert result["path"] == str(target)
    assert target.read_bytes().startswith(b"%PDF")
    assert result["size_bytes"] == target.stat().st_size


# -- write tools go through the elicitation approval gate ---------------------


async def test_create_invoice_executes_when_approved() -> None:
    result = await call_tool(
        "create_invoice",
        {
            "buyer_name": "ACME Sp. z o.o.",
            "positions": [{"name": "Usługa", "total_price_gross": 123.0, "tax": 23}],
        },
        elicitation_callback=APPROVE,
    )

    assert not result.isError
    assert result.structuredContent["id"] == 2


async def test_create_invoice_declined_is_an_error_and_makes_no_request() -> None:
    result = await call_tool(
        "create_invoice",
        {"buyer_name": "ACME Sp. z o.o."},
        elicitation_callback=elicitation_cb(action="decline"),
    )

    assert result.isError
    text = "".join(b.text for b in result.content if b.type == "text")
    assert "not approved" in text


async def test_confirm_false_also_denies() -> None:
    result = await call_tool(
        "change_invoice_status",
        {"invoice_id": 1, "status": "paid"},
        elicitation_callback=elicitation_cb(confirm=False),
    )

    assert result.isError


async def test_client_without_elicitation_support_gets_clear_error() -> None:
    result = await call_tool("delete_client", {"client_id": 5})

    assert result.isError
    text = "".join(b.text for b in result.content if b.type == "text")
    assert SKIP_ENV in text


async def test_skip_env_bypasses_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(SKIP_ENV, "1")

    result = await call_tool("delete_client", {"client_id": 5})

    assert not result.isError
    assert result.structuredContent == {"deleted_client_id": 5}


async def test_change_invoice_status_rejects_unknown_status() -> None:
    result = await call_tool(
        "change_invoice_status",
        {"invoice_id": 1, "status": "destroyed"},
        elicitation_callback=APPROVE,
    )

    assert result.isError
    text = "".join(b.text for b in result.content if b.type == "text")
    assert "Invalid status" in text


async def test_write_roundtrip_all_tools_approved() -> None:
    cases = [
        ("update_invoice", {"invoice_id": 1, "fields": {"buyer_email": "n@acme.pl"}}),
        ("change_invoice_status", {"invoice_id": 1, "status": "paid"}),
        ("create_client", {"name": "ACME Sp. z o.o."}),
        ("update_client", {"client_id": 5, "fields": {"email": "n@acme.pl"}}),
        ("delete_client", {"client_id": 5}),
        ("create_product", {"name": "Abonament", "price_net": "89.0"}),
        ("update_product", {"product_id": 9, "fields": {"price_net": "99.0"}}),
    ]
    for name, args in cases:
        result = await call_tool(name, args, elicitation_callback=APPROVE)
        assert not result.isError, f"{name} failed: {result.content}"


# -- config --------------------------------------------------------------------


def test_missing_env_vars_raise_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    config.set_client(None)
    monkeypatch.delenv("FAKTUROWNIA_DOMAIN", raising=False)
    monkeypatch.delenv("FAKTUROWNIA_API_TOKEN", raising=False)

    with pytest.raises(ConfigError, match="FAKTUROWNIA_DOMAIN"):
        config.get_client()
