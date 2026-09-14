"""What the package offers a caller who just imported it."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import mcp_shell_tools
from mcp_shell_tools import ToolError, Workspace, files, workspace_from

LOADED_SDK = (
    "import sys, mcp_shell_tools, mcp_shell_tools.server.registry; "
    "print(any(name == 'mcp' or name.startswith('mcp.') for name in sys.modules))"
)


def test_everything_promised_is_reachable() -> None:
    missing = [
        name for name in mcp_shell_tools.__all__ if not hasattr(mcp_shell_tools, name)
    ]

    assert missing == []


def test_a_tool_works_through_the_facade(tmp_path: Path) -> None:
    space = Workspace(working_dir=tmp_path)

    files.file_write(space, "note.txt", "content")

    assert files.file_read(space, "note.txt") == "content"


def test_the_refusal_from_the_facade_is_the_one_the_tools_raise(
    tmp_path: Path,
) -> None:
    with pytest.raises(ToolError):
        files.file_read(Workspace(working_dir=tmp_path), "nowhere.txt")


def test_a_workspace_can_be_built_from_a_mapping(tmp_path: Path) -> None:
    space = workspace_from({"working_dir": str(tmp_path), "max_results": 7})

    assert space.working_dir == tmp_path
    assert space.max_results == 7


def test_the_version_is_a_string() -> None:
    assert isinstance(mcp_shell_tools.__version__, str)
    assert mcp_shell_tools.__version__


def test_the_library_and_the_catalogue_do_not_load_the_sdk() -> None:
    finished = subprocess.run(
        [sys.executable, "-c", LOADED_SDK],
        capture_output=True,
        text=True,
        check=True,
    )

    assert finished.stdout.strip() == "False"
