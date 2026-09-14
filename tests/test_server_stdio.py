"""The entry point really starts and answers over stdio.

What a client sees is pinned in `test_server_client.py`, in process. This is
the one thing that cannot be checked that way: that `python -m
mcp_shell_tools.server.app` comes up as a process and answers on its pipes.

The request carries the per-request envelope of protocol revision 2026-07-28.
There is no `initialize` handshake any more — it was removed with SEP-2575, and
on stdio the first request decides the era for the connection.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

pytest.importorskip("mcp")

REVISION = "2026-07-28"
ENVELOPE = {
    "io.modelcontextprotocol/protocolVersion": REVISION,
    "io.modelcontextprotocol/clientCapabilities": {},
}
ANSWER_SECONDS = 30


def ask(method: str, **params: object) -> dict[str, object]:
    """Start the server, send one request, return the answer it prints.

    Raises:
        AssertionError: The server said nothing before it ended.
    """
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": {**params, "_meta": ENVELOPE},
    }
    finished = subprocess.run(
        [sys.executable, "-m", "mcp_shell_tools.server.app", "--working-dir", "/tmp"],
        input=json.dumps(request) + "\n",
        capture_output=True,
        text=True,
        timeout=ANSWER_SECONDS,
        check=False,
    )
    first = finished.stdout.splitlines()[:1]
    assert first, f"the server said nothing, exit status {finished.returncode}"
    return json.loads(first[0])


def test_the_started_process_answers_on_its_pipes() -> None:
    answer = ask("tools/list")

    assert "error" not in answer
    assert len(answer["result"]["tools"]) == 33


def test_the_envelope_is_what_the_server_expects() -> None:
    answer = ask("server/discover")

    assert "error" not in answer
    assert REVISION in answer["result"]["supportedVersions"]
