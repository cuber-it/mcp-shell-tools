"""What the tools share: the working directory, the boundary, the limits.

Every path a tool touches is resolved here and checked against the boundary in
force, including every hit a search pattern turns up. No tool checks a path on
its own. The boundary in force is the configured one as a grant changes it
(:mod:`mcp_shell_tools.grant`); the grant file itself is out of every tool's
reach for changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mcp_shell_tools.boundary import DEFAULT_MODE, Access, Boundary
from mcp_shell_tools.errors import NotPermittedError, OutsideBoundaryError, ToolError
from mcp_shell_tools.grant import GRANT_SCRIPT, boundary_in_force, grant_file, hint

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
        boundary: How far the tools may reach, before any grant.
        timeout: Seconds a command may run.
        max_output: Characters of output kept before it is cut.
        max_results: Rows a listing or search returns at most.
        notes: Notes kept by the note tools, in order.
        state_dir: Where sessions, the trash and the grant are kept.
    """

    working_dir: Path
    boundary: Boundary = field(default_factory=Boundary)
    timeout: float = DEFAULT_TIMEOUT
    max_output: int = DEFAULT_MAX_OUTPUT
    max_results: int = DEFAULT_MAX_RESULTS
    notes: list[str] = field(default_factory=list)
    state_dir: Path | None = None

    def current(self) -> Boundary:
        """Return the boundary in force: the configured one as a grant changes it.

        Raises:
            GrantError: A grant file is there but cannot be used.
        """
        return boundary_in_force(self.boundary, self.state_dir)

    def resolve(self, path: str, access: Access = Access.READ) -> Path:
        """Turn a path from a caller into an absolute, resolved one and check it.

        Raises:
            NotPermittedError: The access would change the grant file.
            OutsideBoundaryError: The boundary in force does not let this access
                reach the path. The message names the grant that would.
            GrantError: A grant file is there but cannot be used.
        """
        resolved = self._absolute(path).resolve()
        self._check(resolved, access)
        return resolved

    def locate(self, path: str, access: Access = Access.READ) -> Path:
        """Like :meth:`resolve`, but a symlink at the end stays the link itself.

        For tools that act on a directory entry rather than on what it points
        to. A path ending in ``..`` is resolved in full.

        Raises:
            NotPermittedError: The access would change the grant file.
            OutsideBoundaryError: The boundary in force does not let this access
                reach the entry.
            GrantError: A grant file is there but cannot be used.
        """
        absolute = self._absolute(path)
        if absolute.name in ("", ".."):
            return self.resolve(path, access)
        located = absolute.parent.resolve() / absolute.name
        self._check(located, access)
        return located

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

        A hit is rejected when it lies in a skipped directory below root, when
        a changing access would reach the grant file, or when the boundary in
        force does not let this access reach it. A ``..`` in a pattern or a
        symlink on the way can lead anywhere, so the hit is resolved and
        checked like a path a caller named. Only the part below root counts
        for skipping: a root that itself lies inside ``.venv`` is still
        searched.

        Raises:
            GrantError: A grant file is there but cannot be used.
        """
        if any(part in SKIPPED for part in hit.relative_to(root).parts):
            return False
        resolved = hit.resolve()
        if self._reaches_grant(resolved, access):
            return False
        return self.current().admits(resolved, access)

    def permit_execute(self) -> None:
        """Check that shell commands may run.

        Raises:
            NotPermittedError: Commands are switched off. The message names the
                grant that would switch them on.
            GrantError: A grant file is there but cannot be used.
        """
        if not self.current().execute:
            raise NotPermittedError(
                "shell commands are switched off; " + hint(self.state_dir, "--exec")
            )

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

    def _absolute(self, path: str) -> Path:
        """Return a path from a caller as an absolute one, not yet resolved."""
        candidate = Path(path).expanduser()
        return candidate if candidate.is_absolute() else self.working_dir / candidate

    def _check(self, target: Path, access: Access) -> None:
        """Refuse an access to a path that the grant file or the boundary forbids.

        Raises:
            NotPermittedError: The access would change the grant file.
            OutsideBoundaryError: The boundary in force does not let this access
                reach the path.
            GrantError: A grant file is there but cannot be used.
        """
        if self._reaches_grant(target, access):
            raise NotPermittedError(
                f"{target} holds the grant file, which only {GRANT_SCRIPT} on the "
                "host changes"
            )
        if not self.current().admits(target, access):
            nearest = target if target.is_dir() else target.parent
            raise OutsideBoundaryError(
                f"outside the allowed roots for {access}: {target}; "
                + hint(self.state_dir, f"--root {nearest}")
            )

    def _reaches_grant(self, resolved: Path, access: Access) -> bool:
        """Say whether a changing access would reach the grant file.

        Writing reaches it through the file itself or through its directory,
        where a copy would land on it. Destroying reaches it through every
        directory above it, because deleting or moving one takes the file
        along.
        """
        if access is Access.READ or self.state_dir is None:
            return False
        held = grant_file(self.state_dir)
        if access is Access.WRITE:
            return resolved in (held, held.parent)
        return resolved == held or resolved in held.parents


def workspace_from(config: dict[str, Any]) -> Workspace:
    """Build the workspace from a configuration mapping.

    The boundary is read from ``allowed_roots``, ``mode`` and ``execute``.

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
        boundary=Boundary(
            roots,
            str(config.get("mode", DEFAULT_MODE)),
            bool(config.get("execute", True)),
        ),
        timeout=float(config.get("timeout", DEFAULT_TIMEOUT)),
        max_output=int(config.get("max_output", DEFAULT_MAX_OUTPUT)),
        max_results=int(config.get("max_results", DEFAULT_MAX_RESULTS)),
        state_dir=Path(str(state)).expanduser().resolve() if state else None,
    )
