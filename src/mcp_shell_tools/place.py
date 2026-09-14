"""Where the tools are working, and what the project says about itself."""

from __future__ import annotations

from mcp_shell_tools.output import cut, read_text
from mcp_shell_tools.workspace import Workspace

PROJECT_FILE = "CLAUDE.md"
PROJECT_EXCERPT = 4000


def cwd(space: Workspace) -> str:
    """Return the directory the tools are working in."""
    return str(space.working_dir)


def cd(space: Workspace, path: str) -> str:
    """Change the directory the tools work in.

    It holds for every tool sharing this workspace, until it is changed again
    or the process ends.

    Raises:
        ToolError: There is no such directory.
    """
    space.working_dir = space.directory(path)
    return f"working directory is now {space.working_dir}"


def project_context(space: Workspace, path: str = ".") -> str:
    """Return what a directory's CLAUDE.md says.

    Returns:
        The file's beginning, or a line saying there is none.

    Raises:
        ToolError: The directory does not exist, or the file leads outside
            the allowed roots or cannot be read as text.
    """
    root = space.directory(path)
    instructions = space.resolve(str(root / PROJECT_FILE))
    if not instructions.is_file():
        return f"no {PROJECT_FILE} in {root}"
    return cut(read_text(instructions), PROJECT_EXCERPT)
