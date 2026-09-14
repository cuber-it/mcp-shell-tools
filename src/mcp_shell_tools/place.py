"""Where the tools are working, and what the project says about itself."""

from __future__ import annotations

from mcp_shell_tools.workspace import ToolError, Workspace

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
    target = space.resolve(path)
    if not target.is_dir():
        raise ToolError(f"no such directory: {target}")
    space.working_dir = target
    return f"working directory is now {target}"


def project_context(space: Workspace, path: str = ".") -> str:
    """Return what a directory's CLAUDE.md says.

    Returns:
        The file's beginning, or a line saying there is none.

    Raises:
        ToolError: The directory does not exist.
    """
    root = space.resolve(path)
    if not root.is_dir():
        raise ToolError(f"no such directory: {root}")
    instructions = root / PROJECT_FILE
    if not instructions.is_file():
        return f"no {PROJECT_FILE} in {root}"
    try:
        text = instructions.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        raise ToolError(f"could not read {instructions}: {err}") from err
    if len(text) > PROJECT_EXCERPT:
        return f"{text[:PROJECT_EXCERPT]}\n[... {len(text) - PROJECT_EXCERPT} more]"
    return text
