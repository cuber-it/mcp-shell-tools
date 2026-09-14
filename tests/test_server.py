"""The server: its arguments, the workspace it builds, and what it publishes.

The tests that need the SDK skip when it is absent, because it is an optional
extra and the package has to be testable without it.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from mcp_shell_tools import server
from mcp_shell_tools.workspace import ToolError, Workspace


def test_stdio_is_the_default() -> None:
    assert server.parse([]).transport == "stdio"


def test_the_http_arguments_are_read() -> None:
    args = server.parse(
        ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "12204"]
    )

    assert args.transport == "streamable-http"
    assert args.host == "0.0.0.0"
    assert args.port == 12204


def test_the_path_defaults_to_mcp_and_can_be_moved() -> None:
    assert server.parse([]).path == "/mcp"
    assert server.parse(["--path", "/shell"]).path == "/shell"


def test_allowed_roots_may_be_repeated() -> None:
    args = server.parse(["--allowed-root", "/one", "--allowed-root", "/two"])

    assert args.allowed_root == ["/one", "/two"]


def test_the_workspace_carries_the_arguments(tmp_path: Path) -> None:
    args = server.parse(
        [
            "--working-dir",
            str(tmp_path),
            "--allowed-root",
            str(tmp_path),
            "--state-dir",
            str(tmp_path / "state"),
        ]
    )

    space = server.workspace_from_args(args)

    assert space.working_dir == tmp_path
    assert space.allowed_roots == (tmp_path,)
    assert space.state_dir == tmp_path / "state"


def test_without_allowed_roots_there_is_no_boundary(tmp_path: Path) -> None:
    space = server.workspace_from_args(server.parse(["--working-dir", str(tmp_path)]))

    assert not space.allowed_roots
    assert space.resolve("/etc") == Path("/etc")


def test_a_working_directory_that_is_no_directory_is_refused(tmp_path: Path) -> None:
    afile = tmp_path / "afile"
    afile.write_text("x", encoding="utf-8")

    with pytest.raises(ToolError):
        server.workspace_from_args(server.parse(["--working-dir", str(afile)]))


def test_the_server_publishes_the_whole_set(tmp_path: Path) -> None:
    pytest.importorskip("mcp.server.mcpserver")

    built = server.build(Workspace(working_dir=tmp_path))

    assert built.name == "mcp-shell-tools"
    assert len(asyncio.run(built.list_tools())) == 33


def test_every_published_tool_carries_its_description(tmp_path: Path) -> None:
    pytest.importorskip("mcp.server.mcpserver")

    built = server.build(Workspace(working_dir=tmp_path))

    published = asyncio.run(built.list_tools())

    assert [tool.name for tool in published if not tool.description] == []


def test_the_server_carries_its_instructions(tmp_path: Path) -> None:
    pytest.importorskip("mcp.server.mcpserver")

    built = server.build(Workspace(working_dir=tmp_path))

    assert built.instructions == server.INSTRUCTIONS


def test_a_tool_call_reaches_the_tools(tmp_path: Path) -> None:
    pytest.importorskip("mcp.server.mcpserver")
    built = server.build(Workspace(working_dir=tmp_path))

    asyncio.run(
        built.call_tool("file_write", {"path": "note.txt", "content": "served"})
    )

    assert (tmp_path / "note.txt").read_text(encoding="utf-8") == "served"


def test_a_refusal_keeps_its_reason(tmp_path: Path) -> None:
    """The SDK blanks a crash but carries its own ToolError through."""
    exceptions = pytest.importorskip("mcp.server.mcpserver.exceptions")
    built = server.build(Workspace(working_dir=tmp_path))

    with pytest.raises(exceptions.ToolError) as refused:
        asyncio.run(built.call_tool("file_read", {"path": "nowhere.txt"}))

    assert not isinstance(refused.value, exceptions.UnexpectedToolError)
    assert "no such file" in str(refused.value)


def test_a_boundary_refusal_keeps_its_reason(tmp_path: Path) -> None:
    exceptions = pytest.importorskip("mcp.server.mcpserver.exceptions")
    built = server.build(
        Workspace(working_dir=tmp_path, allowed_roots=(tmp_path,))
    )

    with pytest.raises(exceptions.ToolError) as refused:
        asyncio.run(built.call_tool("file_read", {"path": "/etc/hostname"}))

    assert not isinstance(refused.value, exceptions.UnexpectedToolError)
    assert "outside the allowed roots" in str(refused.value)
