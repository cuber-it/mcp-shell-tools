"""How far the tools may reach: the roots, the mode, and whether commands run.

This is the one place that decides. A tool names what it is about to do with a
path, and the boundary answers. It knows nothing about the tools.

How far the roots reach depends on the mode:

- ``open`` ignores them.
- ``guarded`` lets reading go anywhere and confines writing and destroying
  access (deleting, moving, replacing across files) to them.
- ``strict`` confines every access to them.

``/tmp`` is always within reach, for every access and in every mode. Empty
roots mean no limit in every mode. Whether shell commands run is a separate
setting.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from mcp_shell_tools.errors import ToolError

MODES = ("open", "guarded", "strict")
DEFAULT_MODE = "guarded"
TMP = Path("/tmp")


class Access(StrEnum):
    """What a tool is about to do with a path."""

    READ = "read"
    WRITE = "write"
    DESTROY = "destroy"


@dataclass(frozen=True)
class Boundary:
    """The roots the tools are confined to, how far that reaches, and commands.

    Attributes:
        roots: Directories the tools are confined to, empty for no limit.
        mode: How far the roots reach, one of :data:`MODES`.
        execute: Whether shell commands may run.
    """

    roots: tuple[Path, ...] = ()
    mode: str = DEFAULT_MODE
    execute: bool = True

    def __post_init__(self) -> None:
        """Refuse a mode that does not exist.

        Raises:
            ToolError: The mode is not one of :data:`MODES`.
        """
        if self.mode not in MODES:
            raise ToolError(f"no such mode {self.mode!r}, choose from {MODES}")

    def admits(self, resolved: Path, access: Access = Access.READ) -> bool:
        """Say whether this access may reach a resolved path."""
        if not self.roots or self.mode == "open" or _within(resolved, (TMP,)):
            return True
        if self.mode == "guarded" and access is Access.READ:
            return True
        return _within(resolved, self.roots)


def _within(path: Path, directories: tuple[Path, ...]) -> bool:
    """Say whether a path is one of the directories or lies below one."""
    return any(
        path == directory or directory in path.parents for directory in directories
    )
