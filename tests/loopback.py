"""What tests run on the loopback interface: free ports, a stand-in issuer."""

from __future__ import annotations

import json
import socket
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs

POLL_SECONDS = 0.01


def free_port() -> int:
    """Return a loopback port nothing listens on right now."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@dataclass
class Issuer:
    """What the stand-in authorization server answers, and what it was asked.

    Attributes:
        url: Base URL it listens on.
        answer: Object sent back as JSON.
        status: HTTP status sent back.
        body: Raw body sent instead of ``answer`` when set.
        tokens: The tokens it was asked about, in order.
    """

    url: str = ""
    answer: Any = field(default_factory=lambda: {"active": False})
    status: int = 200
    body: bytes | None = None
    tokens: list[str] = field(default_factory=list)

    @property
    def introspection(self) -> str:
        """Return the URL of the introspection endpoint."""
        return f"{self.url}/introspect"


@contextmanager
def serve_issuer() -> Iterator[Issuer]:
    """Run a stand-in authorization server for as long as the block lasts."""
    issuer = Issuer()

    class Introspection(BaseHTTPRequestHandler):
        """Answers every POST from the state of ``issuer``."""

        def do_POST(self) -> None:
            """Record the token asked about and send the configured answer."""
            length = int(self.headers.get("Content-Length", 0))
            form = parse_qs(self.rfile.read(length).decode())
            issuer.tokens.extend(form.get("token", []))
            body = issuer.body
            if body is None:
                body = json.dumps(issuer.answer).encode()
            self.send_response(issuer.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args: Any) -> None:
            """Keep the test output quiet."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Introspection)
    issuer.url = f"http://127.0.0.1:{server.server_address[1]}"
    thread = threading.Thread(
        target=server.serve_forever,
        kwargs={"poll_interval": POLL_SECONDS},
        daemon=True,
    )
    thread.start()
    try:
        yield issuer
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
