"""Workstation tools: files, editing, searching, commands, notes, machine.

The tools are plain functions, grouped by subject into one module each. Every
one of them takes the :class:`Workspace` it works against as its first
argument, so the caller holds the state and nothing hides in a module global.

    from pathlib import Path
    from mcp_shell_tools import Workspace, files

    space = Workspace(working_dir=Path.cwd())
    print(files.file_read(space, "README.md"))

Nothing here knows about MCP or any other server. :mod:`mcp_shell_tools.server`
publishes these functions; the library itself never imports it.
"""

from importlib.metadata import PackageNotFoundError, version

from mcp_shell_tools import edit, files, find, notes, place, run, system
from mcp_shell_tools.boundary import Boundary
from mcp_shell_tools.errors import NotPermittedError, OutsideBoundaryError, ToolError
from mcp_shell_tools.workspace import Workspace, workspace_from

try:
    __version__ = version("mcp-shell-tools")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "0.0.0"

__all__ = [
    "Boundary",
    "NotPermittedError",
    "OutsideBoundaryError",
    "ToolError",
    "Workspace",
    "__version__",
    "edit",
    "files",
    "find",
    "notes",
    "place",
    "run",
    "system",
    "workspace_from",
]
