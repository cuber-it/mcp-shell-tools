"""What the package offers a caller who just imported it."""

from __future__ import annotations

from pathlib import Path

import pytest

import mcp_shell_tools
from mcp_shell_tools import ToolError, Workspace, files, workspace_from


def test_everything_promised_is_reachable() -> None:
    missing = [
        name for name in mcp_shell_tools.__all__ if not hasattr(mcp_shell_tools, name)
    ]

    assert missing == []


def test_a_tool_works_through_the_facade(tmp_path: Path) -> None:
    space = Workspace(working_dir=tmp_path)

    files.file_write(space, "note.txt", "content")

    assert files.file_read(space, "note.txt") == "content"


def test_every_group_is_reachable_as_a_module(tmp_path: Path) -> None:
    space = Workspace(working_dir=tmp_path)
    groups = (
        mcp_shell_tools.edit,
        mcp_shell_tools.files,
        mcp_shell_tools.find,
        mcp_shell_tools.notes,
        mcp_shell_tools.place,
        mcp_shell_tools.run,
        mcp_shell_tools.system,
    )

    assert mcp_shell_tools.place.cwd(space) == str(tmp_path)
    assert len(groups) == 7


def test_the_refusal_from_the_facade_is_the_one_the_tools_raise(
    tmp_path: Path,
) -> None:
    space = Workspace(working_dir=tmp_path)

    with pytest.raises(ToolError):
        files.file_read(space, "nowhere.txt")


def test_a_workspace_can_be_built_from_a_mapping(tmp_path: Path) -> None:
    space = workspace_from({"working_dir": str(tmp_path), "max_results": 7})

    assert space.working_dir == tmp_path
    assert space.max_results == 7


def test_the_version_is_a_string() -> None:
    assert isinstance(mcp_shell_tools.__version__, str)
    assert mcp_shell_tools.__version__
