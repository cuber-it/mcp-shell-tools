"""Fixtures shared by the test modules."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_shell_tools.workspace import Workspace


@pytest.fixture
def space(tmp_path: Path) -> Workspace:
    """Return a workspace rooted in a fresh temporary directory."""
    return Workspace(working_dir=tmp_path, state_dir=tmp_path / "state")
