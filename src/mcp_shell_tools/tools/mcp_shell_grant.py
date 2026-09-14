"""Raise or lower the boundary of a running mcp-shell-tools server.

A person on the host runs this, with the interpreter the server runs with. In a
checkout ``scripts/grant.sh`` does that:

    scripts/grant.sh set --root /opt/data --for 2h
    scripts/grant.sh set --exec --for 30m
    scripts/grant.sh show
    scripts/grant.sh reset

After ``pip install`` the same program is
``python -m mcp_shell_tools.tools.mcp_shell_grant``.

What a grant changes and how the server reads it is described in
:mod:`mcp_shell_tools.grant`.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from mcp_shell_tools.boundary import MODES
from mcp_shell_tools.errors import GrantError
from mcp_shell_tools.grant import (
    DEFAULT_STATE_DIR,
    Grant,
    parse_duration,
    read_grant,
    remove_grant,
    write_grant,
)

PROG = "mcp_shell_grant"
REFUSED = 2


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
        print(f"{PROG}: {err}", file=sys.stderr)
        return REFUSED
    return 0


def _parser() -> argparse.ArgumentParser:
    """Return the parser for the program's arguments."""
    parser = argparse.ArgumentParser(
        prog=PROG,
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


if __name__ == "__main__":
    raise SystemExit(main())
