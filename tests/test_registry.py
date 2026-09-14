"""What the catalogue hands a server.

No server is involved: the catalogue is plain data, which is the point of
keeping it free of any server library.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_shell_tools import ToolError, Workspace
from mcp_shell_tools.server.registry import Catalogue, catalogue

EXPECTED = {
    "file_read",
    "file_write",
    "file_append",
    "file_list",
    "file_delete",
    "file_move",
    "file_copy",
    "tree",
    "file_info",
    "head",
    "tail",
    "str_replace",
    "diff_preview",
    "find_replace",
    "glob_search",
    "grep",
    "exec",
    "env",
    "set_env",
    "which",
    "ps",
    "sysinfo",
    "port_check",
    "disk_usage",
    "cwd",
    "cd",
    "project_context",
    "memory_add",
    "memory_show",
    "memory_clear",
    "session_save",
    "session_resume",
    "session_list",
}


@pytest.fixture
def tools(space: Workspace) -> Catalogue:
    """Return the catalogue bound to a fresh workspace."""
    return catalogue(space)


def test_the_whole_set_is_in_the_catalogue(tools: Catalogue) -> None:
    assert set(tools) == EXPECTED


def test_every_tool_carries_a_description(tools: Catalogue) -> None:
    assert [name for name, tool in tools.items() if not tool.__doc__] == []


def test_every_description_carries_the_german_words(tools: Catalogue) -> None:
    without = [
        name for name, tool in tools.items() if "Auf Deutsch:" not in tool.__doc__
    ]

    assert without == []


def test_the_tools_do_their_work(tools: Catalogue, tmp_path: Path) -> None:
    tools["file_write"]("note.txt", "content")

    assert tools["file_read"]("note.txt") == "content"
    assert (tmp_path / "note.txt").is_file()


def test_exec_runs_a_command(tools: Catalogue) -> None:
    assert tools["exec"]("echo hello") == "hello\n"


def test_the_tools_share_one_workspace(
    tools: Catalogue, space: Workspace, tmp_path: Path
) -> None:
    (tmp_path / "below").mkdir()

    tools["cd"]("below")

    assert tools["cwd"]() == str(tmp_path / "below")
    assert space.working_dir == tmp_path / "below"


def test_a_refusal_reaches_the_caller(tools: Catalogue) -> None:
    with pytest.raises(ToolError):
        tools["file_read"]("nowhere.txt")


def test_the_boundary_holds_through_the_catalogue(bounded: Workspace) -> None:
    with pytest.raises(ToolError, match="outside the allowed roots"):
        catalogue(bounded)["file_read"]("/etc/hostname")
