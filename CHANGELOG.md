# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/), versioning: SemVer.

## [0.3.0] - 2026-07-31

### Added
- Payment tools: `list_payments` (with optional embedded invoices),
  `create_payment` (settle one invoice via `invoice_id` or several via
  `invoice_ids`) and `delete_payment` — recording actual money is now
  distinct from `change_invoice_status(status='paid')`.
- `send_invoice_by_email` 🔒: e-mails the invoice PDF to the buyer or up to
  5 explicit recipients (plus CC), with the document variant selectable;
  marked `openWorldHint` (reaches an external mailbox) and always gated by
  approval.
- Two MCP prompts: `monthly_summary` and `chase_unpaid`.
- `.mcpb` bundle attached to every GitHub release — one-click install in
  Claude Desktop (uv-managed runtime, API token stored as a secret field).

### Changed
- Requires `fakturownia-client>=0.2.0` (payments + send_by_email support).

## [0.2.0] - 2026-07-30

### Added
- Two-phase confirmation fallback for clients without elicitation support
  (e.g. Claude Desktop): write tools take an optional `confirm` flag; the
  first call is rejected with instructions and only a repeated call with
  `confirm=true` (after the user agreed in conversation) executes. On
  dialog-capable clients `confirm=true` does not bypass the dialog.

## [0.1.2] - 2026-07-30

### Added
- Every environment variable now also works with the `INVOICEOCEAN_` prefix
  (`INVOICEOCEAN_DOMAIN`, `INVOICEOCEAN_API_TOKEN`, …); the `FAKTUROWNIA_`
  form wins when both are set.
- "Compatible platforms" documentation: fakturownia.pl, invoiceocean.com,
  invoiceocean.de, vosfactures.fr, bitfactura.es (same API, pass the full
  account domain).

## [0.1.1] - 2026-07-30

### Added
- Companion (unofficial) alias package
  [`invoiceocean-mcp`](https://pypi.org/project/invoiceocean-mcp/) with an
  `invoiceocean-mcp` command, published in lockstep from this repository.

### Changed
- Made the unofficial status explicit (README, package descriptions,
  trademark disclaimer).
- Requires `fakturownia-client>=0.1.2` (InvoiceOcean domains supported
  as-is in `normalize_domain`).

## [0.1.0] - 2026-07-28

### Added
- MCP tool annotations on all 15 tools (`readOnlyHint`, `destructiveHint`,
  `idempotentHint`, `openWorldHint`, human titles) so hosts can auto-allow
  reads and highlight destructive operations.
- Tool descriptions rewritten to Anthropic's tool-writing guidance:
  what/when/when-not/returns/example, with workflow hints (dedupe clients
  before create, ids come from list_* tools).
- Steering error messages: 404/422/auth/rate-limit failures now tell the
  agent how to recover instead of dumping raw exceptions.
- `FAKTUROWNIA_TIMEOUT` and `FAKTUROWNIA_DOWNLOAD_DIR` env vars.
- Approval dialogs now show the exact values being written (field=value,
  invoice positions with amounts); `delete_client` shows the client's name.
- `py.typed` marker.

### Fixed
- `download_invoice_pdf` no longer writes to arbitrary paths: writes are
  confined to the download directory and never overwrite existing files.
- The approval gate distinguishes "client lacks elicitation support" (checked
  via declared capabilities) from real errors, and no longer advertises the
  skip switch on unexpected failures.
- The shared API client is closed cleanly via the server lifespan; lazy
  creation is now race-free.
- Write tools return trimmed summaries instead of full record dumps; full
  records from get_* tools have secret share-link fields removed
  (`token`, `view_url`, `panel_url`).

### Changed
- Requires `fakturownia-client>=0.1.0` (retries, PDF validation, typed
  transport errors).
- Dropped the unused `mcp[cli]` extra (faster `uvx` cold start).
- License metadata migrated to PEP 639; version single-sourced from
  `fakturownia_mcp.__version__`.

## [0.0.2] - 2026-07-28

### Changed
- README rewritten for PyPI users; development docs moved to CONTRIBUTING.
- Added `python -m fakturownia_mcp` entry point.

## [0.0.1] - 2026-07-28

### Added
- Initial release: FastMCP stdio server with 15 tools (invoices, clients,
  products), async tools, elicitation-based approval gate for writes.
