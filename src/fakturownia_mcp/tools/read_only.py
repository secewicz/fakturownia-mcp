"""Read-only tools for additional Fakturownia API resources."""

from __future__ import annotations

from typing import Annotated, Any

from fakturownia_client.models import ApiRecord
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from fakturownia_mcp import config
from fakturownia_mcp.errors import api_call
from fakturownia_mcp.schemas import DateStr, Page, PerPage, full_record

_READ = ToolAnnotations(readOnlyHint=True, openWorldHint=False)


def _summary(record: ApiRecord) -> dict[str, Any]:
    data = full_record(record)
    fields = (
        "id",
        "name",
        "number",
        "kind",
        "code",
        "warehouse_id",
        "warehouse_document_id",
        "product_id",
        "quantity",
        "date",
        "account_number",
        "currency",
        "event_type",
    )
    return {key: data[key] for key in fields if key in data}


def _list_result(records: list[ApiRecord], key: str, page: int, per_page: int) -> dict[str, Any]:
    return {
        key: [_summary(record) for record in records],
        "page": page,
        "has_more": len(records) == per_page,
    }


async def _get_record(awaitable: Any) -> dict[str, Any]:
    return full_record(await api_call(awaitable))


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=_READ.model_copy(update={"title": "List recurring definitions"}))
    async def list_recurrings(page: Page = 1, per_page: PerPage = 25) -> dict[str, Any]:
        """List recurring invoice definitions as compact summaries. Use this to discover scheduled document templates and their numeric ids; do not use it to list already issued invoices. Returns {"recurrings": [...], "page", "has_more"}; call get_recurring for the full definition."""
        client = await config.get_client()
        records = await api_call(client.list_recurrings(page=page, per_page=per_page))
        return _list_result(records, "recurrings", page, per_page)

    @mcp.tool(annotations=_READ.model_copy(update={"title": "Get recurring definition"}))
    async def get_recurring(recurring_id: int) -> dict[str, Any]:
        """Get one recurring invoice definition by numeric id. Use an id returned by list_recurrings; do not pass an invoice number or schedule label. Returns the full definition with secret and public-link fields redacted."""
        client = await config.get_client()
        return await _get_record(client.get_recurring(recurring_id))

    @mcp.tool(annotations=_READ.model_copy(update={"title": "List price lists"}))
    async def list_price_lists(page: Page = 1, per_page: PerPage = 25) -> dict[str, Any]:
        """List configured price lists as compact summaries. Use this to discover price-list ids before inspecting one; do not confuse these lists with individual products. Returns {"price_lists": [...], "page", "has_more"}; call get_price_list for the full record."""
        client = await config.get_client()
        records = await api_call(client.list_price_lists(page=page, per_page=per_page))
        return _list_result(records, "price_lists", page, per_page)

    @mcp.tool(annotations=_READ.model_copy(update={"title": "Get price list"}))
    async def get_price_list(price_list_id: int) -> dict[str, Any]:
        """Get one price list by numeric id. Use an id returned by list_price_lists; do not pass a product id. Returns the full price-list record with secret and public-link fields redacted."""
        client = await config.get_client()
        return await _get_record(client.get_price_list(price_list_id))

    @mcp.tool(annotations=_READ.model_copy(update={"title": "List warehouses"}))
    async def list_warehouses(page: Page = 1, per_page: PerPage = 25) -> dict[str, Any]:
        """List warehouses as compact summaries. Use this to discover warehouse ids for stock queries; do not use it for warehouse documents or movements. Returns {"warehouses": [...], "page", "has_more"}; call get_warehouse for the full record."""
        client = await config.get_client()
        records = await api_call(client.list_warehouses(page=page, per_page=per_page))
        return _list_result(records, "warehouses", page, per_page)

    @mcp.tool(annotations=_READ.model_copy(update={"title": "Get warehouse"}))
    async def get_warehouse(warehouse_id: int) -> dict[str, Any]:
        """Get one warehouse by numeric id. Use an id returned by list_warehouses; do not pass a warehouse-document id. Returns the full warehouse record with secret and public-link fields redacted."""
        client = await config.get_client()
        return await _get_record(client.get_warehouse(warehouse_id))

    @mcp.tool(annotations=_READ.model_copy(update={"title": "List warehouse documents"}))
    async def list_warehouse_documents(page: Page = 1, per_page: PerPage = 25) -> dict[str, Any]:
        """List warehouse documents as compact summaries. Use this to discover receipt, issue, and transfer document ids; do not use it for individual stock movements. Returns {"warehouse_documents": [...], "page", "has_more"}; call get_warehouse_document for full details."""
        client = await config.get_client()
        records = await api_call(client.list_warehouse_documents(page=page, per_page=per_page))
        return _list_result(records, "warehouse_documents", page, per_page)

    @mcp.tool(annotations=_READ.model_copy(update={"title": "Get warehouse document"}))
    async def get_warehouse_document(warehouse_document_id: int) -> dict[str, Any]:
        """Get one warehouse document by numeric id. Use an id returned by list_warehouse_documents; do not pass its printed document number. Returns the full document with secret and public-link fields redacted."""
        client = await config.get_client()
        return await _get_record(client.get_warehouse_document(warehouse_document_id))

    @mcp.tool(annotations=_READ.model_copy(update={"title": "List warehouse actions"}))
    async def list_warehouse_actions(
        warehouse_id: Annotated[int | None, Field(description="Filter by warehouse id")] = None,
        kind: Annotated[str | None, Field(description="Filter by warehouse action kind")] = None,
        product_id: Annotated[int | None, Field(description="Filter by product id")] = None,
        date_from: DateStr | None = None,
        date_to: DateStr | None = None,
        from_warehouse_document: Annotated[
            int | None, Field(description="First warehouse-document id in a range")
        ] = None,
        to_warehouse_document: Annotated[
            int | None, Field(description="Last warehouse-document id in a range")
        ] = None,
        warehouse_document_id: Annotated[
            int | None, Field(description="Filter by one warehouse-document id")
        ] = None,
        page: Page = 1,
        per_page: PerPage = 25,
    ) -> dict[str, Any]:
        """List stock movements with optional warehouse, product, kind, date, and document filters. Use this for inventory movement history; do not use it to fetch warehouse-document headers. Returns {"warehouse_actions": [...], "page", "has_more"} as compact summaries."""
        client = await config.get_client()
        records = await api_call(
            client.list_warehouse_actions(
                warehouse_id=warehouse_id,
                kind=kind,
                product_id=product_id,
                date_from=date_from,
                date_to=date_to,
                from_warehouse_document=from_warehouse_document,
                to_warehouse_document=to_warehouse_document,
                warehouse_document_id=warehouse_document_id,
                page=page,
                per_page=per_page,
            )
        )
        return _list_result(records, "warehouse_actions", page, per_page)

    @mcp.tool(annotations=_READ.model_copy(update={"title": "List categories"}))
    async def list_categories(page: Page = 1, per_page: PerPage = 25) -> dict[str, Any]:
        """List account categories as compact summaries. Use this to discover category ids used by other records; do not pass category names where ids are required. Returns {"categories": [...], "page", "has_more"}; call get_category for the full record."""
        client = await config.get_client()
        records = await api_call(client.list_categories(page=page, per_page=per_page))
        return _list_result(records, "categories", page, per_page)

    @mcp.tool(annotations=_READ.model_copy(update={"title": "Get category"}))
    async def get_category(category_id: int) -> dict[str, Any]:
        """Get one category by numeric id. Use an id returned by list_categories; do not pass the category name. Returns the full category record with secret and public-link fields redacted."""
        client = await config.get_client()
        return await _get_record(client.get_category(category_id))

    @mcp.tool(annotations=_READ.model_copy(update={"title": "List departments"}))
    async def list_departments(page: Page = 1, per_page: PerPage = 25) -> dict[str, Any]:
        """List departments as compact summaries. Use this to discover seller-department ids for document context; do not confuse departments with issuers. Returns {"departments": [...], "page", "has_more"}; call get_department for the full record."""
        client = await config.get_client()
        records = await api_call(client.list_departments(page=page, per_page=per_page))
        return _list_result(records, "departments", page, per_page)

    @mcp.tool(annotations=_READ.model_copy(update={"title": "Get department"}))
    async def get_department(department_id: int) -> dict[str, Any]:
        """Get one department by numeric id. Use an id returned by list_departments; do not pass an issuer id. Returns the full department record with secret and public-link fields redacted."""
        client = await config.get_client()
        return await _get_record(client.get_department(department_id))

    @mcp.tool(annotations=_READ.model_copy(update={"title": "List issuers"}))
    async def list_issuers(page: Page = 1, per_page: PerPage = 25) -> dict[str, Any]:
        """List invoice issuers as compact summaries. Use this to discover issuer ids and names; do not confuse issuers with account departments. Returns {"issuers": [...], "page", "has_more"}; call get_issuer for the full record."""
        client = await config.get_client()
        records = await api_call(client.list_issuers(page=page, per_page=per_page))
        return _list_result(records, "issuers", page, per_page)

    @mcp.tool(annotations=_READ.model_copy(update={"title": "Get issuer"}))
    async def get_issuer(issuer_id: int) -> dict[str, Any]:
        """Get one issuer by numeric id. Use an id returned by list_issuers; do not pass a department id. Returns the full issuer record with secret and public-link fields redacted."""
        client = await config.get_client()
        return await _get_record(client.get_issuer(issuer_id))

    @mcp.tool(annotations=_READ.model_copy(update={"title": "List bank accounts"}))
    async def list_bank_accounts(page: Page = 1, per_page: PerPage = 25) -> dict[str, Any]:
        """List configured bank accounts as compact summaries. Use this to discover bank-account ids and currencies; do not use it to list banking payments. Returns {"bank_accounts": [...], "page", "has_more"}; call get_bank_account for the full record."""
        client = await config.get_client()
        records = await api_call(client.list_bank_accounts(page=page, per_page=per_page))
        return _list_result(records, "bank_accounts", page, per_page)

    @mcp.tool(annotations=_READ.model_copy(update={"title": "Get bank account"}))
    async def get_bank_account(bank_account_id: int) -> dict[str, Any]:
        """Get one configured bank account by numeric id. Use an id returned by list_bank_accounts; do not pass the account number itself. Returns the full bank-account record with secret and public-link fields redacted."""
        client = await config.get_client()
        return await _get_record(client.get_bank_account(bank_account_id))

    @mcp.tool(annotations=_READ.model_copy(update={"title": "List webhooks"}))
    async def list_webhooks(page: Page = 1, per_page: PerPage = 25) -> dict[str, Any]:
        """List webhook registrations as compact summaries. Use this to inspect configured integrations and discover ids; this read-only tool does not create or change callbacks. Returns {"webhooks": [...], "page", "has_more"}; call get_webhook for the redacted full record."""
        client = await config.get_client()
        records = await api_call(client.list_webhooks(page=page, per_page=per_page))
        return _list_result(records, "webhooks", page, per_page)

    @mcp.tool(annotations=_READ.model_copy(update={"title": "Get webhook"}))
    async def get_webhook(webhook_id: int) -> dict[str, Any]:
        """Get one webhook registration by numeric id. Use an id returned by list_webhooks; this read-only tool does not test or trigger the callback. Returns the full webhook record with secret and public-link fields redacted."""
        client = await config.get_client()
        return await _get_record(client.get_webhook(webhook_id))
