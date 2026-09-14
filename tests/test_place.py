"""Behaviour of the tools about where work happens."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_shell_tools import OutsideBoundaryError, ToolError, Workspace, place


def test_the_working_directory_is_reported(space: Workspace, tmp_path: Path) -> None:
    assert place.cwd(space) == str(tmp_path)


def test_changing_the_directory_holds(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "below").mkdir()

    place.cd(space, "below")

    assert place.cwd(space) == str(tmp_path / "below")


def test_changing_to_a_missing_directory_is_refused(
    space: Workspace, tmp_path: Path
) -> None:
    with pytest.raises(ToolError):
        place.cd(space, "nowhere")

    assert space.working_dir == tmp_path


def test_changing_out_of_bounds_is_refused(bounded: Workspace) -> None:
    with pytest.raises(OutsideBoundaryError):
        place.cd(bounded, "..")


def test_the_project_context_is_returned(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("# rules\n", encoding="utf-8")

    assert place.project_context(space) == "# rules\n"


def test_a_directory_without_context_says_so(space: Workspace) -> None:
    assert "no CLAUDE.md" in place.project_context(space)


def test_a_long_context_is_cut_and_says_so(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("x" * 4010, encoding="utf-8")

    assert "10 more" in place.project_context(space)


def test_a_context_linked_out_of_bounds_is_refused(bounded: Workspace) -> None:
    inside = bounded.working_dir
    (inside / "CLAUDE.md").symlink_to(inside.parent / "outside.txt")

    with pytest.raises(OutsideBoundaryError):
        place.project_context(bounded)
