# invoiceocean-mcp

**Unofficial** MCP (Model Context Protocol) server for
[InvoiceOcean](https://invoiceocean.com) invoicing: invoices, clients and
products as tools for Claude and other MCP clients.

> This is a community-maintained project. It is not affiliated with, endorsed
> by, or sponsored by InvoiceOcean or Fakturownia sp. z o.o. "InvoiceOcean"
> and "Fakturownia" are trademarks of their respective owner, used here only
> to indicate compatibility.

This package is an alias for
[`fakturownia-mcp`](https://pypi.org/project/fakturownia-mcp/) —
InvoiceOcean is the international brand of Fakturownia and both run the same
API. It ships the same server under an `invoiceocean-mcp` command:

```bash
claude mcp add invoiceocean \
  -e FAKTUROWNIA_DOMAIN=mycompany.invoiceocean.com \
  -e FAKTUROWNIA_API_TOKEN=... \
  -- uvx invoiceocean-mcp
```

Set `FAKTUROWNIA_DOMAIN` to your full `*.invoiceocean.com` domain. Full
documentation (tools, approval gate, environment variables) lives in the
[fakturownia-mcp repository](https://github.com/KrzysztofMarmol/fakturownia-mcp).

## License

MIT
