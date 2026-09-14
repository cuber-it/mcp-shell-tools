"""How far the roots reach in each mode."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_shell_tools import Boundary, ToolError
from mcp_shell_tools.boundary import Access

ROOT = Path("/srv/inside")
OUTSIDE = Path("/etc/hostname")


def test_guarded_is_the_default_mode() -> None:
    assert Boundary().mode == "guarded"


def test_an_unknown_mode_is_refused() -> None:
    with pytest.raises(ToolError, match="no such mode"):
        Boundary(mode="loose")


@pytest.mark.parametrize(
    ("mode", "access", "admitted"),
    [
        ("open", Access.READ, True),
        ("open", Access.WRITE, True),
        ("open", Access.DESTROY, True),
        ("guarded", Access.READ, True),
        ("guarded", Access.WRITE, False),
        ("guarded", Access.DESTROY, False),
        ("strict", Access.READ, False),
        ("strict", Access.WRITE, False),
        ("strict", Access.DESTROY, False),
    ],
)
def test_the_mode_decides_how_far_the_roots_reach(
    mode: str, access: Access, admitted: bool
) -> None:
    assert Boundary((ROOT,), mode).admits(OUTSIDE, access) is admitted


@pytest.mark.parametrize("mode", ["open", "guarded", "strict"])
def test_every_mode_admits_everything_inside_the_roots(mode: str) -> None:
    boundary = Boundary((ROOT,), mode)

    assert all(boundary.admits(ROOT / "a.txt", access) for access in Access)
    assert all(boundary.admits(ROOT, access) for access in Access)


def test_a_sibling_with_a_shared_prefix_is_outside() -> None:
    boundary = Boundary((ROOT,), "strict")

    assert not boundary.admits(Path("/srv/inside-not"), Access.READ)


def test_without_roots_even_strict_admits_everything() -> None:
    assert Boundary(mode="strict").admits(OUTSIDE, Access.DESTROY)
