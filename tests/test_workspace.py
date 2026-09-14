"""How paths are resolved, checked against the boundary, and searched."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_shell_tools import OutsideBoundaryError, ToolError, Workspace, workspace_from


def test_a_relative_path_is_taken_from_the_working_directory(
    space: Workspace, tmp_path: Path
) -> None:
    assert space.resolve("some/file.txt") == tmp_path / "some/file.txt"


def test_an_absolute_path_is_kept(space: Workspace) -> None:
    assert space.resolve("/etc/hostname") == Path("/etc/hostname")


def test_a_tilde_is_expanded(space: Workspace) -> None:
    assert space.resolve("~") == Path.home()


def test_without_roots_everything_is_allowed(space: Workspace) -> None:
    assert space.resolve("/etc") == Path("/etc")


def test_a_path_inside_the_roots_is_allowed(bounded: Workspace) -> None:
    inside = bounded.working_dir

    assert bounded.resolve("below/file") == inside / "below/file"


def test_the_root_itself_is_allowed(bounded: Workspace) -> None:
    assert bounded.resolve(str(bounded.working_dir)) == bounded.working_dir


def test_a_path_outside_the_roots_is_refused(bounded: Workspace) -> None:
    with pytest.raises(OutsideBoundaryError):
        bounded.resolve("/etc/hostname")


def test_climbing_out_of_the_roots_is_refused(bounded: Workspace) -> None:
    with pytest.raises(OutsideBoundaryError):
        bounded.resolve("../outside.txt")


def test_a_link_out_of_the_roots_is_refused(bounded: Workspace) -> None:
    (bounded.working_dir / "link").symlink_to(bounded.working_dir.parent)

    with pytest.raises(OutsideBoundaryError):
        bounded.resolve("link/outside.txt")


def test_an_existing_path_is_returned(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")

    assert space.existing("a.txt") == tmp_path / "a.txt"


def test_a_missing_path_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError, match="no such path"):
        space.existing("nowhere")


def test_a_directory_is_returned(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "adir").mkdir()

    assert space.directory("adir") == tmp_path / "adir"


def test_a_file_is_not_a_directory(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")

    with pytest.raises(ToolError, match="no such directory"):
        space.directory("a.txt")


def test_globbing_returns_sorted_hits(space: Workspace, tmp_path: Path) -> None:
    for name in ("b.py", "a.py"):
        (tmp_path / name).write_text("x", encoding="utf-8")

    assert space.glob(tmp_path, "*.py") == [tmp_path / "a.py", tmp_path / "b.py"]


def test_globbing_leaves_out_skipped_directories_below_the_root(
    space: Workspace, tmp_path: Path
) -> None:
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv/a.py").write_text("x", encoding="utf-8")

    assert space.glob(tmp_path, "**/*.py") == []


def test_globbing_a_root_inside_a_skipped_directory_finds(tmp_path: Path) -> None:
    root = tmp_path / ".venv" / "project"
    root.mkdir(parents=True)
    (root / "a.py").write_text("x", encoding="utf-8")

    assert Workspace(working_dir=root).glob(root, "*.py") == [root / "a.py"]


def test_globbing_does_not_climb_out_of_the_roots(bounded: Workspace) -> None:
    hits = bounded.glob(bounded.working_dir, "../*")

    assert [hit.name for hit in hits] == ["inside"]


def test_globbing_leaves_out_links_out_of_the_roots(bounded: Workspace) -> None:
    inside = bounded.working_dir
    (inside / "link.txt").symlink_to(inside.parent / "outside.txt")

    assert bounded.glob(inside, "*") == []


def test_without_roots_a_pattern_may_climb(tmp_path: Path) -> None:
    inside = tmp_path / "inside"
    inside.mkdir()
    (tmp_path / "beside.txt").write_text("x", encoding="utf-8")

    hits = Workspace(working_dir=inside).glob(inside, "../*.txt")

    assert [hit.name for hit in hits] == ["beside.txt"]


@pytest.mark.parametrize("pattern", ["", "/etc/*"])
def test_an_unusable_pattern_is_refused(space: Workspace, pattern: str) -> None:
    with pytest.raises(ToolError, match="not a usable pattern"):
        space.glob(space.working_dir, pattern)


def test_configuration_is_read(tmp_path: Path) -> None:
    space = workspace_from(
        {"working_dir": str(tmp_path), "timeout": 5, "max_output": 7}
    )

    assert space.working_dir == tmp_path
    assert space.timeout == 5
    assert space.max_output == 7


def test_an_empty_configuration_still_works(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    space = workspace_from({})

    assert space.working_dir == tmp_path.resolve()
    assert not space.allowed_roots


def test_a_working_directory_that_is_no_directory_is_refused(tmp_path: Path) -> None:
    afile = tmp_path / "afile"
    afile.write_text("x", encoding="utf-8")

    with pytest.raises(ToolError):
        workspace_from({"working_dir": str(afile)})
