"""How paths are resolved and how limits are kept."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_shell_tools.workspace import (
    OutsideBoundaryError,
    ToolError,
    Workspace,
    read_text,
    workspace_from,
)


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


def test_a_path_inside_the_roots_is_allowed(tmp_path: Path) -> None:
    space = Workspace(working_dir=tmp_path, allowed_roots=(tmp_path,))

    assert space.resolve("below/file") == tmp_path / "below/file"


def test_the_root_itself_is_allowed(tmp_path: Path) -> None:
    space = Workspace(working_dir=tmp_path, allowed_roots=(tmp_path,))

    assert space.resolve(str(tmp_path)) == tmp_path


def test_a_path_outside_the_roots_is_refused(tmp_path: Path) -> None:
    space = Workspace(working_dir=tmp_path, allowed_roots=(tmp_path,))

    with pytest.raises(OutsideBoundaryError):
        space.resolve("/etc/hostname")


def test_climbing_out_of_the_roots_is_refused(tmp_path: Path) -> None:
    space = Workspace(working_dir=tmp_path, allowed_roots=(tmp_path,))

    with pytest.raises(OutsideBoundaryError):
        space.resolve("../..")


def test_short_output_is_left_alone(space: Workspace) -> None:
    assert space.cut("hello") == "hello"


def test_long_output_is_cut_and_says_so(tmp_path: Path) -> None:
    space = Workspace(working_dir=tmp_path, max_output=10)

    cut = space.cut("x" * 25)

    assert cut.startswith("x" * 10)
    assert "15 more characters" in cut


def test_output_at_the_limit_is_not_cut(tmp_path: Path) -> None:
    space = Workspace(working_dir=tmp_path, max_output=5)

    assert space.cut("12345") == "12345"


def test_reading_a_missing_file_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError):
        read_text(space, "nowhere.txt")


def test_reading_a_directory_is_refused(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "adir").mkdir()

    with pytest.raises(ToolError):
        read_text(space, "adir")


def test_reading_something_that_is_not_text_is_refused(
    space: Workspace, tmp_path: Path
) -> None:
    (tmp_path / "binary").write_bytes(b"\xff\xfe\x00\x01")

    with pytest.raises(ToolError):
        read_text(space, "binary")


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
