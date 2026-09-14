"""Grants: raising or lowering the boundary from outside, for a limited time.

A grant is a file in the server's state directory, written by the
``mcp-shell-grant`` program on the host and never by the tools. The server
reads it at every check, so a grant takes effect at the next tool call and
lapses when its time is up, without a restart.

A grant changes the configured boundary in up to three ways:

- ``mode`` replaces the mode.
- ``roots`` are added to the configured roots. Without configured roots there
  is no limit, and a grant does not introduce one.
- ``execute`` switches shell commands on or off.

Every grant has an end; lasting changes belong in the server's configuration.
A grant file that cannot be used stops every check instead of being passed
over, because passing over it could lift a restriction it imposes.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import re
import sys
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from mcp_shell_tools.boundary import MODES, Boundary
from mcp_shell_tools.errors import GrantError
from mcp_shell_tools.output import span

PROGRAM = "mcp-shell-grant"
GRANT_FILE = "grant.json"
DEFAULT_STATE_DIR = "~/.mcp-shell-tools"
SUGGESTED_DURATION = "1h"
DURATION = re.compile(r"(\d+)([smhd])")
SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
REFUSED = 2


@dataclass(frozen=True)
class Grant:
    """What a grant changes, and until when.

    Attributes:
        until: Unix time the grant lapses at.
        mode: Mode used instead of the configured one, or None to keep it.
        roots: Roots added to the configured ones.
        execute: Whether shell commands run, or None to keep the setting.
    """

    until: float
    mode: str | None = None
    roots: tuple[Path, ...] = ()
    execute: bool | None = None

    @classmethod
    def from_file(cls, text: str, where: Path) -> Grant:
        """Read a grant from the text of its file.

        Raises:
            GrantError: The text is not a usable grant.
        """
        try:
            data = json.loads(text)
            grant = cls(
                until=float(data["until"]),
                mode=data.get("mode"),
                roots=tuple(Path(root) for root in data.get("roots", [])),
                execute=data.get("execute"),
            )
        except (ValueError, TypeError, KeyError, AttributeError) as err:
            raise GrantError(_unusable(where, f"not a grant: {err!r}")) from err
        usable = (
            (grant.mode is None or grant.mode in MODES)
            and isinstance(grant.execute, bool | None)
            and all(root.is_absolute() for root in grant.roots)
        )
        if not usable:
            raise GrantError(_unusable(where, "unknown mode, execute or relative root"))
        return grant

    def to_file(self) -> str:
        """Return the text the grant is stored as."""
        return json.dumps(
            {
                "until": self.until,
                "mode": self.mode,
                "roots": [str(root) for root in self.roots],
                "execute": self.execute,
            },
            indent=2,
        )

    def applied(self, base: Boundary) -> Boundary:
        """Return the boundary this grant makes of the configured one."""
        added = tuple(root for root in self.roots if root not in base.roots)
        return Boundary(
            roots=base.roots + added if base.roots else (),
            mode=self.mode or base.mode,
            execute=base.execute if self.execute is None else self.execute,
        )

    def describe(self, now: float) -> str:
        """Say in one line what the grant changes and how long it holds."""
        changes = []
        if self.mode:
            changes.append(f"mode {self.mode}")
        if self.roots:
            changes.append("roots " + ", ".join(str(root) for root in self.roots))
        if self.execute is not None:
            changes.append(f"commands {'on' if self.execute else 'off'}")
        left = int(self.until - now)
        holds = f"lapses in {span(left)}" if left > 0 else "has lapsed"
        return f"grant: {'; '.join(changes)}; {holds}"


def grant_file(state_dir: Path) -> Path:
    """Return where the grant of a state directory is kept."""
    return state_dir / GRANT_FILE


def read_grant(state_dir: Path) -> Grant | None:
    """Return the grant in a state directory, lapsed or not, or None.

    Raises:
        GrantError: A grant file is there but cannot be used.
    """
    where = grant_file(state_dir)
    try:
        stamp = where.stat()
    except FileNotFoundError:
        return None
    except OSError as err:
        raise GrantError(_unusable(where, str(err))) from err
    return _parsed(where, stamp.st_mtime_ns, stamp.st_size)


@lru_cache(maxsize=16)
def _parsed(where: Path, mtime_ns: int, size: int) -> Grant:
    """Read and parse a grant file once per version of it.

    Modification time and size are part of the cache key, so a rewritten file
    is read again.

    Raises:
        GrantError: The file cannot be read or is not a usable grant.
    """
    del mtime_ns, size
    try:
        text = where.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        raise GrantError(_unusable(where, str(err))) from err
    return Grant.from_file(text, where)


def boundary_in_force(base: Boundary, state_dir: Path | None) -> Boundary:
    """Return the configured boundary as a grant that has not lapsed changes it.

    Raises:
        GrantError: A grant file is there but cannot be used.
    """
    grant = read_grant(state_dir) if state_dir is not None else None
    if grant is None or grant.until <= time.time():
        return base
    return grant.applied(base)


def write_grant(state_dir: Path, grant: Grant) -> Path:
    """Write a grant so that a reader finds the old one or the new one, never half.

    Returns:
        Where the grant was written.

    Raises:
        GrantError: It could not be written; a previous grant stays in force.
    """
    where = grant_file(state_dir)
    partial = where.with_name(f"{GRANT_FILE}.partial")
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        partial.write_text(grant.to_file(), encoding="utf-8")
        partial.chmod(0o600)
        partial.replace(where)
    except OSError as err:
        with contextlib.suppress(OSError):
            partial.unlink(missing_ok=True)
        raise GrantError(
            f"could not write {where}: {err}; a previous grant stays in force"
        ) from err
    return where


def remove_grant(state_dir: Path) -> bool:
    """Remove the grant of a state directory.

    Returns:
        Whether there was one.

    Raises:
        GrantError: It is there but could not be removed.
    """
    try:
        grant_file(state_dir).unlink()
    except FileNotFoundError:
        return False
    except OSError as err:
        raise GrantError(f"could not remove the grant: {err}") from err
    return True


def parse_duration(text: str) -> int:
    """Return the seconds a duration such as ``30m``, ``2h`` or ``1d`` stands for.

    Raises:
        GrantError: The text is no duration, or a duration of zero.
    """
    match = DURATION.fullmatch(text.strip())
    if match is None or int(match[1]) == 0:
        raise GrantError(f"not a duration: {text!r}; use for instance 30m, 2h or 1d")
    return int(match[1]) * SECONDS[match[2]]


def hint(state_dir: Path | None, change: str) -> str:
    """Return how a refusal can be lifted, for the message that reports it."""
    if state_dir is None:
        return "grants need a server started with --state-dir"
    return (
        f"a person on the host can allow it with: {PROGRAM} --state-dir "
        f"{state_dir} set {change} --for {SUGGESTED_DURATION}"
    )


def main(argv: list[str] | None = None) -> int:
    """Set, show or remove the grant of a server.

    Returns:
        0 when done, 2 when the arguments or the grant file were refused.
    """
    args = _parser().parse_args(argv)
    state_dir = Path(args.state_dir).expanduser().resolve()
    try:
        print(args.command(state_dir, args))
    except GrantError as err:
        print(f"{PROGRAM}: {err}", file=sys.stderr)
        return REFUSED
    return 0


def _parser() -> argparse.ArgumentParser:
    """Return the parser for the program's arguments."""
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description="Raise or lower the boundary of an mcp-shell-tools server "
        "for a limited time.",
    )
    parser.add_argument(
        "--state-dir",
        default=DEFAULT_STATE_DIR,
        help="state directory of the server (default: %(default)s)",
    )
    commands = parser.add_subparsers(required=True)
    setting = commands.add_parser(
        "set", help="write a grant, replacing any previous one"
    )
    setting.add_argument(
        "--for", dest="duration", required=True, help="how long it holds: 30m, 2h, 1d"
    )
    setting.add_argument(
        "--mode", choices=MODES, help="mode to use instead of the configured one"
    )
    setting.add_argument(
        "--root", action="append", default=[], metavar="PATH", help="add a root"
    )
    setting.add_argument(
        "--exec",
        dest="execute",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="switch shell commands on or off",
    )
    setting.set_defaults(command=_set)
    commands.add_parser("show", help="show the grant").set_defaults(command=_show)
    commands.add_parser("reset", help="remove the grant").set_defaults(command=_reset)
    return parser


def _set(state_dir: Path, args: argparse.Namespace) -> str:
    """Write the grant the arguments describe.

    Raises:
        GrantError: It changes nothing, the duration is unusable, or it cannot
            be written.
    """
    if args.mode is None and not args.root and args.execute is None:
        raise GrantError(
            "a grant has to change something: give --mode, --root, --exec or --no-exec"
        )
    now = time.time()
    grant = Grant(
        until=now + parse_duration(args.duration),
        mode=args.mode,
        roots=tuple(Path(root).expanduser().resolve() for root in args.root),
        execute=args.execute,
    )
    where = write_grant(state_dir, grant)
    return f"{grant.describe(now)}; written to {where}"


def _show(state_dir: Path, args: argparse.Namespace) -> str:
    """Describe the grant of a state directory.

    Raises:
        GrantError: The grant file cannot be used.
    """
    del args
    grant = read_grant(state_dir)
    if grant is None:
        return f"no grant in {state_dir}"
    return grant.describe(time.time())


def _reset(state_dir: Path, args: argparse.Namespace) -> str:
    """Remove the grant of a state directory.

    Raises:
        GrantError: The grant file could not be removed.
    """
    del args
    if remove_grant(state_dir):
        return f"removed the grant in {state_dir}"
    return f"no grant in {state_dir}"


def _unusable(where: Path, reason: str) -> str:
    """Return the message for a grant file that stops every check."""
    return (
        f"the grant file {where} cannot be used ({reason}); every check is "
        f"refused until it is fixed or removed with {PROGRAM} --state-dir "
        f"{where.parent} reset"
    )
