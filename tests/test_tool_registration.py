from mcp.shared.memory import create_connected_server_and_client_session as client_session

from fakturownia_mcp.server import mcp

EXPECTED_TOOLS = {
    "list_invoices",
    "get_invoice",
    "create_invoice",
    "update_invoice",
    "change_invoice_status",
    "download_invoice_pdf",
    "list_clients",
    "get_client",
    "create_client",
    "update_client",
    "delete_client",
    "list_products",
    "get_product",
    "create_product",
    "update_product",
}


async def test_all_tools_registered() -> None:
    async with client_session(mcp._mcp_server) as session:
        tools = await session.list_tools()

    names = {tool.name for tool in tools.tools}
    assert names == EXPECTED_TOOLS
    assert "delete_invoice" not in names  # deliberately excluded as destructive


async def test_list_invoices_roundtrip() -> None:
    async with client_session(mcp._mcp_server) as session:
        result = await session.call_tool("list_invoices", {"period": "this_month"})

    assert not result.isError
    text = "".join(block.text for block in result.content if block.type == "text")
    assert "2026/07/01" in text
