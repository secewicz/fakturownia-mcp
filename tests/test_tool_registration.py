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
    "list_payments",
    "create_payment",
    "delete_payment",
    "send_invoice_by_email",
}


async def test_all_tools_registered() -> None:
    async with client_session(mcp._mcp_server) as session:
        tools = await session.list_tools()

    names = {tool.name for tool in tools.tools}
    assert names == EXPECTED_TOOLS
    assert "delete_invoice" not in names  # deliberately excluded as destructive


async def test_tool_annotations() -> None:
    async with client_session(mcp._mcp_server) as session:
        tools = {tool.name: tool for tool in (await session.list_tools()).tools}

    read_only = {t for t in EXPECTED_TOOLS if t.startswith(("list_", "get_"))}
    for name in read_only:
        assert tools[name].annotations.readOnlyHint is True, name
    assert tools["delete_client"].annotations.destructiveHint is True
    assert tools["delete_payment"].annotations.destructiveHint is True
    assert tools["download_invoice_pdf"].annotations.readOnlyHint is False  # writes a file
    for name in EXPECTED_TOOLS:
        expected_open_world = name == "send_invoice_by_email"  # e-mails an external mailbox
        assert tools[name].annotations.openWorldHint is expected_open_world, name
        assert tools[name].annotations.title, name


async def test_docstrings_meet_guidance_bar() -> None:
    async with client_session(mcp._mcp_server) as session:
        tools = (await session.list_tools()).tools

    for tool in tools:
        assert tool.description, tool.name
        sentences = [s for s in tool.description.split(".") if s.strip()]
        assert len(sentences) >= 3, f"{tool.name} description too terse"


async def test_prompts_registered() -> None:
    async with client_session(mcp._mcp_server) as session:
        prompts = (await session.list_prompts()).prompts

    names = {p.name for p in prompts}
    assert names == {"monthly_summary", "chase_unpaid"}
    for prompt in prompts:
        assert prompt.description, prompt.name


async def test_monthly_summary_prompt_renders() -> None:
    async with client_session(mcp._mcp_server) as session:
        result = await session.get_prompt("monthly_summary", {"month": "2026-06"})

    text = result.messages[0].content.text
    assert "2026-06" in text
    assert "list_payments" in text


async def test_list_invoices_roundtrip() -> None:
    async with client_session(mcp._mcp_server) as session:
        result = await session.call_tool("list_invoices", {"period": "this_month"})

    assert not result.isError
    text = "".join(block.text for block in result.content if block.type == "text")
    assert "2026/07/01" in text
