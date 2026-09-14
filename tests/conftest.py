"""Fixtures shared by the test modules."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_shell_tools import Workspace


@pytest.fixture
def space(tmp_path: Path) -> Workspace:
    """Return a workspace rooted in a fresh temporary directory."""
    return Workspace(working_dir=tmp_path, state_dir=tmp_path / "state")


@pytest.fixture
def bounded(tmp_path: Path) -> Workspace:
    """Return a workspace confined to ``inside``, with ``outside.txt`` beside it.

    The file outside holds the word ``secret``. A tool that shows or changes
    it has crossed the boundary.
    """
    inside = tmp_path / "inside"
    inside.mkdir()
    (tmp_path / "outside.txt").write_text("secret\n", encoding="utf-8")
    return Workspace(working_dir=inside, allowed_roots=(inside,))
