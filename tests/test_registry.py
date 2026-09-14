"""What the registry publishes on a server.

Driven through a stand-in registrar, so these tests need no SDK — which is the
point of keeping the registration free of it.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from mcp_shell_tools.registry import register
from mcp_shell_tools.workspace import ToolError, Workspace

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


class Registrar:
    """Collects what is published, the way a server would.

    Attributes:
        tools: The published functions by the name they were published under.
    """

    def __init__(self) -> None:
        """Start out with nothing published."""
        self.tools: dict[str, Callable[..., Any]] = {}

    def tool(
        self, name: str | None = None, **_: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Return the decorator that records the function.

        Args:
            name: Name to publish under, or None for the function's own name.

        Returns:
            The decorator.
        """

        def decorate(handler: Callable[..., Any]) -> Callable[..., Any]:
            self.tools[name or handler.__name__] = handler
            return handler

        return decorate


@pytest.fixture
def registrar() -> Registrar:
    """Return a registrar with nothing published yet."""
    return Registrar()


@pytest.fixture
def space(tmp_path: Path) -> Workspace:
    """Return a workspace rooted in a fresh temporary directory."""
    return Workspace(working_dir=tmp_path, state_dir=tmp_path / "state")


def test_the_whole_set_is_published(registrar: Registrar, space: Workspace) -> None:
    register(registrar, space)

    assert set(registrar.tools) == EXPECTED


def test_no_name_carries_a_prefix(registrar: Registrar, space: Workspace) -> None:
    register(registrar, space)

    assert not [name for name in registrar.tools if name.startswith("shell_")]


def test_every_tool_carries_a_description(
    registrar: Registrar, space: Workspace
) -> None:
    register(registrar, space)

    without = [name for name, handler in registrar.tools.items() if not handler.__doc__]

    assert without == []


def test_every_description_carries_the_german_words(
    registrar: Registrar, space: Workspace
) -> None:
    register(registrar, space)

    without = [
        name
        for name, handler in registrar.tools.items()
        if "Auf Deutsch:" not in (handler.__doc__ or "")
    ]

    assert without == []


def test_the_published_tools_do_their_work(
    registrar: Registrar, space: Workspace, tmp_path: Path
) -> None:
    register(registrar, space)

    registrar.tools["file_write"]("note.txt", "content")

    assert registrar.tools["file_read"]("note.txt") == "content"
    assert (tmp_path / "note.txt").is_file()


def test_running_a_command_works_through_the_registrar(
    registrar: Registrar, space: Workspace
) -> None:
    register(registrar, space)

    assert "hello" in registrar.tools["exec"]("echo hello")


def test_the_tools_share_one_workspace(
    registrar: Registrar, space: Workspace, tmp_path: Path
) -> None:
    (tmp_path / "below").mkdir()
    register(registrar, space)

    registrar.tools["cd"]("below")

    assert registrar.tools["cwd"]() == str(tmp_path / "below")
    assert space.working_dir == tmp_path / "below"


def test_a_refusal_reaches_the_caller(
    registrar: Registrar, space: Workspace
) -> None:
    register(registrar, space)

    with pytest.raises(ToolError):
        registrar.tools["file_read"]("nowhere.txt")


def test_the_boundary_holds_through_the_registrar(
    registrar: Registrar, tmp_path: Path
) -> None:
    inside = tmp_path / "inside"
    inside.mkdir()
    space = Workspace(working_dir=inside, allowed_roots=(inside,))
    register(registrar, space)

    with pytest.raises(ToolError):
        registrar.tools["file_read"]("/etc/hostname")
