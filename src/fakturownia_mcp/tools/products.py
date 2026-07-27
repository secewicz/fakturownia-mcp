"""Product tools."""

from __future__ import annotations

from typing import Any

from fakturownia_client.models import Product
from mcp.server.fastmcp import Context, FastMCP

from fakturownia_mcp import config
from fakturownia_mcp.approval import require_approval


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
    @mcp.tool()
    async def list_products(page: int = 1, per_page: int = 25) -> dict[str, Any]:
        """List products. Returns summaries; use get_product for details."""
        products = await config.get_client().list_products(page=page, per_page=per_page)
        return {
            "products": [_summary(p) for p in products],
            "page": page,
            "has_more": len(products) == per_page,
        }

    @mcp.tool()
    async def get_product(product_id: int) -> dict[str, Any]:
        """Get full product details."""
        product = await config.get_client().get_product(product_id)
        return product.model_dump(mode="json", exclude_none=True)

    @mcp.tool()
    async def create_product(
        name: str,
        price_net: float | str | None = None,
        price_gross: float | str | None = None,
        tax: float | str = 23,
        code: str | None = None,
        currency: str | None = None,
        *,
        ctx: Context,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Create a product. Give price_net or price_gross; tax is the VAT rate (e.g. 23)."""
        await require_approval(ctx, f"create product '{name}'")
        payload: dict[str, Any] = {
            "name": name,
            "price_net": price_net,
            "price_gross": price_gross,
            "tax": tax,
            "code": code,
            "currency": currency,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        product = await config.get_client().create_product(payload)
        return product.model_dump(mode="json", exclude_none=True)

    @mcp.tool()
    async def update_product(
        product_id: int,
        fields: dict[str, Any],
        *,
        ctx: Context,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Update selected fields of a product, e.g. {"price_net": "99.0"}."""
        await require_approval(
            ctx, f"update product {product_id}, fields: {', '.join(sorted(fields))}"
        )
        product = await config.get_client().update_product(product_id, fields)
        return product.model_dump(mode="json", exclude_none=True)
