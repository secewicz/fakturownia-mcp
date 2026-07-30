"""Product tools."""

from __future__ import annotations

from typing import Annotated, Any

from fakturownia_client.models import Product
from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from fakturownia_mcp import config
from fakturownia_mcp.approval import format_fields, require_approval
from fakturownia_mcp.errors import api_call
from fakturownia_mcp.schemas import (
    ConfirmFlag,
    Page,
    PerPage,
    ProductUpdateFields,
    TaxRate,
    full_record,
)

Price = Annotated[float | str | None, Field(description="Amount, e.g. 99.99 or '99.99'")]

_READ = ToolAnnotations(readOnlyHint=True, openWorldHint=False)


def _summary(product: Product) -> dict[str, Any]:
    return {
        "id": product.id,
        "name": product.name,
        "code": product.code,
        "price_net": product.price_net,
        "price_gross": product.price_gross,
        "tax": product.tax,
        "currency": product.currency,
    }


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=_READ.model_copy(update={"title": "List products"}))
    async def list_products(page: Page = 1, per_page: PerPage = 25) -> dict[str, Any]:
        """List the account's products (price-list items) as summaries.

        The API offers no name/code filter for products — paginate and match
        locally when looking for a specific one. Product ids feed
        create_invoice positions (product_id) and the other product tools.

        Returns {"products": [{id, name, code, price_net, price_gross, tax,
        currency}], "page", "has_more"}; use get_product(product_id) for the
        full record.
        """
        client = await config.get_client()
        products = await api_call(client.list_products(page=page, per_page=per_page))
        return {
            "products": [_summary(p) for p in products],
            "page": page,
            "has_more": len(products) == per_page,
        }

    @mcp.tool(annotations=_READ.model_copy(update={"title": "Get product"}))
    async def get_product(product_id: int) -> dict[str, Any]:
        """Get the full record of one product.

        Call this for details a list_products summary lacks (units, warehouse
        fields, descriptions). product_id is the numeric id from list_products.
        Returns the complete record as stored in Fakturownia.
        """
        client = await config.get_client()
        record = await api_call(client.get_product(product_id))
        return full_record(record)

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Create product",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        )
    )
    async def create_product(
        name: Annotated[str, Field(min_length=1, description="Product name")],
        price_net: Price = None,
        price_gross: Price = None,
        tax: TaxRate = 23,
        code: Annotated[str | None, Field(description="Product code/SKU")] = None,
        currency: Annotated[str | None, Field(description="Currency code, e.g. PLN")] = None,
        confirm: ConfirmFlag = False,
        *,
        ctx: Context,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Create a new product (price-list item) in the account.

        Provide price_net or price_gross — the other is derived from the VAT
        rate. Check list_products first to avoid duplicating an existing item.
        The user approves the creation (with values) in a dialog before anything
        is written.

        Returns a summary with the new product's id.
        Example: create_product(name="Abonament", price_net="89.0", tax=23).
        """
        payload: dict[str, Any] = {
            "name": name,
            "price_net": price_net,
            "price_gross": price_gross,
            "tax": tax,
            "code": code,
            "currency": currency,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        await require_approval(ctx, f"create product: {format_fields(payload)}", confirm=confirm)
        client = await config.get_client()
        record = await api_call(client.create_product(payload))
        return _summary(record)

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Update product",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    async def update_product(
        product_id: int,
        fields: ProductUpdateFields,
        confirm: ConfirmFlag = False,
        *,
        ctx: Context,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Update selected fields of an existing product (partial update).

        API caveat: to change the price you MUST send price_net and price_gross
        together — the API silently ignores a lone price_net. The user approves
        the exact values in a dialog first. Returns a summary of the updated
        product. Example: update_product(product_id=9,
        fields={"price_net": "99.0", "price_gross": "121.77"}).
        """
        await require_approval(
            ctx, f"update product {product_id}: {format_fields(fields)}", confirm=confirm
        )
        client = await config.get_client()
        record = await api_call(client.update_product(product_id, fields))
        return _summary(record)
