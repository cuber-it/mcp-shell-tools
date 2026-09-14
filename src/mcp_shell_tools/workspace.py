"""What the tools share: the working directory and the limits they respect."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SKIPPED = frozenset({".git", "__pycache__", ".venv", "node_modules", ".mypy_cache"})

DEFAULT_TIMEOUT = 120.0
DEFAULT_MAX_OUTPUT = 200_000
DEFAULT_MAX_RESULTS = 200


class ToolError(Exception):
    """A tool refused to do what it was asked."""


class OutsideBoundaryError(ToolError):
    """The path lies outside what this installation may touch."""


@dataclass
class Workspace:
    """The state the tools work against.

    Attributes:
        working_dir: Directory relative paths are resolved against.
        allowed_roots: Directories the tools may touch, empty for no limit.
        timeout: Seconds a command may run.
        max_output: Bytes of output kept before it is cut.
        max_results: Rows a listing or search returns at most.
        notes: Notes kept by the note tools, in order.
        state_dir: Where sessions are written.
    """

    working_dir: Path
    allowed_roots: tuple[Path, ...] = ()
    timeout: float = DEFAULT_TIMEOUT
    max_output: int = DEFAULT_MAX_OUTPUT
    max_results: int = DEFAULT_MAX_RESULTS
    notes: list[str] = field(default_factory=list)
    state_dir: Path | None = None

    def resolve(self, path: str) -> Path:
        """Turn a path from a caller into an absolute one and check it.

        Raises:
            OutsideBoundaryError: The path lies outside ``allowed_roots``.
        """
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = self.working_dir / candidate
        resolved = Path(candidate).resolve()
        if not self.allowed_roots:
            return resolved
        for root in self.allowed_roots:
            if resolved == root or root in resolved.parents:
                return resolved
        raise OutsideBoundaryError(f"outside the allowed roots: {resolved}")

    def cut(self, text: str) -> str:
        """Shorten output that is too long, saying how much was dropped.

        Returns:
            The output, cut to ``max_output`` with a note if it was.
        """
        if len(text) <= self.max_output:
            return text
        dropped = len(text) - self.max_output
        return f"{text[: self.max_output]}\n[... {dropped} more characters]"


def workspace_from(config: dict[str, Any]) -> Workspace:
    """Build the workspace from a configuration mapping.

    Raises:
        ToolError: ``working_dir`` names something that is not a directory.
    """
    working = Path(str(config.get("working_dir", Path.cwd()))).expanduser().resolve()
    if not working.is_dir():
        raise ToolError(f"working_dir is not a directory: {working}")
    roots = tuple(
        Path(str(entry)).expanduser().resolve()
        for entry in config.get("allowed_roots", ())
    )
    state = config.get("state_dir")
    return Workspace(
        working_dir=working,
        allowed_roots=roots,
        timeout=float(config.get("timeout", DEFAULT_TIMEOUT)),
        max_output=int(config.get("max_output", DEFAULT_MAX_OUTPUT)),
        max_results=int(config.get("max_results", DEFAULT_MAX_RESULTS)),
        state_dir=Path(str(state)).expanduser().resolve() if state else None,
    )


def read_text(space: Workspace, path: str) -> str:
    """Return a file's text, with the refusals a caller can act on.

    Raises:
        ToolError: The file is missing, is a directory, or is not UTF-8 text.
    """
    target = space.resolve(path)
    try:
        return target.read_text(encoding="utf-8")
    except FileNotFoundError as err:
        raise ToolError(f"no such file: {target}") from err
    except IsADirectoryError as err:
        raise ToolError(f"this is a directory: {target}") from err
    except UnicodeDecodeError as err:
        raise ToolError(f"not text, or not UTF-8: {target}") from err


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
