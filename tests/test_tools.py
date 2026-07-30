from pathlib import Path

import pytest

from fakturownia_mcp import config
from fakturownia_mcp.config import ConfigError
from tests.conftest import call_tool, elicitation_cb, last_request_params, result_text, tool_fn

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
    assert "token" not in summary


async def test_list_invoices_income_false_passes_income_no() -> None:
    await tool_fn("list_invoices")(income=False)

    assert last_request_params("/invoices.json")["income"] == "no"


async def test_has_more_true_on_full_page() -> None:
    result = await tool_fn("list_invoices")(per_page=1)

    assert result["has_more"] is True


async def test_get_invoice_full_record_redacts_secrets() -> None:
    invoice = await tool_fn("get_invoice")(invoice_id=1)

    assert invoice["id"] == 1
    assert invoice["price_gross"] == "123.0"
    assert "token" not in invoice
    assert "view_url" not in invoice


async def test_get_client_redacts_secrets() -> None:
    record = await tool_fn("get_client")(client_id=5)

    assert record["id"] == 5
    assert "token" not in record
    assert "panel_url" not in record


async def test_read_tools_never_elicit() -> None:
    for name, args in [
        ("list_invoices", {}),
        ("get_invoice", {"invoice_id": 1}),
        ("list_clients", {}),
        ("get_client", {"client_id": 5}),
        ("list_products", {}),
        ("get_product", {"product_id": 9}),
    ]:
        result = await call_tool(name, args)  # session with NO elicitation support
        assert not result.isError, f"{name} should not require elicitation"


# -- PDF download: confined writes ---------------------------------------------


async def test_download_pdf_default_path_in_download_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(config.ENV_DOWNLOAD_DIR, str(tmp_path))

    result = await tool_fn("download_invoice_pdf")(invoice_id=1)

    assert result["path"] == str(tmp_path / "faktura-2026-07-01.pdf")
    assert Path(result["path"]).read_bytes().startswith(b"%PDF")


async def test_download_pdf_never_overwrites(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(config.ENV_DOWNLOAD_DIR, str(tmp_path))
    (tmp_path / "faktura-2026-07-01.pdf").write_bytes(b"old")

    result = await tool_fn("download_invoice_pdf")(invoice_id=1)

    assert result["path"] == str(tmp_path / "faktura-2026-07-01-1.pdf")
    assert (tmp_path / "faktura-2026-07-01.pdf").read_bytes() == b"old"


async def test_download_pdf_rejects_path_outside_download_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(config.ENV_DOWNLOAD_DIR, str(tmp_path / "allowed"))

    result = await call_tool(
        "download_invoice_pdf", {"invoice_id": 1, "output_path": "/etc/pwned.pdf"}
    )

    assert result.isError
    assert "download directory" in result_text(result)


async def test_download_pdf_relative_path_resolves_inside(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(config.ENV_DOWNLOAD_DIR, str(tmp_path))

    result = await tool_fn("download_invoice_pdf")(invoice_id=1, output_path="sub/inv.pdf")

    assert result["path"] == str(tmp_path / "sub" / "inv.pdf")


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
    assert "token" not in result.structuredContent  # trimmed summary, not a full dump


async def test_create_invoice_declined_is_an_error() -> None:
    result = await call_tool(
        "create_invoice",
        {"buyer_name": "ACME Sp. z o.o."},
        elicitation_callback=elicitation_cb(action="decline"),
    )

    assert result.isError
    assert "did not approve" in result_text(result)


async def test_confirm_false_also_denies() -> None:
    result = await call_tool(
        "change_invoice_status",
        {"invoice_id": 1, "status": "paid"},
        elicitation_callback=elicitation_cb(confirm=False),
    )

    assert result.isError


async def test_no_elicitation_first_call_demands_two_phase_confirm() -> None:
    result = await call_tool("delete_client", {"client_id": 5})

    assert result.isError
    text = result_text(result)
    assert "CONFIRMATION REQUIRED" in text
    assert "confirm=true" in text  # steers the model to the two-phase fallback


async def test_no_elicitation_confirm_true_executes() -> None:
    result = await call_tool("delete_client", {"client_id": 5, "confirm": True})

    assert not result.isError
    assert result.structuredContent == {"deleted_client_id": 5}


async def test_confirm_true_does_not_bypass_elicitation_dialog() -> None:
    result = await call_tool(
        "change_invoice_status",
        {"invoice_id": 1, "status": "paid", "confirm": True},
        elicitation_callback=elicitation_cb(action="decline"),
    )

    assert result.isError  # dialog-capable client: the dialog decision wins


async def test_skip_env_bypasses_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.ENV_SKIP_CONFIRM, "1")

    result = await call_tool("delete_client", {"client_id": 5})

    assert not result.isError
    assert result.structuredContent == {"deleted_client_id": 5}


async def test_update_approval_summary_contains_values() -> None:
    captured: list[str] = []

    async def capturing_cb(context, params):  # noqa: ANN001, ANN202
        from mcp.types import ElicitResult

        captured.append(params.message)
        return ElicitResult(action="accept", content={"confirm": True})

    result = await call_tool(
        "update_client",
        {"client_id": 5, "fields": {"email": "new@acme.pl"}},
        elicitation_callback=capturing_cb,
    )

    assert not result.isError
    assert "email='new@acme.pl'" in captured[0]


async def test_change_invoice_status_rejects_unknown_status_via_schema() -> None:
    result = await call_tool(
        "change_invoice_status",
        {"invoice_id": 1, "status": "destroyed"},
        elicitation_callback=APPROVE,
    )

    assert result.isError  # rejected by the Literal enum in the tool schema


async def test_per_page_above_100_rejected_by_schema() -> None:
    result = await call_tool("list_invoices", {"per_page": 500})

    assert result.isError


async def test_bad_date_format_rejected_by_schema() -> None:
    result = await call_tool("list_invoices", {"date_from": "27-07-2026"})

    assert result.isError


async def test_empty_update_fields_rejected_by_schema() -> None:
    result = await call_tool(
        "update_invoice",
        {"invoice_id": 1, "fields": {}},
        elicitation_callback=APPROVE,
    )

    assert result.isError


async def test_write_roundtrip_all_tools_approved() -> None:
    cases = [
        ("update_invoice", {"invoice_id": 1, "fields": {"buyer_email": "n@acme.pl"}}),
        ("change_invoice_status", {"invoice_id": 1, "status": "paid"}),
        ("create_client", {"name": "ACME Sp. z o.o."}),
        ("update_client", {"client_id": 5, "fields": {"email": "n@acme.pl"}}),
        ("delete_client", {"client_id": 5}),
        ("create_product", {"name": "Abonament", "price_net": "89.0"}),
        (
            "update_product",
            {"product_id": 9, "fields": {"price_net": "99.0", "price_gross": "121.77"}},
        ),
    ]
    for name, args in cases:
        result = await call_tool(name, args, elicitation_callback=APPROVE)
        assert not result.isError, f"{name} failed: {result.content}"


# -- steering errors ------------------------------------------------------------


async def test_not_found_error_steers_to_list_tools() -> None:
    result = await call_tool("get_invoice", {"invoice_id": 999})

    assert result.isError
    text = result_text(result)
    assert "list_" in text  # points the agent at list_* for valid ids


# -- config --------------------------------------------------------------------


def test_missing_env_vars_raise_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    config.set_client(None)
    for name in (
        "FAKTUROWNIA_DOMAIN",
        "FAKTUROWNIA_API_TOKEN",
        "INVOICEOCEAN_DOMAIN",
        "INVOICEOCEAN_API_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ConfigError, match="FAKTUROWNIA_DOMAIN"):
        config._build_client()


def test_invoiceocean_env_aliases_work(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("FAKTUROWNIA_DOMAIN", "FAKTUROWNIA_API_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("INVOICEOCEAN_DOMAIN", "mycompany.invoiceocean.com")
    monkeypatch.setenv("INVOICEOCEAN_API_TOKEN", "tok")

    client = config._build_client()
    assert client.base_url == "https://mycompany.invoiceocean.com"


def test_fakturownia_env_wins_over_invoiceocean(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKTUROWNIA_DOMAIN", "firma")
    monkeypatch.setenv("FAKTUROWNIA_API_TOKEN", "tok")
    monkeypatch.setenv("INVOICEOCEAN_DOMAIN", "other.invoiceocean.com")

    client = config._build_client()
    assert client.base_url == "https://firma.fakturownia.pl"


async def test_skip_confirm_via_invoiceocean_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FAKTUROWNIA_SKIP_CONFIRM", raising=False)
    monkeypatch.setenv("INVOICEOCEAN_SKIP_CONFIRM", "1")

    result = await call_tool("delete_client", {"client_id": 5})

    assert not result.isError
