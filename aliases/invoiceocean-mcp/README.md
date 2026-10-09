# invoiceocean-mcp

**Unofficial** MCP (Model Context Protocol) server for
[InvoiceOcean](https://invoiceocean.com) invoicing and account data, including
invoices, clients, products, warehouses, bank accounts, and webhooks, as tools
for Claude and other MCP clients.

> This is a community-maintained project. It is not affiliated with, endorsed
> by, or sponsored by InvoiceOcean or Fakturownia sp. z o.o. "InvoiceOcean"
> and "Fakturownia" are trademarks of their respective owner, used here only
> to indicate compatibility.

This package is an alias for
[`fakturownia-mcp`](https://github.com/secewicz/fakturownia-mcp) —
InvoiceOcean is the international brand of Fakturownia and both run the same
API. It ships the same server under an `invoiceocean-mcp` command:

```bash
claude mcp add invoiceocean \
  -e INVOICEOCEAN_DOMAIN=mycompany.invoiceocean.com \
  -e INVOICEOCEAN_API_TOKEN=... \
  -- uvx --from https://github.com/secewicz/fakturownia-mcp/releases/download/v0.4.1/invoiceocean_mcp-0.4.1-py3-none-any.whl invoiceocean-mcp
```

All environment variables accept the `INVOICEOCEAN_` prefix
(`INVOICEOCEAN_DOMAIN`, `INVOICEOCEAN_API_TOKEN`, `INVOICEOCEAN_TIMEOUT`,
`INVOICEOCEAN_DOWNLOAD_DIR`, `INVOICEOCEAN_SKIP_CONFIRM`). Set the domain to
your full account domain — the server works with every regional brand of the
platform: invoiceocean.com, invoiceocean.de, vosfactures.fr, bitfactura.es
and fakturownia.pl. Full documentation (tools, approval gate) lives in the
[fakturownia-mcp repository](https://github.com/secewicz/fakturownia-mcp).

## License

MIT
