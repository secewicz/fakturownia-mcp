# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup requirement

Development needs a **sibling checkout** of `fakturownia-client` at
`../fakturownia-client` — `[tool.uv.sources]` wires it as an editable path
dependency. CI also has a `test-published` job that resolves the client from
PyPI (`uv sync --no-sources`); remember `--no-sources` on `uv run` there too.

## Commands

```bash
uv sync --extra dev
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest                        # offline; in-memory MCP sessions + MockTransport
uv run pytest tests/test_tools.py::test_create_invoice_executes_when_approved
FAKTUROWNIA_DOMAIN=... FAKTUROWNIA_API_TOKEN=... uv run fakturownia-mcp   # run stdio server
uv build && uv build aliases/invoiceocean-mcp -o dist
```

CI (`ci.yml`) runs the dev matrix (3.10/3.12/3.13, `--cov-fail-under=85`) plus
the published-pair job.

## Architecture

FastMCP stdio server on the **mcp v1 SDK (pinned `<2.0`;** v2 migration is a
known future task). `server.py` builds the `FastMCP` instance with agent-facing
`instructions` and a `lifespan` that closes the shared API client on shutdown.

- `config.py` — env-driven singleton `AsyncFakturowniaClient` with an
  ownership flag: `aclose_client()` only closes clients it created, so tests
  can inject via `set_client()` without the lifespan killing their instance.
  Every env var works with both `FAKTUROWNIA_` and `INVOICEOCEAN_` prefixes
  (`_env()` helper; `FAKTUROWNIA_` wins).
- `tools/{invoices,clients,products}.py` — each exposes `register(mcp)`;
  called once from `server.py` via `tools.register_all`.
- `approval.py` — elicitation gate for every mutating tool. It checks the
  client's declared elicitation capability first (clear error when absent),
  and the dialog message must show the actual values being written
  (`format_fields`). `FAKTUROWNIA_SKIP_CONFIRM=1` bypasses.
- `errors.py` — `api_call()` wraps every client-library call and rephrases
  failures into agent-steering `ToolError`s (e.g. 404 → "ids come from
  list_* tools, not document numbers").
- `schemas.py` — shared `Annotated` parameter types (date pattern, page
  bounds, status Literal, per-entity `*UpdateFields` docs) and
  `full_record()`, which strips secret fields (`token`, `view_url`,
  `panel_url`, `payment_url`) from any full model dump.

Tool design rules (tests in `test_tool_registration.py` enforce them):
- every tool has `ToolAnnotations` (readOnly/destructive/idempotent/openWorld
  + human `title`) and a description of at least 3 sentences following
  what / when to use / when not / returns / example;
- `list_*` return hand-picked summaries with `has_more`; `get_*` return
  redacted full records; write tools return summaries, never full dumps;
- there is deliberately **no `delete_invoice` tool** (status changes instead)
  and no product-delete (endpoint undocumented);
- `download_invoice_pdf` is the one local write: confined to
  `FAKTUROWNIA_DOWNLOAD_DIR` (default `~/Downloads`), rejects escapes, never
  overwrites (numeric suffix).

## Tests

`tests/conftest.py` provides the whole harness: `fake_client` (autouse,
`httpx.MockTransport` with canned routes + `RECORDED` request log),
`call_tool()` (in-memory MCP session; pass `elicitation_cb()` to approve or
decline writes), `tool_fn()` (direct access to the undecorated function) and
`last_request_params()` for asserting wire parameters.

## Releasing

Version lives in `src/fakturownia_mcp/__init__.py` (`__version__`); the alias
`aliases/invoiceocean-mcp/pyproject.toml` must match it exactly (version and
`fakturownia-mcp==<version>` pin) — `publish.yml` fails otherwise. Bump both +
`CHANGELOG.md` → green CI → `git tag vX.Y.Z && git push origin vX.Y.Z`.
Release `fakturownia-client` first when depending on its new features, and
bump the `fakturownia-client>=` floor accordingly.

## Conventions

- Do not add `Co-Authored-By` trailers to commits.
- `gh run view --json conclusion` exits 0 even for failed runs — never use it
  as a `&&` gate; read the conclusion value instead.
- This is an unofficial project: keep the trademark disclaimer wording in
  README/descriptions intact; InvoiceOcean-facing examples use English and
  `mycompany`, not `firma`.
