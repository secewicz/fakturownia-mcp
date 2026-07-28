# Contributing / Development

Clone both repos side by side — `fakturownia-client` is wired as an editable
path dependency via `[tool.uv.sources]` (see `pyproject.toml` for the git
alternative):

```bash
git clone https://github.com/KrzysztofMarmol/fakturownia-client
git clone https://github.com/KrzysztofMarmol/fakturownia-mcp
cd fakturownia-mcp
uv sync --extra dev
```

Checks (all must pass; CI runs the same set on release tags):

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest
```

Run your development copy in Claude Code with

```bash
claude mcp add fakturownia-dev \
  -e FAKTUROWNIA_DOMAIN=... -e FAKTUROWNIA_API_TOKEN=... \
  -- uv run --directory /path/to/fakturownia-mcp fakturownia-mcp
```

## Releasing

1. Bump `version` in `pyproject.toml` and `__version__` in
   `src/fakturownia_mcp/__init__.py`.
2. Commit, then `git tag vX.Y.Z && git push origin vX.Y.Z`.
3. The `publish.yml` workflow tests, builds and uploads to PyPI
   (requires the `PYPI_API_TOKEN` repository secret).

Release `fakturownia-client` first when the server depends on new client
features.
