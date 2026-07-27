# fakturownia-mcp

MCP (Model Context Protocol) server exposing a [Fakturownia](https://fakturownia.pl)
(InvoiceOcean) account as tools for Claude: invoices (list/search, create, update,
status changes, PDF download), clients and products.

Built on [`fakturownia-client`](https://github.com/KrzysztofMarmol/fakturownia-client) —
the API token is sent only in the `Authorization: Bearer` header, never in URLs.
All tools are `async` (backed by `AsyncFakturowniaClient`), so concurrent tool
calls don't block the server's event loop.

There is deliberately **no invoice-delete tool** (destructive on financial records);
use `change_invoice_status` instead.

## Approval gate for writes

Every mutating tool (`create_*`, `update_*`, `delete_client`,
`change_invoice_status`) asks for confirmation via **MCP elicitation** before
touching the API — clients with elicitation support (Claude Code, Claude
Desktop, MCP Inspector) show a native approval dialog describing the exact
operation. Declining aborts the call before any request is sent.

For clients without elicitation support, or for trusted automation, set
`FAKTUROWNIA_SKIP_CONFIRM=1` in the server env to disable the gate.

## Tools

| Tool | Description |
|---|---|
| `list_invoices` | Search invoices by period, date range, client, number, kind (summaries + `has_more`) |
| `get_invoice` | Full invoice with positions |
| `create_invoice` | Issue an invoice (buyer by `client_id` or `buyer_*` fields) |
| `update_invoice` | Partial update of invoice fields |
| `change_invoice_status` | `issued` / `sent` / `paid` / `partial` / `rejected` |
| `download_invoice_pdf` | Saves the PDF (default `~/Downloads/faktura-<number>.pdf`) |
| `list_clients` / `get_client` / `create_client` / `update_client` / `delete_client` | Contractor CRUD |
| `list_products` / `get_product` / `create_product` / `update_product` | Product management |

## Setup

Once published to PyPI, no checkout is needed — `uvx fakturownia-mcp` runs the
server directly (use `"command": "uvx", "args": ["fakturownia-mcp"]` in client
configs below instead of the `uv run --directory ...` form).

For development, a sibling checkout of `fakturownia-client` is required
(editable path dependency — see `[tool.uv.sources]` in `pyproject.toml` for the
git alternative):

```bash
git clone https://github.com/KrzysztofMarmol/fakturownia-client
git clone https://github.com/KrzysztofMarmol/fakturownia-mcp
cd fakturownia-mcp && uv sync
```

Configuration (from Fakturownia: Ustawienia → Ustawienia konta → Integracja):

- `FAKTUROWNIA_DOMAIN` — your account subdomain (e.g. `mycompany`)
- `FAKTUROWNIA_API_TOKEN` — API authorization code

### Claude Code

```bash
claude mcp add fakturownia \
  -e FAKTUROWNIA_DOMAIN=mycompany \
  -e FAKTUROWNIA_API_TOKEN=... \
  -- uv run --directory /path/to/fakturownia-mcp fakturownia-mcp
```

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "fakturownia": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/fakturownia-mcp", "fakturownia-mcp"],
      "env": {
        "FAKTUROWNIA_DOMAIN": "mycompany",
        "FAKTUROWNIA_API_TOKEN": "..."
      }
    }
  }
}
```

### MCP Inspector (interactive testing)

```bash
FAKTUROWNIA_DOMAIN=... FAKTUROWNIA_API_TOKEN=... uv run mcp dev src/fakturownia_mcp/server.py
```

## Development

```bash
uv sync --extra dev
uv run ruff check . && uv run mypy && uv run pytest
```

## License

MIT
