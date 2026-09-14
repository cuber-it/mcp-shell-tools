"""Finding files by name and lines by content."""

from __future__ import annotations

import re
from pathlib import Path

from mcp_shell_tools.errors import ToolError
from mcp_shell_tools.output import render, text_or_none
from mcp_shell_tools.workspace import Workspace


def glob_search(space: Workspace, pattern: str, path: str = ".") -> str:
    """Find files whose path below the directory matches a glob pattern.

    Returns:
        The matching paths, one per line, cut at the result limit.

    Raises:
        ToolError: The directory does not exist, or the pattern is not usable.
    """
    root = space.directory(path)
    found = [str(hit) for hit in space.glob(root, pattern)]
    return render(found, space.max_results, f"nothing matches {pattern} under {root}")


def grep(space: Workspace, pattern: str, path: str = ".", glob: str = "**/*") -> str:
    """Find lines matching a regular expression.

    Returns:
        Matching lines as ``file:line: text``, cut at the result limit.

    Raises:
        ToolError: The expression or the glob is not usable, or the path is
            missing.
    """
    try:
        expression = re.compile(pattern)
    except re.error as err:
        raise ToolError(f"not a usable pattern: {err}") from err

    root = space.existing(path)
    candidates = [root] if root.is_file() else space.glob(root, glob)

    hits: list[str] = []
    for candidate in candidates:
        if len(hits) >= space.max_results:
            break
        if candidate.is_file():
            hits.extend(_search(candidate, expression, space.max_results - len(hits)))
    return render(hits, space.max_results, f"no line matches {pattern} under {root}")


def _search(path: Path, expression: re.Pattern[str], room: int) -> list[str]:
    """Return matching lines of one file.

    Returns:
        The hits as ``file:line: text``, unreadable files yield nothing.
    """
    text = text_or_none(path)
    if text is None:
        return []
    hits: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if len(hits) >= room:
            break
        if expression.search(line):
            hits.append(f"{path}:{number}: {line.strip()}")
    return hits
