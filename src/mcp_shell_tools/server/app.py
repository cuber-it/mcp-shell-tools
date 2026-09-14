"""The server: the whole tool set over stdio or HTTP, through the MCP SDK.

This is the only module that imports the SDK. It takes the catalogue from
:mod:`mcp_shell_tools.server.registry` and the authentication from
:mod:`mcp_shell_tools.server.auth` and hands both to the SDK, so a change in
the SDK is felt here and nowhere else.
"""

from __future__ import annotations

import argparse
import functools
import os
import sys
from pathlib import Path
from typing import Any

from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError as AnticipatedError

from mcp_shell_tools import __version__
from mcp_shell_tools.boundary import DEFAULT_MODE, MODES
from mcp_shell_tools.errors import ToolError
from mcp_shell_tools.grant import DEFAULT_STATE_DIR
from mcp_shell_tools.server.auth import (
    AuthConfig,
    ConfigurationError,
    TokenCheck,
    auth_from_environment,
    guard_exposure,
)
from mcp_shell_tools.server.registry import Tool, catalogue
from mcp_shell_tools.workspace import Workspace, workspace_from

INSTRUCTIONS = (
    "Workstation tools: files, editing, searching, running commands, notes "
    "that survive a restart, and a look at the machine. By default reading "
    "reaches the whole system, writing, deleting and moving stay inside the "
    "allowed roots, and shell commands are off. A refusal names the grant "
    "command (scripts/grant.sh) that lifts it; a person runs it on the "
    "host.\n\n"
    "Arbeitsplatz-Werkzeuge: Dateien, Bearbeiten, Suchen, Befehle, Notizen, "
    "die einen Neustart überdauern, und ein Blick auf den Rechner. Standardmäßig "
    "reicht Lesen durch das ganze System, Schreiben, Löschen und Verschieben "
    "bleiben in den erlaubten Wurzeln, und Shell-Befehle sind aus. Eine "
    "Ablehnung nennt den Freigabe-Befehl (scripts/grant.sh), der sie "
    "aufhebt; ausführen "
    "muss ihn ein Mensch auf dem Host."
)
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
REFUSED = 2


def _anticipated(tool: Tool) -> Tool:
    """Wrap a tool so that its refusals reach the caller with their reason.

    The SDK tells a deliberate refusal from a crash by the exception class:
    its own ``ToolError`` reaches the caller carrying its message, while
    anything else is a crash and the caller is told no more than "Error
    executing tool <name>". The tools raise our own ``ToolError``, which would
    land in that second case. This translates those, and only those: a real
    crash stays a crash.

    ``functools.wraps`` carries name, docstring and signature over, and the
    SDK builds description and input schema from them.
    """

    @functools.wraps(tool)
    def translated(*args: Any, **kwargs: Any) -> str:
        try:
            return tool(*args, **kwargs)
        except ToolError as err:
            raise AnticipatedError(str(err)) from err

    return translated


class _Verifier:
    """Answers the SDK's question about a token by asking a :class:`TokenCheck`."""

    def __init__(self, check: TokenCheck) -> None:
        """Bind the verifier to the check it asks."""
        self._check = check

    async def verify_token(self, token: str) -> AccessToken | None:
        """Return the SDK's access token for a valid token, None otherwise."""
        info = await self._check.check(token)
        if info is None:
            return None
        return AccessToken(
            token=token,
            client_id=info.client_id,
            scopes=list(info.scopes),
            subject=info.subject,
            expires_at=info.expires_at,
        )


def _auth_arguments(auth: AuthConfig | None) -> dict[str, Any]:
    """Translate the authentication for the SDK's constructor.

    Resource validation stays off. Whether the authorization server names the
    resource a token was issued for is not established, and switching it on
    without that would reject every token.
    """
    if auth is None:
        return {}
    return {
        "token_verifier": _Verifier(auth.check),
        "auth": AuthSettings(
            issuer_url=auth.issuer_url,
            resource_server_url=auth.resource_url,
            required_scopes=list(auth.required_scopes),
            validate_token_resource=False,
        ),
    }


def build(space: Workspace, auth: AuthConfig | None = None) -> MCPServer:
    """Return a server with the whole tool set published on it.

    With ``auth``, every HTTP request has to carry a bearer token the check
    accepts, and the server publishes its protected resource metadata. stdio
    is not affected, because a pipe carries no token.
    """
    server = MCPServer(
        name="mcp-shell-tools",
        version=__version__,
        instructions=INSTRUCTIONS,
        **_auth_arguments(auth),
    )
    for name, tool in catalogue(space).items():
        server.add_tool(_anticipated(tool), name=name)
    return server


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    """Read the server's arguments; host and port default to the environment."""
    parser = argparse.ArgumentParser(
        prog="mcp-shell-tools",
        description="Serve the workstation tools over MCP. Authentication is "
        "read from MCP_OAUTH_ENABLED, MCP_OAUTH_SERVER_URL, MCP_PUBLIC_URL and "
        "MCP_AUTH_METHOD.",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="stdio for a client that starts the server itself, "
        "streamable-http to listen on a port (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_HOST", DEFAULT_HOST),
        help="HTTP: address to bind (default: MCP_HOST or 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_PORT", DEFAULT_PORT)),
        help="HTTP: port to bind (default: MCP_PORT or 8000)",
    )
    parser.add_argument(
        "--path", default="/mcp", help="HTTP: path the server answers on"
    )
    parser.add_argument(
        "--working-dir",
        default=str(Path.cwd()),
        help="Where the tools start out (default: the current directory)",
    )
    parser.add_argument(
        "--allowed-root",
        action="append",
        default=[],
        metavar="PATH",
        help="An allowed root; repeatable (default: the home directory)",
    )
    parser.add_argument(
        "--state-dir",
        default=DEFAULT_STATE_DIR,
        help="Where sessions, the trash and the grant are kept; empty for none "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--mode",
        choices=MODES,
        default=DEFAULT_MODE,
        help="open ignores the allowed roots, guarded confines writing, deleting "
        "and moving to them, strict confines reading too "
        f"(default: {DEFAULT_MODE})",
    )
    parser.add_argument(
        "--exec",
        action="store_true",
        help="Let shell commands run without a grant",
    )
    return parser.parse_args(argv)


def workspace_from_args(args: argparse.Namespace) -> Workspace:
    """Build the workspace the tools will share.

    Raises:
        ToolError: The working directory does not exist.
    """
    settings: dict[str, Any] = {
        "working_dir": args.working_dir,
        "allowed_roots": args.allowed_root or [str(Path.home())],
        "mode": args.mode,
        "execute": args.exec,
    }
    if args.state_dir:
        settings["state_dir"] = args.state_dir
    return workspace_from(settings)


def main(argv: list[str] | None = None) -> int:
    """Run the server until it is stopped.

    Returns:
        0 after the server stopped, 2 when the configuration was refused
        before it started.
    """
    args = parse(argv)
    try:
        auth = auth_from_environment(os.environ, args.path)
        guard_exposure(args.transport, args.host, auth)
        space = workspace_from_args(args)
    except (ConfigurationError, ToolError) as err:
        print(f"mcp-shell-tools: {err}", file=sys.stderr)
        return REFUSED

    server = build(space, auth)
    if args.transport == "stdio":
        server.run("stdio")
        return 0

    # Sessionless: nothing ties a caller to this process between requests,
    # and a client of the older revision gets no session to lose either.
    server.run(
        "streamable-http",
        host=args.host,
        port=args.port,
        streamable_http_path=args.path,
        stateless_http=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
