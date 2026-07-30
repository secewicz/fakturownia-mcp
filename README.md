# fakturownia-mcp

[![PyPI](https://img.shields.io/pypi/v/fakturownia-mcp)](https://pypi.org/project/fakturownia-mcp/)
[![CI](https://github.com/KrzysztofMarmol/fakturownia-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/KrzysztofMarmol/fakturownia-mcp/actions/workflows/ci.yml)
[![Python](https://img.shields.io/pypi/pyversions/fakturownia-mcp)](https://pypi.org/project/fakturownia-mcp/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Unofficial** MCP (Model Context Protocol) server exposing a
[Fakturownia](https://fakturownia.pl) (InvoiceOcean) account as tools for
Claude and other MCP clients: invoices (list/search, create, update, status
changes, PDF download), clients and products.

> This is a community-maintained project. It is not affiliated with, endorsed
> by, or sponsored by Fakturownia sp. z o.o. or InvoiceOcean. "Fakturownia"
> and "InvoiceOcean" are trademarks of their respective owner, used here only
> to indicate compatibility. InvoiceOcean users: pass your full
> `*.invoiceocean.com` domain as `FAKTUROWNIA_DOMAIN`, or install the
> [`invoiceocean-mcp`](https://pypi.org/project/invoiceocean-mcp/) alias.

Built on [`fakturownia-client`](https://pypi.org/project/fakturownia-client/) —
the API token is sent only in the `Authorization: Bearer` header, never in URLs.
All tools are `async`, and every write goes through an approval gate.

There is deliberately **no invoice-delete tool** (destructive on financial records);
use `change_invoice_status` instead.

## Compatible platforms

Fakturownia runs the same API under several regional brands — this server
works with all of them; just pass your full account domain:

| Platform | Region | Example `FAKTUROWNIA_DOMAIN` |
|---|---|---|
| fakturownia.pl | Poland | `mycompany` or `mycompany.fakturownia.pl` |
| invoiceocean.com | Global / USA | `mycompany.invoiceocean.com` |
| invoiceocean.de | Germany | `mycompany.invoiceocean.de` |
| vosfactures.fr | France | `mycompany.vosfactures.fr` |
| bitfactura.es | Spain | `mycompany.bitfactura.es` |

A bare account name defaults to `.fakturownia.pl`; any value containing a
dot is used as-is.

## Configuration

Two required environment variables (from your account settings, Integration
section — in Fakturownia: *Ustawienia → Ustawienia konta → Integracja*).
Every variable also accepts the `INVOICEOCEAN_` prefix (e.g.
`INVOICEOCEAN_DOMAIN`); the `FAKTUROWNIA_` form wins when both are set:

| Variable | Required | Meaning |
|---|---|---|
| `FAKTUROWNIA_DOMAIN` | yes | Account subdomain: `mycompany`, `mycompany.fakturownia.pl` and the full URL all work |
| `FAKTUROWNIA_API_TOKEN` | yes | API authorization code (kept out of URLs and logs) |
| `FAKTUROWNIA_SKIP_CONFIRM` | no | `1` disables the write-approval dialog (for automation or clients without elicitation) |
| `FAKTUROWNIA_TIMEOUT` | no | HTTP timeout in seconds (default 30) |
| `FAKTUROWNIA_DOWNLOAD_DIR` | no | Directory PDF downloads are confined to (default `~/Downloads`); paths outside it are rejected and existing files are never overwritten |

## Setup

### Claude Code

```bash
claude mcp add fakturownia \
  -e FAKTUROWNIA_DOMAIN=mycompany \
  -e FAKTUROWNIA_API_TOKEN=... \
  -- uvx fakturownia-mcp
```

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "fakturownia": {
      "command": "/Users/you/.local/bin/uvx",
      "args": ["fakturownia-mcp"],
      "env": {
        "FAKTUROWNIA_DOMAIN": "mycompany",
        "FAKTUROWNIA_API_TOKEN": "..."
      }
    }
  }
}
```

### Any other MCP client / no uv

The server speaks MCP over **stdio**. Any of these commands starts it:

```bash
uvx fakturownia-mcp                  # zero-install, recommended
pip install fakturownia-mcp && fakturownia-mcp
python -m fakturownia_mcp            # after pip install
```

### MCP Inspector (interactive testing)

```bash
npx @modelcontextprotocol/inspector \
  -e FAKTUROWNIA_DOMAIN=... -e FAKTUROWNIA_API_TOKEN=... \
  uvx fakturownia-mcp
```

## Tools

| Tool | Description |
|---|---|
| `list_invoices` | Search by period, date range, client, number, kind; `income=false` lists **cost/expense** invoices; paginated summaries + `has_more` |
| `get_invoice` | Full invoice with positions |
| `create_invoice` 🔒 | Issue an invoice: buyer by `client_id` or `buyer_*` fields, typed positions, any document kind (`vat`, `proforma`, …) |
| `update_invoice` 🔒 | Partial update, e.g. `{"buyer_email": "x@y.pl"}` or `{"approval_status": "verified"}` |
| `change_invoice_status` 🔒 | `issued` / `sent` / `paid` / `partial` / `rejected` |
| `download_invoice_pdf` | Saves the PDF to disk (default `~/Downloads/faktura-<number>.pdf`) |
| `list_clients` / `get_client` | Search contractors by name, tax id (NIP), e-mail |
| `create_client` 🔒 / `update_client` 🔒 / `delete_client` 🔒 | Contractor management |
| `list_products` / `get_product` / `create_product` 🔒 / `update_product` 🔒 | Product management |

Parameters are fully typed (Pydantic) — date patterns, pagination limits and
status enums are enforced in the tool JSON Schema before any API call.

Example prompts once connected:

- *"List my unpaid invoices from this month"*
- *"Show my expenses from June"* → `list_invoices(income=false, ...)`
- *"Issue a VAT invoice for ACME for 'Consulting', 1000 zł net"* → approval dialog → created
- *"Mark invoice 52572/07/2026 as paid"*
- *"Download the PDF of my latest invoice"*

## Approval gate for writes (🔒)

Every mutating tool asks for confirmation via **MCP elicitation** before
touching the API — clients with elicitation support (Claude Code, Claude
Desktop, MCP Inspector) show a native approval dialog describing the exact
operation (e.g. *"create vat invoice for ACME with positions: Consulting"*).
Declining aborts the call before any request is sent.

Clients without elicitation support get a clear error instead; set
`FAKTUROWNIA_SKIP_CONFIRM=1` to run without the gate.

## Troubleshooting

- **"command not found" in Claude Desktop** — GUI apps don't inherit your
  shell's `PATH`; use the full path to `uvx` (`which uvx`).
- **"Missing environment variables" tool error** — the server starts without
  credentials and validates them on first use; check both env vars in your
  client config.
- **HTTP 401 on every call** — wrong `FAKTUROWNIA_API_TOKEN` or wrong account
  subdomain in `FAKTUROWNIA_DOMAIN`.
- **A new release doesn't show up** — `uvx` caches installs; run
  `uvx fakturownia-mcp@latest` once (or pin `fakturownia-mcp==X.Y.Z`).
- **Product price update seems ignored** — Fakturownia quirk: send `price_net`
  and `price_gross` together; a lone `price_net` is ignored by the API.

## License

MIT
