"""How far the tools may reach: the roots, the mode, and the kind of access.

This is the one place that decides. A tool names what it is about to do with a
path, and the boundary answers. It knows nothing about the tools, so a policy
of another kind can take its place later without touching them.

How far the roots reach depends on the mode:

- ``open`` ignores them.
- ``guarded`` lets reading and writing go anywhere and confines destroying
  access (deleting, moving, replacing across files) to them.
- ``strict`` confines every access to them and runs no commands.

Empty roots mean no limit in every mode.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from mcp_shell_tools.errors import NotPermittedError, ToolError

MODES = ("open", "guarded", "strict")
DEFAULT_MODE = "guarded"


class Access(StrEnum):
    """What a tool is about to do with a path."""

    READ = "read"
    WRITE = "write"
    DESTROY = "destroy"


@dataclass(frozen=True)
class Boundary:
    """The roots the tools are confined to, and how far that reaches.

    Attributes:
        roots: Directories the tools are confined to, empty for no limit.
        mode: How far the roots reach, one of :data:`MODES`.
    """

    roots: tuple[Path, ...] = ()
    mode: str = DEFAULT_MODE

    def __post_init__(self) -> None:
        """Refuse a mode that does not exist.

        Raises:
            ToolError: The mode is not one of :data:`MODES`.
        """
        if self.mode not in MODES:
            raise ToolError(f"no such mode {self.mode!r}, choose from {MODES}")

    def admits(self, resolved: Path, access: Access = Access.READ) -> bool:
        """Say whether this access may reach a resolved path."""
        if not self.roots or self.mode == "open":
            return True
        if self.mode == "guarded" and access is not Access.DESTROY:
            return True
        return any(resolved == root or root in resolved.parents for root in self.roots)

    def permit_execute(self) -> None:
        """Check that commands may run.

        Raises:
            NotPermittedError: The mode is ``strict``.
        """
        if self.mode == "strict":
            raise NotPermittedError("commands are not run in strict mode")
