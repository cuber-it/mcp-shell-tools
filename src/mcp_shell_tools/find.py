"""Finding files by name and lines by content."""

from __future__ import annotations

import re
from pathlib import Path

from mcp_shell_tools.workspace import SKIPPED, ToolError, Workspace, render


def glob_search(space: Workspace, pattern: str, path: str = ".") -> str:
    """Find files whose name matches a pattern.

    Returns:
        The matching paths, one per line, cut at the result limit.

    Raises:
        ToolError: The directory does not exist.
    """
    root = space.resolve(path)
    if not root.is_dir():
        raise ToolError(f"no such directory: {root}")
    found = [
        str(hit)
        for hit in sorted(root.glob(pattern))
        if not _is_skipped(hit)
    ]
    return render(found, space.max_results, f"nothing matches {pattern} under {root}")


def grep(
    space: Workspace, pattern: str, path: str = ".", glob: str = "**/*"
) -> str:
    """Find lines matching a regular expression.

    Returns:
        Matching lines as ``file:line: text``, cut at the result limit.

    Raises:
        ToolError: The pattern is not a valid expression, or the path is
            missing.
    """
    try:
        expression = re.compile(pattern)
    except re.error as err:
        raise ToolError(f"not a usable pattern: {err}") from err

    root = space.resolve(path)
    if not root.exists():
        raise ToolError(f"no such path: {root}")
    files = [root] if root.is_file() else sorted(root.glob(glob))

    hits: list[str] = []
    for candidate in files:
        if len(hits) >= space.max_results:
            break
        if not candidate.is_file() or _is_skipped(candidate):
            continue
        hits.extend(_search(candidate, expression, space.max_results - len(hits)))
    return render(hits, space.max_results, f"no line matches {pattern} under {root}")


def _search(path: Path, expression: re.Pattern[str], room: int) -> list[str]:
    """Return matching lines of one file.

    Returns:
        The hits as ``file:line: text``, unreadable files yield nothing.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    hits = []
    for number, line in enumerate(text.splitlines(), start=1):
        if len(hits) >= room:
            break
        if expression.search(line):
            hits.append(f"{path}:{number}: {line.strip()}")
    return hits


def _is_skipped(path: Path) -> bool:
    """Say whether a path lies in a directory nobody wants searched."""
    return any(part in SKIPPED for part in path.parts)
