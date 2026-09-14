"""What the tools share: the working directory, the boundary, the limits.

Every path a tool touches is resolved here and checked against the
:class:`~mcp_shell_tools.boundary.Boundary`, including every hit a search
pattern turns up. No tool checks a path on its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mcp_shell_tools.boundary import DEFAULT_MODE, Access, Boundary
from mcp_shell_tools.errors import OutsideBoundaryError, ToolError

SKIPPED = frozenset({".git", "__pycache__", ".venv", "node_modules", ".mypy_cache"})

DEFAULT_TIMEOUT = 120.0
DEFAULT_MAX_OUTPUT = 200_000
DEFAULT_MAX_RESULTS = 200
TRASH = "trash"


@dataclass
class Workspace:
    """The state the tools work against.

    Attributes:
        working_dir: Directory relative paths are resolved against.
        boundary: How far the tools may reach.
        timeout: Seconds a command may run.
        max_output: Characters of output kept before it is cut.
        max_results: Rows a listing or search returns at most.
        notes: Notes kept by the note tools, in order.
        state_dir: Where sessions and the trash are written.
    """

    working_dir: Path
    boundary: Boundary = field(default_factory=Boundary)
    timeout: float = DEFAULT_TIMEOUT
    max_output: int = DEFAULT_MAX_OUTPUT
    max_results: int = DEFAULT_MAX_RESULTS
    notes: list[str] = field(default_factory=list)
    state_dir: Path | None = None

    def resolve(self, path: str, access: Access = Access.READ) -> Path:
        """Turn a path from a caller into an absolute one and check it.

        Raises:
            OutsideBoundaryError: The boundary does not let this access reach
                the path.
        """
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = self.working_dir / candidate
        resolved = candidate.resolve()
        if not self.boundary.admits(resolved, access):
            raise OutsideBoundaryError(
                f"outside the allowed roots for {access}: {resolved}"
            )
        return resolved

    def existing(self, path: str, access: Access = Access.READ) -> Path:
        """Resolve a path that has to name something that exists.

        Raises:
            OutsideBoundaryError: The boundary does not let this access reach it.
            ToolError: Nothing exists there.
        """
        target = self.resolve(path, access)
        if not target.exists():
            raise ToolError(f"no such path: {target}")
        return target

    def directory(self, path: str) -> Path:
        """Resolve a path that has to name an existing directory, for reading.

        Raises:
            OutsideBoundaryError: The boundary does not let reading reach it.
            ToolError: There is no directory there.
        """
        target = self.resolve(path)
        if not target.is_dir():
            raise ToolError(f"no such directory: {target}")
        return target

    def glob(
        self, root: Path, pattern: str, access: Access = Access.READ
    ) -> list[Path]:
        """Return what a pattern matches below root, as far as it may be seen.

        Returns:
            The hits in sorted order, without those :meth:`within` rejects.

        Raises:
            ToolError: The pattern is not usable, for instance empty or absolute.
        """
        try:
            hits = sorted(root.glob(pattern))
        except (ValueError, NotImplementedError) as err:
            raise ToolError(f"not a usable pattern {pattern!r}: {err}") from err
        return [hit for hit in hits if self.within(root, hit, access)]

    def within(self, root: Path, hit: Path, access: Access = Access.READ) -> bool:
        """Say whether something found below root may be shown or touched.

        A hit is rejected when it lies in a skipped directory below root, or
        when the boundary does not let this access reach it. A ``..`` in a
        pattern or a symlink on the way can lead anywhere, so the hit is
        resolved and checked like a path a caller named. Only the part below
        root counts for skipping: a root that itself lies inside ``.venv`` is
        still searched.
        """
        if any(part in SKIPPED for part in hit.relative_to(root).parts):
            return False
        return self.boundary.admits(hit.resolve(), access)

    def state(self) -> Path:
        """Return the state directory.

        Raises:
            ToolError: No state directory is configured.
        """
        if self.state_dir is None:
            raise ToolError("no state_dir configured")
        return self.state_dir

    def trash(self) -> Path:
        """Return where deleted entries are moved to.

        Raises:
            ToolError: No state directory is configured.
        """
        return self.state() / TRASH


def workspace_from(config: dict[str, Any]) -> Workspace:
    """Build the workspace from a configuration mapping.

    The boundary is read from ``allowed_roots`` and ``mode``.

    Raises:
        ToolError: ``working_dir`` names something that is not a directory, or
            ``mode`` is unknown.
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
        boundary=Boundary(roots, str(config.get("mode", DEFAULT_MODE))),
        timeout=float(config.get("timeout", DEFAULT_TIMEOUT)),
        max_output=int(config.get("max_output", DEFAULT_MAX_OUTPUT)),
        max_results=int(config.get("max_results", DEFAULT_MAX_RESULTS)),
        state_dir=Path(str(state)).expanduser().resolve() if state else None,
    )
