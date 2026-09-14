"""Behaviour of the editing, finding, running, place and note tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_shell_tools import edit, find, notes, place, run
from mcp_shell_tools.workspace import ToolError, Workspace


def test_replacing_changes_the_one_passage(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("keep this change", encoding="utf-8")

    edit.str_replace(space, "a.txt", "this", "that")

    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "keep that change"


def test_replacing_a_missing_passage_is_refused(
    space: Workspace, tmp_path: Path
) -> None:
    (tmp_path / "a.txt").write_text("content", encoding="utf-8")

    with pytest.raises(ToolError):
        edit.str_replace(space, "a.txt", "absent", "new")


def test_an_ambiguous_passage_is_refused_and_changes_nothing(
    space: Workspace, tmp_path: Path
) -> None:
    (tmp_path / "a.txt").write_text("same same", encoding="utf-8")

    with pytest.raises(ToolError):
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
    shown = edit.diff_preview(space, "new.txt", "content\n")

    assert "+content" in shown


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


def test_grep_finds_the_line(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("one\nneedle here\nthree\n", encoding="utf-8")

    found = find.grep(space, "needle")

    assert "a.txt:2: needle here" in found


def test_grep_without_a_match_says_so(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("nothing\n", encoding="utf-8")

    assert "no line matches" in find.grep(space, "absent")


def test_grep_with_a_broken_pattern_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError):
        find.grep(space, "[unclosed")


def test_grep_in_a_single_file_works(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("needle\n", encoding="utf-8")

    assert "needle" in find.grep(space, "needle", "a.txt")


def test_a_command_returns_its_output(space: Workspace) -> None:
    assert "hello" in run.shell_exec(space, "echo hello")


def test_a_command_runs_in_the_working_directory(
    space: Workspace, tmp_path: Path
) -> None:
    assert str(tmp_path) in run.shell_exec(space, "pwd")


def test_a_failing_command_names_its_status(space: Workspace) -> None:
    assert "exit status 3" in run.shell_exec(space, "exit 3")


def test_a_command_without_output_says_so(space: Workspace) -> None:
    assert run.shell_exec(space, "true") == "[no output]"


def test_error_output_comes_back_too(space: Workspace) -> None:
    assert "trouble" in run.shell_exec(space, "echo trouble >&2")


def test_a_command_that_hangs_is_stopped(space: Workspace) -> None:
    with pytest.raises(ToolError):
        run.shell_exec(space, "sleep 5", timeout=0.2)


def test_the_environment_can_be_read(space: Workspace) -> None:
    run.set_env(space, "MCP_SHELL_PROBE", "value")

    assert run.env(space, "MCP_SHELL_PROBE") == "MCP_SHELL_PROBE=value"


def test_an_unset_variable_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError):
        run.env(space, "MCP_SHELL_DEFINITELY_UNSET")


def test_a_broken_variable_name_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError):
        run.set_env(space, "not=usable", "x")


def test_a_set_variable_reaches_the_command(space: Workspace) -> None:
    run.set_env(space, "MCP_SHELL_PROBE2", "reached")

    assert "reached" in run.shell_exec(space, "echo $MCP_SHELL_PROBE2")


def test_the_working_directory_is_reported(space: Workspace, tmp_path: Path) -> None:
    assert place.cwd(space) == str(tmp_path)


def test_changing_the_directory_holds(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "below").mkdir()

    place.cd(space, "below")

    assert place.cwd(space) == str(tmp_path / "below")


def test_changing_to_a_missing_directory_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError):
        place.cd(space, "nowhere")


def test_the_project_context_is_returned(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("# rules\n", encoding="utf-8")

    assert "# rules" in place.project_context(space)


def test_a_directory_without_context_says_so(space: Workspace) -> None:
    assert "no CLAUDE.md" in place.project_context(space)


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
    notes.memory_add(space, "kept")
    notes.session_save(space, "work", "a summary")
    notes.memory_clear(space)

    answer = notes.session_resume(space, "work")

    assert "a summary" in answer
    assert "kept" in notes.memory_show(space)
    assert (tmp_path / "state").is_dir()


def test_resuming_something_missing_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError):
        notes.session_resume(space, "never-saved")


def test_a_bad_session_name_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError):
        notes.session_save(space, "../escape")


def test_sessions_are_listed_newest_first(space: Workspace) -> None:
    notes.session_save(space, "older", "first")
    notes.session_save(space, "newer", "second")

    listed = notes.session_list(space)

    assert listed.splitlines()[0].startswith("newer")


def test_without_sessions_it_says_so(space: Workspace) -> None:
    assert notes.session_list(space) == "no sessions saved"


def test_without_a_state_directory_saving_is_refused(tmp_path: Path) -> None:
    space = Workspace(working_dir=tmp_path)

    with pytest.raises(ToolError):
        notes.session_save(space, "work")
