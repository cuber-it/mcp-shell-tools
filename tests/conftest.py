"""Fixtures shared by the test modules."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from loopback import Issuer, serve_issuer
from mcp_shell_tools import Boundary, Workspace


@pytest.fixture
def issuer() -> Iterator[Issuer]:
    """Return a stand-in authorization server that rejects every token."""
    with serve_issuer() as running:
        yield running


@pytest.fixture
def space(tmp_path: Path) -> Workspace:
    """Return a workspace rooted in a fresh temporary directory."""
    return Workspace(working_dir=tmp_path, state_dir=tmp_path / "state")


@pytest.fixture
def bounded(tmp_path: Path) -> Workspace:
    """Return a strict workspace confined to ``inside``, with ``outside.txt`` beside it.

    The file outside holds the word ``secret``. A tool that shows or changes
    it has crossed the boundary.
    """
    inside = tmp_path / "inside"
    inside.mkdir()
    (tmp_path / "outside.txt").write_text("secret\n", encoding="utf-8")
    return Workspace(working_dir=inside, boundary=Boundary((inside,), "strict"))


@pytest.fixture
def guarded(bounded: Workspace) -> Workspace:
    """Return the bounded workspace in guarded mode, with a state directory."""
    bounded.boundary = Boundary(bounded.boundary.roots, "guarded")
    bounded.state_dir = bounded.working_dir / ".state"
    return bounded
