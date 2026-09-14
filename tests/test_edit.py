"""Behaviour of the editing tools."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from mcp_shell_tools import NotPermittedError, ToolError, Workspace, edit
from mcp_shell_tools.grant import Grant, write_grant


def test_replacing_changes_the_one_passage(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("keep this change", encoding="utf-8")

    edit.str_replace(space, "a.txt", "this", "that")

    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "keep that change"


def test_replacing_a_missing_passage_is_refused(
    space: Workspace, tmp_path: Path
) -> None:
    (tmp_path / "a.txt").write_text("content", encoding="utf-8")

    with pytest.raises(ToolError, match="not found"):
        edit.str_replace(space, "a.txt", "absent", "new")


def test_an_ambiguous_passage_is_refused_and_changes_nothing(
    space: Workspace, tmp_path: Path
) -> None:
    (tmp_path / "a.txt").write_text("same same", encoding="utf-8")

    with pytest.raises(ToolError, match="2 times"):
        edit.str_replace(space, "a.txt", "same", "other")

    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "same same"


def test_the_preview_shows_the_change(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("before\n", encoding="utf-8")

    shown = edit.diff_preview(space, "a.txt", "after\n")

    assert "-before" in shown
    assert "+after" in shown


def test_the_preview_writes_nothing(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("before\n", encoding="utf-8")

    edit.diff_preview(space, "a.txt", "after\n")

    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "before\n"


def test_the_preview_of_an_unchanged_file_says_so(
    space: Workspace, tmp_path: Path
) -> None:
    (tmp_path / "a.txt").write_text("same\n", encoding="utf-8")

    assert "would not change" in edit.diff_preview(space, "a.txt", "same\n")


def test_the_preview_of_a_new_file_shows_everything(space: Workspace) -> None:
    assert "+content" in edit.diff_preview(space, "new.txt", "content\n")


def test_find_replace_reports_without_writing(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("old and old", encoding="utf-8")

    out = edit.find_replace(space, "old", "new", ".", "*.py")

    assert "would replace 2 occurrences in 1 files" in out
    assert "nothing was written" in out
    assert (tmp_path / "a.py").read_text(encoding="utf-8") == "old and old"


def test_find_replace_writes_when_asked(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("old and old", encoding="utf-8")

    out = edit.find_replace(space, "old", "new", ".", "*.py", apply=True)

    assert "replaced 2 occurrences in 1 files" in out
    assert (tmp_path / "a.py").read_text(encoding="utf-8") == "new and new"


def test_find_replace_reaches_into_subdirectories(
    space: Workspace, tmp_path: Path
) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub/a.py").write_text("old", encoding="utf-8")

    edit.find_replace(space, "old", "new", ".", "*.py", apply=True)

    assert (tmp_path / "sub/a.py").read_text(encoding="utf-8") == "new"


def test_find_replace_honours_the_glob(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("old", encoding="utf-8")
    (tmp_path / "b.txt").write_text("old", encoding="utf-8")

    edit.find_replace(space, "old", "new", ".", "*.py", apply=True)

    assert (tmp_path / "a.py").read_text(encoding="utf-8") == "new"
    assert (tmp_path / "b.txt").read_text(encoding="utf-8") == "old"


def test_find_replace_says_so_when_nothing_matches(
    space: Workspace, tmp_path: Path
) -> None:
    (tmp_path / "a.py").write_text("nothing", encoding="utf-8")

    assert "appears in no file" in edit.find_replace(space, "old", "new")


def test_find_replace_leaves_git_and_venv_alone(
    space: Workspace, tmp_path: Path
) -> None:
    for directory in (".git", ".venv"):
        (tmp_path / directory).mkdir()
        (tmp_path / directory / "config").write_text("old", encoding="utf-8")
    (tmp_path / "normal.txt").write_text("old", encoding="utf-8")

    edit.find_replace(space, "old", "new", ".", "*", apply=True)

    assert (tmp_path / ".git/config").read_text(encoding="utf-8") == "old"
    assert (tmp_path / ".venv/config").read_text(encoding="utf-8") == "old"
    assert (tmp_path / "normal.txt").read_text(encoding="utf-8") == "new"


def test_find_replace_does_not_write_out_of_bounds(bounded: Workspace) -> None:
    outside = bounded.working_dir.parent / "outside.txt"

    edit.find_replace(bounded, "secret", "open", ".", "../*", apply=True)

    assert outside.read_text(encoding="utf-8") == "secret\n"


def test_guarded_find_replace_does_not_write_out_of_bounds(guarded: Workspace) -> None:
    outside = guarded.working_dir.parent / "outside.txt"

    edit.find_replace(guarded, "secret", "open", ".", "../*", apply=True)

    assert outside.read_text(encoding="utf-8") == "secret\n"


def test_guarded_dry_run_looks_out_of_bounds(guarded: Workspace) -> None:
    out = edit.find_replace(guarded, "secret", "open", ".", "../*")

    assert "outside.txt" in out


def test_find_replace_around_the_state_directory_leaves_the_grant(
    space: Workspace, tmp_path: Path
) -> None:
    held = write_grant(space.state(), Grant(time.time() + 60, execute=True))
    before = held.read_text(encoding="utf-8")
    (tmp_path / "a.txt").write_text('"execute": true', encoding="utf-8")

    edit.find_replace(space, "true", "false", ".", "*", apply=True)

    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == '"execute": false'
    assert held.read_text(encoding="utf-8") == before


def test_find_replace_on_the_grant_file_itself_is_refused(space: Workspace) -> None:
    held = write_grant(space.state(), Grant(time.time() + 60, execute=True))
    before = held.read_text(encoding="utf-8")

    with pytest.raises(NotPermittedError, match="grant file"):
        edit.find_replace(space, "true", "false", str(held), apply=True)

    assert held.read_text(encoding="utf-8") == before


def test_find_replace_says_when_the_limit_stopped_it(tmp_path: Path) -> None:
    space = Workspace(working_dir=tmp_path, max_results=2)
    for name in ("a", "b", "c"):
        (tmp_path / f"{name}.txt").write_text("old", encoding="utf-8")

    out = edit.find_replace(space, "old", "new", ".", "*.txt", apply=True)

    assert "stopped at the limit of 2 files" in out
    assert (tmp_path / "c.txt").read_text(encoding="utf-8") == "old"


def test_find_replace_within_the_limit_claims_no_stop(tmp_path: Path) -> None:
    space = Workspace(working_dir=tmp_path, max_results=2)
    for name in ("a", "b"):
        (tmp_path / f"{name}.txt").write_text("old", encoding="utf-8")

    out = edit.find_replace(space, "old", "new", ".", "*.txt", apply=True)

    assert "stopped" not in out


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes to read-only files")
def test_a_failed_write_names_what_was_already_changed(
    space: Workspace, tmp_path: Path
) -> None:
    (tmp_path / "a.txt").write_text("old", encoding="utf-8")
    (tmp_path / "b.txt").write_text("old", encoding="utf-8")
    (tmp_path / "b.txt").chmod(0o444)

    with pytest.raises(ToolError, match="1 files before it were already changed"):
        edit.find_replace(space, "old", "new", ".", "*.txt", apply=True)

    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "new"
    assert (tmp_path / "b.txt").read_text(encoding="utf-8") == "old"
