"""Behaviour of the file tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_shell_tools import Boundary, OutsideBoundaryError, ToolError, Workspace, files


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


def test_writing_creates_missing_directories(space: Workspace, tmp_path: Path) -> None:
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
    assert "afile  2 bytes" in listing


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


def test_deleting_moves_a_file_to_the_trash(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("kept", encoding="utf-8")

    files.file_delete(space, "a.txt")

    trashed = list((tmp_path / "state/trash").iterdir())
    assert not (tmp_path / "a.txt").exists()
    assert [entry.name.endswith("-a.txt") for entry in trashed] == [True]
    assert trashed[0].read_text(encoding="utf-8") == "kept"


def test_deleting_moves_a_directory_with_content_to_the_trash(
    space: Workspace, tmp_path: Path
) -> None:
    (tmp_path / "adir").mkdir()
    (tmp_path / "adir/inside").write_text("x", encoding="utf-8")

    answer = files.file_delete(space, "adir")

    kept = Path(answer.rsplit(": ", 1)[1])
    assert not (tmp_path / "adir").exists()
    assert (kept / "inside").read_text(encoding="utf-8") == "x"


def test_deleting_the_same_name_twice_keeps_both(
    space: Workspace, tmp_path: Path
) -> None:
    for content in ("first", "second"):
        (tmp_path / "a.txt").write_text(content, encoding="utf-8")
        files.file_delete(space, "a.txt")

    assert len(list((tmp_path / "state/trash").iterdir())) == 2


def test_deleting_something_missing_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError):
        files.file_delete(space, "nowhere")


def test_deleting_without_a_state_directory_is_refused_and_keeps_the_file(
    tmp_path: Path,
) -> None:
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")

    with pytest.raises(ToolError, match="no state_dir"):
        files.file_delete(Workspace(working_dir=tmp_path), "a.txt")

    assert (tmp_path / "a.txt").is_file()


def test_guarded_mode_refuses_deleting_outside_the_roots(guarded: Workspace) -> None:
    outside = guarded.working_dir.parent / "outside.txt"

    with pytest.raises(OutsideBoundaryError):
        files.file_delete(guarded, str(outside))

    assert outside.is_file()


def test_guarded_mode_refuses_moving_out_of_the_roots(guarded: Workspace) -> None:
    (guarded.working_dir / "a.txt").write_text("x", encoding="utf-8")

    with pytest.raises(OutsideBoundaryError):
        files.file_move(guarded, "a.txt", "../a.txt")

    assert (guarded.working_dir / "a.txt").is_file()


def test_guarded_mode_reads_outside_but_writes_only_inside(guarded: Workspace) -> None:
    beside = guarded.working_dir.parent / "beside.txt"

    assert files.file_read(guarded, "../outside.txt") == "secret\n"
    with pytest.raises(OutsideBoundaryError, match="mcp_shell_grant.py"):
        files.file_write(guarded, str(beside), "written")

    assert not beside.exists()


def test_open_mode_deletes_outside_the_roots(guarded: Workspace) -> None:
    guarded.boundary = Boundary(guarded.boundary.roots, "open")
    outside = guarded.working_dir.parent / "outside.txt"

    files.file_delete(guarded, str(outside))

    assert not outside.exists()


def test_moving_takes_the_file_along(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("content", encoding="utf-8")

    files.file_move(space, "a.txt", "b.txt")

    assert not (tmp_path / "a.txt").exists()
    assert (tmp_path / "b.txt").read_text(encoding="utf-8") == "content"


def test_moving_something_missing_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError, match="nothing to transfer"):
        files.file_move(space, "nowhere", "elsewhere")


def test_a_failed_move_says_move(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "adir").mkdir()

    with pytest.raises(ToolError, match="could not move"):
        files.file_move(space, "adir", "adir/below")


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


def test_a_failed_copy_says_copy(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "adir").mkdir()

    with pytest.raises(ToolError, match="could not copy"):
        files.file_copy(space, "adir", "adir")


def test_copying_a_directory_keeps_links_as_links(bounded: Workspace) -> None:
    inside = bounded.working_dir
    (inside / "adir").mkdir()
    (inside / "adir/link").symlink_to(inside.parent / "outside.txt")

    files.file_copy(bounded, "adir", "copy")

    assert (inside / "copy/link").is_symlink()


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


def test_the_tree_counts_what_it_left_out(tmp_path: Path) -> None:
    space = Workspace(working_dir=tmp_path, max_results=5)
    (tmp_path / "big").mkdir()
    for number in range(40):
        (tmp_path / f"big/f{number}").write_text("x", encoding="utf-8")

    assert "36 more" in files.tree(space, "big", 2)


def test_the_tree_leaves_out_the_noise(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git/config").write_text("x", encoding="utf-8")

    shown = files.tree(space, ".")

    assert "src/" in shown
    assert ".git" not in shown


def test_the_tree_does_not_follow_a_link_out_of_bounds(bounded: Workspace) -> None:
    elsewhere = bounded.working_dir.parent / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "hidden.txt").write_text("x", encoding="utf-8")
    (bounded.working_dir / "link").symlink_to(elsewhere)

    assert "hidden.txt" not in files.tree(bounded, ".")


def test_the_tree_of_a_missing_directory_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError):
        files.tree(space, "nowhere")


def test_file_info_names_kind_and_size(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "note.txt").write_text("hello", encoding="utf-8")

    out = files.file_info(space, "note.txt")

    assert "kind:      file" in out
    assert "size:      5 bytes" in out
    assert "modified:" in out


def test_file_info_counts_directory_entries(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub/a").write_text("a", encoding="utf-8")
    (tmp_path / "sub/b").write_text("b", encoding="utf-8")

    out = files.file_info(space, "sub")

    assert "kind:      directory" in out
    assert "entries:   2" in out


def test_file_info_on_a_missing_path_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError):
        files.file_info(space, "nowhere")


def test_head_and_tail_take_opposite_ends(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "log").write_text(
        "\n".join(str(n) for n in range(1, 21)), encoding="utf-8"
    )

    assert files.head(space, "log", 3) == "1\n2\n3"
    assert files.tail(space, "log", 3) == "18\n19\n20"


def test_head_and_tail_cope_with_short_files(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "short").write_text("only one line", encoding="utf-8")

    assert files.head(space, "short", 10) == "only one line"
    assert files.tail(space, "short", 10) == "only one line"


def test_head_and_tail_give_at_least_one_line(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "log").write_text("first\nlast", encoding="utf-8")

    assert files.head(space, "log", 0) == "first"
    assert files.tail(space, "log", 0) == "last"
