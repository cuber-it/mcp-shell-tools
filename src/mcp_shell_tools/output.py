"""Text in and out: reading files as text, and keeping output within limits."""

from __future__ import annotations

from pathlib import Path

from mcp_shell_tools.errors import ToolError


def read_text(target: Path) -> str:
    """Return a file's text, with the refusals a caller can act on.

    Raises:
        ToolError: The file is missing, is a directory, is not UTF-8 text, or
            cannot be read.
    """
    try:
        return target.read_text(encoding="utf-8")
    except FileNotFoundError as err:
        raise ToolError(f"no such file: {target}") from err
    except IsADirectoryError as err:
        raise ToolError(f"this is a directory: {target}") from err
    except UnicodeDecodeError as err:
        raise ToolError(f"not text, or not UTF-8: {target}") from err
    except OSError as err:
        raise ToolError(f"could not read {target}: {err}") from err


def text_or_none(target: Path) -> str | None:
    """Return a file's text, or None when it cannot be read as UTF-8 text.

    Meant for tools that walk many files and pass over those without text.
    """
    try:
        return target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def cut(text: str, limit: int) -> str:
    """Shorten text that is too long, saying how much was dropped.

    Returns:
        The text, cut to ``limit`` characters with a note if it was.
    """
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n[... {len(text) - limit} more characters]"


def render(rows: list[str], limit: int, empty: str) -> str:
    """Join result rows, cutting at the limit and saying how many were left.

    Returns:
        The rows, or ``empty`` when there are none.
    """
    if not rows:
        return empty
    if len(rows) <= limit:
        return "\n".join(rows)
    dropped = len(rows) - limit
    return "\n".join(rows[:limit] + [f"[... {dropped} more]"])


def span(seconds: int) -> str:
    """Render a number of seconds as days, hours and minutes.

    Returns:
        For instance ``2d 3h 5m``, ``3h 5m`` or ``5m``; below a minute ``0m``.
    """
    minutes = max(seconds, 0) // 60
    days, minutes = divmod(minutes, 1440)
    hours, minutes = divmod(minutes, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def size(value: float) -> str:
    """Render a byte count in the largest unit that keeps it readable.

    Returns:
        The count with a unit suffix, for instance ``1.9M``.
    """
    for unit in ("B", "K", "M", "G"):
        if value < 1024:
            return f"{value:.0f}{unit}" if unit == "B" else f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}T"
