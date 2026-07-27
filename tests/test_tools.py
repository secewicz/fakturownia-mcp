from pathlib import Path

import pytest

from fakturownia_mcp import config
from fakturownia_mcp.config import ConfigError
from tests.conftest import tool_fn


def test_list_invoices_returns_summaries_with_paging() -> None:
    result = tool_fn("list_invoices")(period="this_month", per_page=25)

    assert result["page"] == 1
    assert result["has_more"] is False  # 1 item < per_page
    (summary,) = result["invoices"]
    assert summary["number"] == "2026/07/01"
    assert summary["buyer_name"] == "ACME Sp. z o.o."
    assert "positions" not in summary  # summaries stay small


def test_get_invoice_returns_full_record() -> None:
    invoice = tool_fn("get_invoice")(invoice_id=1)

    assert invoice["id"] == 1
    assert invoice["price_gross"] == "123.0"


def test_create_invoice_drops_none_fields() -> None:
    invoice = tool_fn("create_invoice")(
        buyer_name="ACME Sp. z o.o.",
        positions=[{"name": "Usługa", "total_price_gross": 123.0, "tax": 23}],
    )

    assert invoice["id"] == 2


def test_change_invoice_status_rejects_unknown_status() -> None:
    with pytest.raises(ValueError, match="Invalid status"):
        tool_fn("change_invoice_status")(invoice_id=1, status="destroyed")


def test_change_invoice_status_ok() -> None:
    assert tool_fn("change_invoice_status")(invoice_id=1, status="paid") == {
        "invoice_id": 1,
        "status": "paid",
    }


def test_download_invoice_pdf_writes_file(tmp_path: Path) -> None:
    target = tmp_path / "faktura.pdf"

    result = tool_fn("download_invoice_pdf")(invoice_id=1, output_path=str(target))

    assert result["path"] == str(target)
    assert target.read_bytes().startswith(b"%PDF")
    assert result["size_bytes"] == target.stat().st_size


def test_client_tools_roundtrip() -> None:
    listed = tool_fn("list_clients")(tax_no="1234567890")
    assert listed["clients"][0]["name"] == "ACME Sp. z o.o."

    assert tool_fn("get_client")(client_id=5)["id"] == 5
    assert tool_fn("create_client")(name="ACME Sp. z o.o.")["id"] == 5
    assert tool_fn("update_client")(client_id=5, fields={"email": "n@acme.pl"})["id"] == 5
    assert tool_fn("delete_client")(client_id=5) == {"deleted_client_id": 5}


def test_product_tools_roundtrip() -> None:
    listed = tool_fn("list_products")()
    assert listed["products"][0]["name"] == "Abonament"

    assert tool_fn("get_product")(product_id=9)["id"] == 9
    assert tool_fn("create_product")(name="Abonament", price_net="89.0")["id"] == 9
    assert tool_fn("update_product")(product_id=9, fields={"price_net": "99.0"})["id"] == 9


def test_missing_env_vars_raise_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    config.set_client(None)
    monkeypatch.delenv("FAKTUROWNIA_DOMAIN", raising=False)
    monkeypatch.delenv("FAKTUROWNIA_API_TOKEN", raising=False)

    with pytest.raises(ConfigError, match="FAKTUROWNIA_DOMAIN"):
        config.get_client()
