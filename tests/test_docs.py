"""The documentation keeps up with the code."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from mcp_shell_tools import Workspace
from mcp_shell_tools.server import app
from mcp_shell_tools.server.registry import catalogue

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "doc"
REPOSITORY = "https://github.com/cuber-it/mcp-shell-tools/blob/master/"
SOURCES = [
    ROOT / "src/mcp_shell_tools/server/app.py",
    ROOT / "src/mcp_shell_tools/server/auth.py",
]


def test_every_tool_has_its_section_in_the_reference(tmp_path: Path) -> None:
    reference = (DOC / "tools.md").read_text(encoding="utf-8")

    missing = [
        name
        for name in catalogue(Workspace(working_dir=tmp_path))
        if f"### `{name}`" not in reference
    ]

    assert not missing


def test_every_server_option_is_described(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        app.parse(["--help"])
    options = set(re.findall(r"--[a-z][a-z-]+", capsys.readouterr().out)) - {"--help"}
    described = (DOC / "server.md").read_text(encoding="utf-8")

    assert options
    assert sorted(option for option in options if f"`{option}`" not in described) == []


def test_every_environment_variable_is_described() -> None:
    names = set()
    for source in SOURCES:
        names |= set(re.findall(r"MCP_[A-Z_]+", source.read_text(encoding="utf-8")))
    described = (DOC / "server.md").read_text(encoding="utf-8")

    assert names
    assert sorted(name for name in names if f"`{name}`" not in described) == []


@pytest.mark.parametrize("page", [f"doc/{p.name}" for p in DOC.glob("*.md")])
def test_links_between_documents_lead_somewhere(page: str) -> None:
    source = ROOT / page
    targets = re.findall(
        r"\]\(([^)#:]+)(?:#[^)]*)?\)", source.read_text(encoding="utf-8")
    )

    broken = [target for target in targets if not (source.parent / target).exists()]

    assert not broken


def test_the_readme_links_only_absolutely_to_files_that_exist() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    targets = re.findall(r"\]\(([^)]+)\)", readme)

    relative = [target for target in targets if "://" not in target]
    missing = [
        target
        for target in targets
        if target.startswith(REPOSITORY)
        and not (ROOT / target.removeprefix(REPOSITORY)).exists()
    ]

    assert targets
    assert not relative
    assert not missing
