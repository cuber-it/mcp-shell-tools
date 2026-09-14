"""Reading, writing and moving files, and looking at directories."""

from __future__ import annotations

import os
import shutil
import stat
from datetime import datetime
from pathlib import Path

from mcp_shell_tools.boundary import Access
from mcp_shell_tools.errors import ToolError
from mcp_shell_tools.output import cut, read_text, render
from mcp_shell_tools.workspace import Workspace

TREE_INDENT = "    "


def file_read(space: Workspace, path: str, start: int = 0, end: int = 0) -> str:
    """Return a file's text, optionally a line range.

    Returns:
        The text, cut if it exceeds the output limit.

    Raises:
        ToolError: The file does not exist or cannot be read as text.
    """
    text = read_text(space.resolve(path))
    if not start and not end:
        return cut(text, space.max_output)
    lines = text.splitlines()
    first = max(start - 1, 0)
    last = end if end else len(lines)
    return cut("\n".join(lines[first:last]), space.max_output)


def file_write(space: Workspace, path: str, content: str) -> str:
    """Write text to a file, replacing what was there.

    Missing parent directories are created.

    Raises:
        ToolError: The file cannot be written.
    """
    target = space.resolve(path, Access.WRITE)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except OSError as err:
        raise ToolError(f"could not write {target}: {err}") from err
    return f"wrote {len(content)} characters to {target}"


def file_append(space: Workspace, path: str, content: str) -> str:
    """Add text to the end of a file, creating it if needed.

    Raises:
        ToolError: The file cannot be written.
    """
    target = space.resolve(path, Access.WRITE)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(content)
    except OSError as err:
        raise ToolError(f"could not append to {target}: {err}") from err
    return f"appended {len(content)} characters to {target}"


def file_list(space: Workspace, path: str = ".") -> str:
    """List a directory, directories first, one entry per line.

    Returns:
        The entries, each with its size, cut at the result limit.

    Raises:
        ToolError: The directory does not exist.
    """
    target = space.directory(path)
    rows = [_describe(entry) for entry in _entries(target)]
    return render(rows, space.max_results, f"{target} is empty")


def file_delete(space: Workspace, path: str) -> str:
    """Move a file, or a directory with everything in it, to the trash.

    Nothing is removed for good. The entry lands in the trash under the state
    directory, named with the time of deletion, and can be moved back. A
    symlink is moved itself, not what it points to.

    Raises:
        ToolError: Nothing is there, no state directory is configured, or the
            move fails. A move across filesystems that fails halfway can leave
            a partial copy in the trash; the message names where.
    """
    target = space.locate(path, Access.DESTROY)
    if not target.exists() and not target.is_symlink():
        raise ToolError(f"nothing to delete at: {target}")
    kept = space.trash() / f"{datetime.now():%Y%m%d-%H%M%S-%f}-{target.name}"
    try:
        kept.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(target, kept)
    except OSError as err:
        raise ToolError(
            f"could not move {target} to the trash: {err}; "
            f"look at {kept} for a partial copy"
        ) from err
    return f"moved {target} to the trash: {kept}"


def file_move(space: Workspace, source: str, destination: str) -> str:
    """Move or rename a file or directory; a symlink is moved itself.

    Raises:
        ToolError: The source is missing or the move fails.
    """
    origin = space.locate(source, Access.DESTROY)
    return _transfer(origin, space.resolve(destination, Access.DESTROY), move=True)


def file_copy(space: Workspace, source: str, destination: str) -> str:
    """Copy a file, or a directory with everything in it.

    Symlinks inside a copied directory are copied as links.

    Raises:
        ToolError: The source is missing or the copy fails.
    """
    origin = space.resolve(source)
    return _transfer(origin, space.resolve(destination, Access.WRITE), move=False)


def tree(space: Workspace, path: str = ".", depth: int = 3) -> str:
    """Show a directory and what is below it, down to a depth.

    Skipped directories and entries leading outside the allowed roots are
    left out.

    Returns:
        The tree, one entry per line, cut at the result limit.

    Raises:
        ToolError: The directory does not exist.
    """
    root = space.directory(path)
    rows: list[str] = []
    _walk(space, root, depth, 1, rows)
    return render([str(root)] + rows, space.max_results, str(root))


def file_info(space: Workspace, path: str) -> str:
    """Report what is known about a file, directory or symlink.

    Returns:
        One labelled line per fact: kind, size, permissions, owner, times.

    Raises:
        ToolError: The entry does not exist.
    """
    target = space.locate(path)
    try:
        info = target.lstat()
    except OSError as err:
        raise ToolError(f"could not stat {target}: {err}") from err

    if target.is_symlink():
        kind = f"symlink -> {os.readlink(target)}"
    else:
        kind = "directory" if target.is_dir() else "file"

    try:
        owner = f"{target.owner()}:{target.group()}"
    except (KeyError, OSError):
        owner = f"{info.st_uid}:{info.st_gid}"

    stamps = {"modified": info.st_mtime, "accessed": info.st_atime}
    stamps["changed"] = info.st_ctime
    lines = [
        f"path:      {target}",
        f"kind:      {kind}",
        f"size:      {info.st_size} bytes",
        f"mode:      {stat.filemode(info.st_mode)} ({oct(info.st_mode & 0o777)})",
        f"owner:     {owner}",
        *(
            f"{label + ':':<11}{datetime.fromtimestamp(stamp):%Y-%m-%d %H:%M:%S}"
            for label, stamp in stamps.items()
        ),
    ]
    if kind == "directory":
        try:
            lines.append(f"entries:   {len(list(target.iterdir()))}")
        except OSError:
            pass
    return "\n".join(lines)


def head(space: Workspace, path: str, lines: int = 10) -> str:
    """Return the first lines of a file.

    Returns:
        The first lines, cut at the output limit.

    Raises:
        ToolError: The file does not exist or cannot be read as text.
    """
    rows = read_text(space.resolve(path)).splitlines()
    return cut("\n".join(rows[: max(lines, 1)]), space.max_output)


def tail(space: Workspace, path: str, lines: int = 10) -> str:
    """Return the last lines of a file.

    Returns:
        The last lines, cut at the output limit.

    Raises:
        ToolError: The file does not exist or cannot be read as text.
    """
    rows = read_text(space.resolve(path)).splitlines()
    return cut("\n".join(rows[-max(lines, 1) :]), space.max_output)


def _entries(directory: Path) -> list[Path]:
    """Return the entries of a directory, directories first, then by name."""
    return sorted(directory.iterdir(), key=lambda item: (item.is_file(), item.name))


def _describe(entry: Path) -> str:
    """Return one listing row for a directory entry."""
    if entry.is_dir():
        return f"{entry.name}/"
    try:
        return f"{entry.name}  {entry.stat().st_size} bytes"
    except OSError:
        return f"{entry.name}  (unreadable)"


def _walk(
    space: Workspace, directory: Path, depth: int, level: int, rows: list[str]
) -> None:
    """Collect tree rows for one directory level."""
    if level > depth:
        return
    try:
        entries = _entries(directory)
    except OSError:
        return
    for entry in entries:
        if not space.within(directory, entry):
            continue
        rows.append(f"{TREE_INDENT * level}{entry.name}{'/' if entry.is_dir() else ''}")
        if entry.is_dir():
            _walk(space, entry, depth, level + 1, rows)


def _transfer(origin: Path, target: Path, move: bool) -> str:
    """Move or copy, whichever was asked for.

    Raises:
        ToolError: The source is missing or the transfer fails.
    """
    if not origin.exists() and not origin.is_symlink():
        raise ToolError(f"nothing to transfer at: {origin}")
    verb, infinitive = ("moved", "move") if move else ("copied", "copy")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if move:
            shutil.move(str(origin), str(target))
        elif origin.is_dir():
            shutil.copytree(origin, target, symlinks=True)
        else:
            shutil.copy2(origin, target)
    except OSError as err:
        raise ToolError(f"could not {infinitive} {origin}: {err}") from err
    return f"{verb} {origin} to {target}"
