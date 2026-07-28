# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/), versioning: SemVer.

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
