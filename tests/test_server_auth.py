"""The HTTP server behind authentication, as a started process meets callers.

The server runs as a subprocess against a stand-in authorization server on the
loopback interface, so the whole path is checked: environment, SDK wiring and
what a caller gets back.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from loopback import Issuer, free_port, serve_issuer

REVISION = "2026-07-28"
ACTIVE = {"active": True, "client_id": "claude", "scope": "user"}
STARTUP_SECONDS = 20.0
POLL_SECONDS = 0.05
TOOL_COUNT = 33


@dataclass(frozen=True)
class Served:
    """A running server and the stand-in issuer it asks.

    Attributes:
        issuer: The stand-in authorization server.
        base: Base URL the server listens on.
    """

    issuer: Issuer
    base: str


def _wait_until_listening(
    port: int, process: subprocess.Popen[bytes], log: Path
) -> None:
    """Return once the server accepts connections.

    Raises:
        AssertionError: The process ended or did not listen in time.
    """
    deadline = time.monotonic() + STARTUP_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(f"the server ended: {log.read_text(encoding='utf-8')}")
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(POLL_SECONDS)
    raise AssertionError("the server did not start listening")


@pytest.fixture(scope="module")
def served(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Served]:
    """Run the server with authentication switched on."""
    work = tmp_path_factory.mktemp("work")
    log = work / "server.log"
    with serve_issuer() as issuer, log.open("wb") as output:
        port = free_port()
        base = f"http://127.0.0.1:{port}"
        env = {
            **os.environ,
            "MCP_OAUTH_ENABLED": "true",
            "MCP_OAUTH_SERVER_URL": f"{issuer.url}/",
            "MCP_PUBLIC_URL": f"{base}/",
            "MCP_AUTH_METHOD": "introspection",
        }
        command = [
            sys.executable,
            "-m",
            "mcp_shell_tools.server.app",
            "--transport",
            "streamable-http",
            "--port",
            str(port),
            "--working-dir",
            str(work),
            "--state-dir",
            str(work / "state"),
        ]
        with subprocess.Popen(
            command, env=env, stdout=output, stderr=output
        ) as process:
            try:
                _wait_until_listening(port, process, log)
                yield Served(issuer, base)
            finally:
                process.terminate()


def ask(base: str, token: str | None) -> tuple[int, Any, str]:
    """Send a tools/list request of the current revision.

    Returns:
        Status, headers and body of the answer.
    """
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {
            "_meta": {
                "io.modelcontextprotocol/protocolVersion": REVISION,
                "io.modelcontextprotocol/clientCapabilities": {},
            }
        },
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": REVISION,
        "Mcp-Method": "tools/list",
    }
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{base}/mcp", data=json.dumps(body).encode(), headers=headers
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.headers, response.read().decode()
    except urllib.error.HTTPError as err:
        return err.code, err.headers, err.read().decode()


def tool_names(text: str) -> set[str]:
    """Return the tool names of a tools/list answer, as JSON or as an event.

    Raises:
        AssertionError: The text holds no answer.
    """
    for line in text.splitlines():
        payload = line.removeprefix("data: ")
        if payload.startswith("{"):
            return {tool["name"] for tool in json.loads(payload)["result"]["tools"]}
    raise AssertionError(f"no answer in {text!r}")


def test_a_request_without_a_token_is_pointed_to_the_metadata(served: Served) -> None:
    status, headers, _ = ask(served.base, None)

    assert status == 401
    metadata = f"{served.base}/.well-known/oauth-protected-resource/mcp"
    assert metadata in headers["WWW-Authenticate"]


def test_an_unknown_token_is_refused_after_asking_the_issuer(served: Served) -> None:
    served.issuer.answer = {"active": False}

    status, _, _ = ask(served.base, "unknown-token")

    assert status == 401
    assert "unknown-token" in served.issuer.tokens


def test_a_valid_token_gets_the_tools(served: Served) -> None:
    served.issuer.answer = ACTIVE

    status, _, text = ask(served.base, "valid-token")

    assert status == 200
    assert len(tool_names(text)) == TOOL_COUNT


def test_a_token_without_the_required_scope_is_forbidden(served: Served) -> None:
    served.issuer.answer = {**ACTIVE, "scope": "other"}

    status, headers, _ = ask(served.base, "narrow-token")

    assert status == 403
    assert "insufficient_scope" in headers["WWW-Authenticate"]


def test_the_metadata_names_resource_and_issuer(served: Served) -> None:
    url = f"{served.base}/.well-known/oauth-protected-resource/mcp"
    with urllib.request.urlopen(url, timeout=10) as response:
        document = json.loads(response.read())

    assert document["resource"] == f"{served.base}/mcp"
    assert document["authorization_servers"] == [f"{served.issuer.url}/"]
