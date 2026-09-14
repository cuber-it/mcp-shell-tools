"""The server: the whole tool set over stdio or HTTP, through the MCP SDK.

This is the only module that imports the SDK. It takes the catalogue from
:mod:`mcp_shell_tools.server.registry` and publishes it, so a change in the SDK
is felt here and nowhere else. The SDK is an optional dependency: install
``mcp-shell-tools[server]`` to get it.
"""

from __future__ import annotations

import argparse
import functools
import sys
from pathlib import Path
from typing import Any

from mcp_shell_tools import __version__
from mcp_shell_tools.boundary import DEFAULT_MODE, MODES
from mcp_shell_tools.errors import ToolError
from mcp_shell_tools.server.registry import Tool, catalogue
from mcp_shell_tools.workspace import Workspace, workspace_from

INSTRUCTIONS = (
    "Workstation tools: files, editing, searching, running commands, notes "
    "that survive a restart, and a look at the machine."
)


def _anticipated(tool: Tool, refusal: type[Exception]) -> Tool:
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
            raise refusal(str(err)) from err

    return translated


def build(space: Workspace) -> Any:
    """Return a server with the whole tool set published on it.

    Raises:
        SystemExit: The SDK is not installed.
    """
    try:
        # Imported here, not at module level: the SDK is an optional extra,
        # and a missing one has to end in a sentence, not a traceback.
        # pylint: disable-next=import-outside-toplevel
        from mcp.server.mcpserver import MCPServer

        # pylint: disable-next=import-outside-toplevel
        from mcp.server.mcpserver.exceptions import ToolError as AnticipatedError
    except ImportError:
        sys.exit(
            "The server needs the MCP SDK:\n    pip install 'mcp-shell-tools[server]'"
        )

    server = MCPServer(
        name="mcp-shell-tools",
        version=__version__,
        instructions=INSTRUCTIONS,
    )
    for name, tool in catalogue(space).items():
        server.add_tool(_anticipated(tool, AnticipatedError), name=name)
    return server


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    """Read the server's arguments."""
    parser = argparse.ArgumentParser(
        prog="mcp-shell-tools",
        description="Serve the workstation tools over MCP.",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="stdio for a client that starts the server itself, "
        "streamable-http to listen on a port (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP: address to bind")
    parser.add_argument("--port", type=int, default=8000, help="HTTP: port to bind")
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
        help="Confine the tools to this directory; repeatable. "
        "Without it they may touch the whole disk.",
    )
    parser.add_argument(
        "--state-dir", default="", help="Where sessions and the trash are written"
    )
    parser.add_argument(
        "--mode",
        choices=MODES,
        default=DEFAULT_MODE,
        help="open ignores the allowed roots, guarded confines deleting and "
        "moving to them, strict confines everything and runs no commands "
        f"(default: {DEFAULT_MODE})",
    )
    return parser.parse_args(argv)


def workspace_from_args(args: argparse.Namespace) -> Workspace:
    """Build the workspace the tools will share.

    Raises:
        ToolError: The working directory does not exist.
    """
    settings: dict[str, Any] = {
        "working_dir": args.working_dir,
        "allowed_roots": args.allowed_root,
        "mode": args.mode,
    }
    if args.state_dir:
        settings["state_dir"] = args.state_dir
    return workspace_from(settings)


def main(argv: list[str] | None = None) -> int:
    """Run the server until it is stopped."""
    args = parse(argv)
    server = build(workspace_from_args(args))

    if args.transport == "stdio":
        server.run("stdio")
        return 0

    # Host, port and path are transport options in mcp 2.x, not server
    # settings, so they are passed to run rather than to the constructor.
    server.run(
        args.transport,
        host=args.host,
        port=args.port,
        streamable_http_path=args.path,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
