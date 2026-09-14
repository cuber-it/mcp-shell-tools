"""Behaviour of the note and session tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_shell_tools import OutsideBoundaryError, ToolError, Workspace, notes


def test_a_note_is_kept_and_shown(space: Workspace) -> None:
    notes.memory_add(space, "remember this")

    assert "remember this" in notes.memory_show(space)


def test_an_empty_note_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError):
        notes.memory_add(space, "   ")


def test_without_notes_it_says_so(space: Workspace) -> None:
    assert notes.memory_show(space) == "nothing noted"


def test_clearing_drops_the_notes(space: Workspace) -> None:
    notes.memory_add(space, "one")

    assert "dropped 1" in notes.memory_clear(space)
    assert notes.memory_show(space) == "nothing noted"


def test_a_session_survives_and_comes_back(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "below").mkdir()
    space.working_dir = tmp_path / "below"
    notes.memory_add(space, "kept")
    notes.session_save(space, "work", "a summary")
    notes.memory_clear(space)
    space.working_dir = tmp_path

    answer = notes.session_resume(space, "work")

    assert "a summary" in answer
    assert "kept" in notes.memory_show(space)
    assert space.working_dir == tmp_path / "below"


def test_resuming_something_missing_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError, match="no such session"):
        notes.session_resume(space, "never-saved")


def test_resuming_a_broken_file_is_refused(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "state").mkdir()
    (tmp_path / "state/broken.session.json").write_text("[1, 2]", encoding="utf-8")

    with pytest.raises(ToolError, match="not a session file"):
        notes.session_resume(space, "broken")


@pytest.mark.parametrize("name", ["", "../escape", ".hidden"])
def test_a_bad_session_name_is_refused(space: Workspace, name: str) -> None:
    with pytest.raises(ToolError):
        notes.session_save(space, name)


def test_sessions_are_listed_newest_first(space: Workspace) -> None:
    notes.session_save(space, "older", "first")
    notes.session_save(space, "newer", "second")

    listed = notes.session_list(space)

    assert listed.splitlines()[0].startswith("newer")


def test_without_sessions_it_says_so(space: Workspace) -> None:
    assert notes.session_list(space) == "no sessions saved"


def test_without_a_state_directory_saving_is_refused(tmp_path: Path) -> None:
    space = Workspace(working_dir=tmp_path)

    with pytest.raises(ToolError, match="no state_dir"):
        notes.session_save(space, "work")


def test_a_refused_resume_changes_nothing(tmp_path: Path) -> None:
    inside = tmp_path / "inside"
    inside.mkdir()
    state = tmp_path / "state"
    space = Workspace(working_dir=inside, allowed_roots=(inside,), state_dir=state)
    notes.memory_add(space, "saved note")
    notes.session_save(space, "s")
    saved = state / "s.session.json"
    saved.write_text(
        saved.read_text(encoding="utf-8").replace(str(inside), "/etc"),
        encoding="utf-8",
    )
    notes.memory_clear(space)
    notes.memory_add(space, "current note")

    with pytest.raises(OutsideBoundaryError):
        notes.session_resume(space, "s")

    assert space.working_dir == inside
    assert "current note" in notes.memory_show(space)
    assert "saved note" not in notes.memory_show(space)
