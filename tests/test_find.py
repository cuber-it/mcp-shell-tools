"""Behaviour of the tools that find files and text."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_shell_tools import ToolError, Workspace, find


def test_globbing_finds_the_matching_files(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    (tmp_path / "b.txt").write_text("x", encoding="utf-8")

    found = find.glob_search(space, "*.py")

    assert "a.py" in found
    assert "b.txt" not in found


def test_globbing_without_a_match_says_so(space: Workspace) -> None:
    assert "nothing matches" in find.glob_search(space, "*.nothing")


def test_globbing_leaves_out_the_noise(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git/config").write_text("x", encoding="utf-8")

    assert "nothing matches" in find.glob_search(space, "**/config")


def test_globbing_below_a_skipped_directory_still_finds(tmp_path: Path) -> None:
    root = tmp_path / ".venv" / "project"
    root.mkdir(parents=True)
    (root / "a.py").write_text("x", encoding="utf-8")

    assert "a.py" in find.glob_search(Workspace(working_dir=root), "*.py")


def test_globbing_does_not_climb_out_of_bounds(bounded: Workspace) -> None:
    assert "outside.txt" not in find.glob_search(bounded, "../*")


def test_globbing_with_an_absolute_pattern_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError):
        find.glob_search(space, "/etc/*")


def test_grep_finds_the_line(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("one\nneedle here\nthree\n", encoding="utf-8")

    assert "a.txt:2: needle here" in find.grep(space, "needle")


def test_grep_without_a_match_says_so(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("nothing\n", encoding="utf-8")

    assert "no line matches" in find.grep(space, "absent")


def test_grep_with_a_broken_pattern_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError):
        find.grep(space, "[unclosed")


def test_grep_in_a_single_file_works(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("needle\n", encoding="utf-8")

    assert "needle" in find.grep(space, "needle", "a.txt")


def test_grep_passes_over_files_without_text(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "binary").write_bytes(b"\xff\xfeneedle")
    (tmp_path / "a.txt").write_text("needle\n", encoding="utf-8")

    assert find.grep(space, "needle").endswith("a.txt:1: needle")


def test_grep_stops_at_the_limit(tmp_path: Path) -> None:
    space = Workspace(working_dir=tmp_path, max_results=3)
    (tmp_path / "a.txt").write_text("needle\n" * 10, encoding="utf-8")

    assert len(find.grep(space, "needle").splitlines()) == 3


def test_grep_below_a_skipped_directory_still_finds(tmp_path: Path) -> None:
    root = tmp_path / ".venv" / "project"
    root.mkdir(parents=True)
    (root / "a.txt").write_text("needle\n", encoding="utf-8")

    assert "a.txt:1: needle" in find.grep(Workspace(working_dir=root), "needle")


def test_grep_does_not_read_out_of_bounds(bounded: Workspace) -> None:
    assert "no line matches" in find.grep(bounded, "secret", ".", "../*")


def test_grep_does_not_follow_a_link_out_of_bounds(bounded: Workspace) -> None:
    inside = bounded.working_dir
    (inside / "link.txt").symlink_to(inside.parent / "outside.txt")

    assert "no line matches" in find.grep(bounded, "secret")
