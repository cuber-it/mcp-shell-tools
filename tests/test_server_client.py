"""The server as a client sees it, in process.

A client built on the server object speaks to it directly — no port, no
subprocess — and negotiates the current protocol revision while doing it. That
makes this the place to pin what a caller actually receives: the tool set, the
descriptions, the effect of a call, and above all whether a refusal keeps its
reason.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from mcp import Client

from mcp_shell_tools import Boundary, Workspace
from mcp_shell_tools.server import app

CURRENT_REVISION = "2026-07-28"


def served(space: Workspace, work: Callable[[Any], Awaitable[Any]]) -> Any:
    """Run one piece of client work against a server on this workspace."""
    built = app.build(space)

    async def talk() -> Any:
        async with Client(built) as client:
            return await work(client)

    return asyncio.run(talk())


def test_the_current_revision_is_spoken(tmp_path: Path) -> None:
    async def work(client: Any) -> Any:
        return client.protocol_version

    assert served(Workspace(working_dir=tmp_path), work) == CURRENT_REVISION


def test_the_server_names_itself(tmp_path: Path) -> None:
    async def work(client: Any) -> Any:
        return client.server_info

    info = served(Workspace(working_dir=tmp_path), work)

    assert info.name == "mcp-shell-tools"
    assert info.version


def test_the_whole_set_is_offered_with_descriptions(tmp_path: Path) -> None:
    async def work(client: Any) -> Any:
        return await client.list_tools()

    listed = served(Workspace(working_dir=tmp_path), work)

    assert len(listed.tools) == 33
    assert {"file_read", "exec", "sysinfo"} <= {tool.name for tool in listed.tools}
    assert [tool.name for tool in listed.tools if not tool.description] == []


def test_a_call_reaches_the_disk(tmp_path: Path) -> None:
    async def work(client: Any) -> Any:
        return await client.call_tool(
            "file_write", {"path": "note.txt", "content": "served"}
        )

    answer = served(Workspace(working_dir=tmp_path), work)

    assert not answer.is_error
    assert (tmp_path / "note.txt").read_text(encoding="utf-8") == "served"


def test_a_refusal_arrives_with_its_reason(tmp_path: Path) -> None:
    async def work(client: Any) -> Any:
        return await client.call_tool("file_read", {"path": "nowhere.txt"})

    answer = served(Workspace(working_dir=tmp_path), work)

    assert answer.is_error
    assert "no such file" in answer.content[0].text


def test_a_boundary_refusal_arrives_with_its_reason(tmp_path: Path) -> None:
    async def work(client: Any) -> Any:
        return await client.call_tool("file_read", {"path": "/etc/hostname"})

    space = Workspace(working_dir=tmp_path, boundary=Boundary((tmp_path,), "strict"))
    answer = served(space, work)

    assert answer.is_error
    assert "outside the allowed roots" in answer.content[0].text


def test_a_file_that_is_not_text_is_refused_in_words(tmp_path: Path) -> None:
    async def work(client: Any) -> Any:
        return await client.call_tool("head", {"path": "note.txt", "lines": 1})

    (tmp_path / "note.txt").write_bytes(b"\xff\xfe\x00")
    answer = served(Workspace(working_dir=tmp_path), work)

    assert answer.is_error
    assert "not text, or not UTF-8" in answer.content[0].text
