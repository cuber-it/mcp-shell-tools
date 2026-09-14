"""Changing text in a file, and looking at a change before making it."""

from __future__ import annotations

import difflib
from pathlib import Path

from mcp_shell_tools.workspace import SKIPPED, ToolError, Workspace, read_text


def str_replace(space: Workspace, path: str, old: str, new: str) -> str:
    """Replace a passage in a file, once and only once.

    The passage has to appear exactly one time. Anything else is refused: no
    match means the caller is looking at a different file than they think, and
    several matches mean the change is ambiguous.

    Raises:
        ToolError: The passage is missing, ambiguous, or the file is
            unreadable.
    """
    target = space.resolve(path)
    text = read_text(space, path)
    found = text.count(old)
    if found == 0:
        raise ToolError(f"passage not found in {target}")
    if found > 1:
        raise ToolError(f"passage appears {found} times in {target}, must be one")
    try:
        target.write_text(text.replace(old, new, 1), encoding="utf-8")
    except OSError as err:
        raise ToolError(f"could not write {target}: {err}") from err
    return f"replaced one passage in {target}"


def diff_preview(space: Workspace, path: str, content: str) -> str:
    """Show what writing this content would change, without writing it.

    Returns:
        A unified diff, or a line saying nothing would change.

    Raises:
        ToolError: The file exists but cannot be read as text.
    """
    target = space.resolve(path)
    before = read_text(space, path) if target.exists() else ""
    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        content.splitlines(keepends=True),
        fromfile=f"{target} (current)",
        tofile=f"{target} (proposed)",
    )
    rendered = "".join(diff)
    return space.cut(rendered) if rendered else f"{target} would not change"


def find_replace(
    space: Workspace,
    old: str,
    new: str,
    path: str = ".",
    glob: str = "*",
    *,
    apply: bool = False,
) -> str:
    """Replace a passage in every matching file, dry run by default.

    Nothing is written unless apply is true. A run across many files is the
    kind of change one wants to read before it happens.

    Returns:
        One line per affected file with the number of replacements, and a
        closing line saying whether anything was written.

    Raises:
        ToolError: The path does not exist, or a file cannot be written.
    """
    root = space.resolve(path)
    if not root.exists():
        raise ToolError(f"no such path: {root}")

    targets = [root] if root.is_file() else sorted(root.rglob(glob))
    targets = [t for t in targets if not any(part in SKIPPED for part in t.parts)]
    hits = _replace_in(targets, old, new, apply, space.max_results)

    if not hits:
        return f"'{old}' appears in no file under {root}"

    lines = [f"{count:>5}x  {target}" for target, count in hits]
    total = sum(count for _, count in hits)
    verb = "replaced" if apply else "would replace"
    lines.append(f"{verb} {total} occurrences in {len(hits)} files")
    if not apply:
        lines.append("nothing was written; call again with apply=true")
    return space.cut("\n".join(lines))


def _replace_in(
    targets: list[Path], old: str, new: str, apply: bool, limit: int
) -> list[tuple[Path, int]]:
    """Count and optionally perform the replacement in each readable file.

    Returns:
        One entry per affected file: the path and how often it matched.

    Raises:
        ToolError: A file could not be written.
    """
    hits: list[tuple[Path, int]] = []
    for target in targets:
        text = _readable_text(target)
        if text is None:
            continue
        count = text.count(old)
        if not count:
            continue
        hits.append((target, count))
        if apply:
            try:
                target.write_text(text.replace(old, new), encoding="utf-8")
            except OSError as err:
                raise ToolError(f"could not write {target}: {err}") from err
        if len(hits) >= limit:
            break
    return hits


def _readable_text(target: Path) -> str | None:
    """Return a file's text, or None when it is not a readable text file."""
    if not target.is_file() or target.is_symlink():
        return None
    try:
        return target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
