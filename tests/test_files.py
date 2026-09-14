"""Behaviour of the file tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_shell_tools import files
from mcp_shell_tools.workspace import ToolError, Workspace


def test_reading_returns_the_content(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hello\nworld\n", encoding="utf-8")

    assert files.file_read(space, "a.txt") == "hello\nworld\n"


def test_reading_a_range_returns_those_lines(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")

    assert files.file_read(space, "a.txt", 2, 3) == "two\nthree"


def test_reading_from_a_line_to_the_end(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("one\ntwo\nthree\n", encoding="utf-8")

    assert files.file_read(space, "a.txt", 2) == "two\nthree"


def test_reading_an_empty_file_returns_nothing(
    space: Workspace, tmp_path: Path
) -> None:
    (tmp_path / "empty.txt").write_text("", encoding="utf-8")

    assert files.file_read(space, "empty.txt") == ""


def test_reading_a_missing_file_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError):
        files.file_read(space, "nowhere.txt")


def test_writing_creates_the_file(space: Workspace, tmp_path: Path) -> None:
    files.file_write(space, "new.txt", "content")

    assert (tmp_path / "new.txt").read_text(encoding="utf-8") == "content"


def test_writing_creates_missing_directories(
    space: Workspace, tmp_path: Path
) -> None:
    files.file_write(space, "deep/down/new.txt", "content")

    assert (tmp_path / "deep/down/new.txt").is_file()


def test_writing_replaces_what_was_there(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("old", encoding="utf-8")

    files.file_write(space, "a.txt", "new")

    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "new"


def test_appending_keeps_what_was_there(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("one\n", encoding="utf-8")

    files.file_append(space, "a.txt", "two\n")

    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "one\ntwo\n"


def test_appending_to_a_missing_file_creates_it(
    space: Workspace, tmp_path: Path
) -> None:
    files.file_append(space, "fresh.txt", "text")

    assert (tmp_path / "fresh.txt").read_text(encoding="utf-8") == "text"


def test_listing_names_the_entries(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "adir").mkdir()
    (tmp_path / "afile").write_text("xx", encoding="utf-8")

    listing = files.file_list(space, ".")

    assert "adir/" in listing
    assert "afile" in listing


def test_listing_puts_directories_first(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "zdir").mkdir()
    (tmp_path / "afile").write_text("x", encoding="utf-8")

    rows = files.file_list(space, ".").splitlines()

    assert rows[0] == "zdir/"


def test_listing_an_empty_directory_says_so(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()

    assert "is empty" in files.file_list(space, "empty")


def test_listing_a_missing_directory_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError):
        files.file_list(space, "nowhere")


def test_listing_stops_at_the_limit(tmp_path: Path) -> None:
    space = Workspace(working_dir=tmp_path, max_results=3)
    for number in range(10):
        (tmp_path / f"file{number}").write_text("x", encoding="utf-8")

    listing = files.file_list(space, ".")

    assert "7 more" in listing


def test_deleting_removes_a_file(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")

    files.file_delete(space, "a.txt")

    assert not (tmp_path / "a.txt").exists()


def test_deleting_removes_a_directory_with_content(
    space: Workspace, tmp_path: Path
) -> None:
    (tmp_path / "adir").mkdir()
    (tmp_path / "adir/inside").write_text("x", encoding="utf-8")

    files.file_delete(space, "adir")

    assert not (tmp_path / "adir").exists()


def test_deleting_something_missing_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError):
        files.file_delete(space, "nowhere")


def test_moving_takes_the_file_along(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("content", encoding="utf-8")

    files.file_move(space, "a.txt", "b.txt")

    assert not (tmp_path / "a.txt").exists()
    assert (tmp_path / "b.txt").read_text(encoding="utf-8") == "content"


def test_moving_something_missing_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError):
        files.file_move(space, "nowhere", "elsewhere")


def test_copying_leaves_the_original(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("content", encoding="utf-8")

    files.file_copy(space, "a.txt", "b.txt")

    assert (tmp_path / "a.txt").is_file()
    assert (tmp_path / "b.txt").read_text(encoding="utf-8") == "content"


def test_copying_a_directory_takes_the_content(
    space: Workspace, tmp_path: Path
) -> None:
    (tmp_path / "adir").mkdir()
    (tmp_path / "adir/inside").write_text("x", encoding="utf-8")

    files.file_copy(space, "adir", "copy")

    assert (tmp_path / "copy/inside").read_text(encoding="utf-8") == "x"


def test_the_tree_shows_what_is_below(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "adir").mkdir()
    (tmp_path / "adir/inside").write_text("x", encoding="utf-8")

    shown = files.tree(space, ".")

    assert "adir/" in shown
    assert "inside" in shown


def test_the_tree_stops_at_the_given_depth(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "one/two").mkdir(parents=True)
    (tmp_path / "one/two/deep").write_text("x", encoding="utf-8")

    shown = files.tree(space, ".", depth=1)

    assert "one/" in shown
    assert "deep" not in shown


def test_the_tree_of_a_missing_directory_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError):
        files.tree(space, "nowhere")
