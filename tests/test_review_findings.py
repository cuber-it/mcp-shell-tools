"""What the review turned up, pinned so it cannot come back."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_shell_tools import edit, files, notes, system
from mcp_shell_tools.workspace import (
    OutsideBoundaryError,
    ToolError,
    Workspace,
    render,
    size,
)


@pytest.fixture
def space(tmp_path: Path) -> Workspace:
    """Return a workspace that cuts listings after five rows."""
    return Workspace(working_dir=tmp_path, max_results=5)


def test_copy_failure_names_the_verb_properly(space: Workspace) -> None:
    (space.working_dir / "b").mkdir()

    with pytest.raises(ToolError, match="could not copy"):
        files.file_copy(space, "b", "b")


def test_move_failure_names_the_verb_properly(space: Workspace) -> None:
    with pytest.raises(ToolError, match="could not move|nothing to transfer"):
        files.file_move(space, "missing", "elsewhere")


def test_tree_counts_what_it_left_out(space: Workspace) -> None:
    big = space.working_dir / "big"
    big.mkdir()
    for number in range(40):
        (big / f"f{number}").write_text("x")

    assert "36 more" in files.tree(space, "big", 2)


def test_find_replace_leaves_git_and_venv_alone(space: Workspace) -> None:
    for directory in (".git", ".venv"):
        (space.working_dir / directory).mkdir()
        (space.working_dir / directory / "config").write_text("alt")
    (space.working_dir / "normal.txt").write_text("alt")

    edit.find_replace(space, "alt", "neu", ".", "*", apply=True)

    assert (space.working_dir / ".git" / "config").read_text() == "alt"
    assert (space.working_dir / ".venv" / "config").read_text() == "alt"
    assert (space.working_dir / "normal.txt").read_text() == "neu"


def test_session_resume_cannot_escape_the_allowed_roots(tmp_path: Path) -> None:
    inside = tmp_path / "inside"
    inside.mkdir()
    state = tmp_path / "state"
    space = Workspace(
        working_dir=inside, allowed_roots=(inside,), state_dir=state
    )
    notes.session_save(space, "s")

    # Hand-edit the saved session to point somewhere it may not go.
    saved = state / "s.session.json"
    saved.write_text(saved.read_text().replace(str(inside), "/etc"))

    with pytest.raises(OutsideBoundaryError):
        notes.session_resume(space, "s")
    assert space.working_dir == inside


def test_ps_has_no_column_it_cannot_measure(space: Workspace) -> None:
    assert "CPU" not in system.ps(space, "").splitlines()[0]


def test_disk_usage_counts_each_file_once_per_ancestor(space: Workspace) -> None:
    deep = space.working_dir / "d1" / "d2"
    deep.mkdir(parents=True)
    (deep / "f").write_text("x" * 3000)

    rows = system.disk_usage(space, ".", 2).splitlines()
    measured = {row.split()[-1]: row.split()[0] for row in rows if "d1" in row}

    assert measured["d1"] == measured["d1/d2"]


def test_size_renders_every_unit() -> None:
    assert size(500) == "500B"
    assert size(2_000_000) == "1.9M"
    assert size(3.5e12).endswith("T")


def test_render_says_how_many_it_dropped() -> None:
    assert render(["a", "b", "c"], 2, "nothing") == "a\nb\n[... 1 more]"
    assert render(["a"], 5, "nothing") == "a"
    assert render([], 5, "nothing") == "nothing"
