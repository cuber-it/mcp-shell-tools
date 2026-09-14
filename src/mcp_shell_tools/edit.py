"""Changing text in a file, and looking at a change before making it."""

from __future__ import annotations

import difflib
from pathlib import Path

from mcp_shell_tools.boundary import Access
from mcp_shell_tools.errors import ToolError
from mcp_shell_tools.output import cut, read_text, text_or_none
from mcp_shell_tools.workspace import Workspace


def str_replace(space: Workspace, path: str, old: str, new: str) -> str:
    """Replace a passage that appears exactly once in a file.

    No match and several matches are both refused.

    Raises:
        ToolError: The passage is missing, ambiguous, or the file is
            unreadable.
    """
    target = space.resolve(path, Access.WRITE)
    text = read_text(target)
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
    before = read_text(target) if target.exists() else ""
    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        content.splitlines(keepends=True),
        fromfile=f"{target} (current)",
        tofile=f"{target} (proposed)",
    )
    rendered = "".join(diff)
    return cut(rendered, space.max_output) if rendered else f"{target} would not change"


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

    Nothing is written unless apply is true. The run stops once the result
    limit of affected files is reached, and says so.

    Returns:
        One line per affected file with the number of replacements, and
        closing lines saying whether anything was written and whether the
        limit stopped the run.

    Raises:
        ToolError: The path does not exist, the pattern is not usable, or a
            file cannot be written.
    """
    # The root is written into, not destroyed; each file found is checked for
    # the replacement itself.
    root = space.existing(path, Access.WRITE if apply else Access.READ)
    access = Access.DESTROY if apply else Access.READ
    targets = [root] if root.is_file() else space.glob(root, f"**/{glob}", access)
    hits, stopped = _replace_in(targets, old, new, apply, space.max_results)

    if not hits:
        return f"'{old}' appears in no file under {root}"

    lines = [f"{count:>5}x  {target}" for target, count in hits]
    total = sum(count for _, count in hits)
    verb = "replaced" if apply else "would replace"
    lines.append(f"{verb} {total} occurrences in {len(hits)} files")
    if stopped:
        lines.append(
            f"stopped at the limit of {len(hits)} files; "
            "the files after it were not looked at"
        )
    if not apply:
        lines.append("nothing was written; call again with apply=true")
    return cut("\n".join(lines), space.max_output)


def _replace_in(
    targets: list[Path], old: str, new: str, apply: bool, limit: int
) -> tuple[list[tuple[Path, int]], bool]:
    """Count and optionally perform the replacement in each text file.

    Symlinks are passed over, so a replacement never writes through a link.

    Returns:
        The affected files with their number of matches, and whether the
        limit stopped the run before every file was looked at.

    Raises:
        ToolError: A file could not be written. The message says how many
            files before it were already changed.
    """
    hits: list[tuple[Path, int]] = []
    for target in targets:
        if len(hits) >= limit:
            return hits, True
        if target.is_symlink() or not target.is_file():
            continue
        text = text_or_none(target)
        if text is None or old not in text:
            continue
        if apply:
            try:
                target.write_text(text.replace(old, new), encoding="utf-8")
            except OSError as err:
                raise ToolError(
                    f"could not write {target}: {err}; "
                    f"{len(hits)} files before it were already changed"
                ) from err
        hits.append((target, text.count(old)))
    return hits, False
