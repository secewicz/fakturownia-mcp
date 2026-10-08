from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

ROOT = Path(__file__).parent.parent
CLIENT_RELEASE = (
    "fakturownia-client @ git+https://github.com/secewicz/fakturownia-client.git@v0.3.0"
)


def test_runtime_dependency_uses_reviewed_client_release_tag() -> None:
    with (ROOT / "pyproject.toml").open("rb") as file:
        project = tomllib.load(file)["project"]

    assert CLIENT_RELEASE in project["dependencies"]


def test_runtime_dependency_does_not_depend_on_unpublished_pypi_version() -> None:
    with (ROOT / "pyproject.toml").open("rb") as file:
        project = tomllib.load(file)["project"]

    assert "fakturownia-client>=0.3.0" not in project["dependencies"]


def test_invoiceocean_docs_install_the_alias_release_wheel() -> None:
    readme = (ROOT / "aliases" / "invoiceocean-mcp" / "README.md").read_text()

    assert (
        "https://github.com/secewicz/fakturownia-mcp/releases/download/"
        "v0.4.0/invoiceocean_mcp-0.4.0-py3-none-any.whl"
    ) in readme


def test_troubleshooting_does_not_recommend_upstream_pypi_package() -> None:
    readme = (ROOT / "README.md").read_text()

    assert "uvx fakturownia-mcp@latest" not in readme
