"""How paths are resolved, checked against the boundary, and searched."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from mcp_shell_tools import (
    Boundary,
    GrantError,
    NotPermittedError,
    OutsideBoundaryError,
    ToolError,
    Workspace,
    workspace_from,
)
from mcp_shell_tools.boundary import Access
from mcp_shell_tools.grant import GRANT_FILE, Grant, write_grant


def test_a_relative_path_is_taken_from_the_working_directory(
    space: Workspace, tmp_path: Path
) -> None:
    assert space.resolve("some/file.txt") == tmp_path / "some/file.txt"


def test_an_absolute_path_is_kept(space: Workspace) -> None:
    assert space.resolve("/etc/hostname") == Path("/etc/hostname")


def test_a_tilde_is_expanded(space: Workspace) -> None:
    assert space.resolve("~") == Path.home()


def test_without_roots_everything_is_allowed(space: Workspace) -> None:
    assert space.resolve("/etc", Access.DESTROY) == Path("/etc")


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


def test_the_refusal_names_the_access(bounded: Workspace) -> None:
    with pytest.raises(OutsideBoundaryError, match="for destroy"):
        bounded.resolve("/etc/hostname", Access.DESTROY)


def test_guarded_resolves_reading_outside_but_not_changing(
    guarded: Workspace,
) -> None:
    assert guarded.resolve("../outside.txt").name == "outside.txt"

    for access in (Access.WRITE, Access.DESTROY):
        with pytest.raises(OutsideBoundaryError):
            guarded.resolve("../outside.txt", access)


def test_the_refusal_names_the_grant_that_would_allow_it(guarded: Workspace) -> None:
    parent = guarded.working_dir.parent

    with pytest.raises(OutsideBoundaryError) as refused:
        guarded.resolve("../outside.txt", Access.WRITE)

    expected = f"mcp_shell_grant.py --state-dir {guarded.state_dir} set --root {parent}"
    assert expected in str(refused.value)


def test_a_grant_lets_writing_reach_an_added_root(guarded: Workspace) -> None:
    parent = guarded.working_dir.parent
    write_grant(guarded.state(), Grant(time.time() + 60, roots=(parent,)))

    assert guarded.resolve("../outside.txt", Access.WRITE) == parent / "outside.txt"


def test_a_lapsed_grant_reaches_no_further(guarded: Workspace) -> None:
    parent = guarded.working_dir.parent
    write_grant(guarded.state(), Grant(time.time() - 1, roots=(parent,)))

    with pytest.raises(OutsideBoundaryError):
        guarded.resolve("../outside.txt", Access.WRITE)


def test_an_unusable_grant_file_refuses_even_reading(guarded: Workspace) -> None:
    guarded.state().mkdir()
    (guarded.state() / GRANT_FILE).write_text("not json", encoding="utf-8")

    with pytest.raises(GrantError):
        guarded.resolve("a.txt")


@pytest.mark.parametrize("mode", ["open", "guarded"])
def test_the_grant_file_is_out_of_reach_for_changes(tmp_path: Path, mode: str) -> None:
    state = tmp_path / "state"
    space = Workspace(
        working_dir=tmp_path, boundary=Boundary(mode=mode), state_dir=state
    )
    held = write_grant(state, Grant(time.time() + 60, execute=True))

    assert space.resolve(str(held)) == held
    refused = [
        (held, Access.WRITE),
        (state, Access.WRITE),
        (held, Access.DESTROY),
        (state, Access.DESTROY),
        (tmp_path, Access.DESTROY),
    ]
    for target, access in refused:
        with pytest.raises(NotPermittedError, match="grant file"):
            space.resolve(str(target), access)


def test_writing_above_the_state_directory_is_not_mistaken_for_the_grant(
    space: Workspace, tmp_path: Path
) -> None:
    write_grant(space.state(), Grant(time.time() + 60, execute=True))

    assert space.resolve(str(tmp_path), Access.WRITE) == tmp_path
    assert space.resolve("beside.txt", Access.WRITE) == tmp_path / "beside.txt"


def test_globbing_for_changes_passes_over_the_grant_file(space: Workspace) -> None:
    held = write_grant(space.state(), Grant(time.time() + 60, execute=True))

    assert held in space.glob(space.state(), "*")
    assert held not in space.glob(space.state(), "*", Access.DESTROY)


def test_switched_off_commands_are_refused_with_the_grant(tmp_path: Path) -> None:
    space = Workspace(
        working_dir=tmp_path, boundary=Boundary(execute=False), state_dir=tmp_path
    )

    with pytest.raises(NotPermittedError, match=r"set --exec --for 1h"):
        space.permit_execute()


def test_a_grant_switches_commands_on(tmp_path: Path) -> None:
    space = Workspace(
        working_dir=tmp_path, boundary=Boundary(execute=False), state_dir=tmp_path
    )
    write_grant(tmp_path, Grant(time.time() + 60, execute=True))

    assert space.current().execute is True
    assert space.permit_execute() is None


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


def test_guarded_globbing_for_destroying_stays_inside(guarded: Workspace) -> None:
    inside = guarded.working_dir

    reading = guarded.glob(inside, "../*.txt")
    destroying = guarded.glob(inside, "../*.txt", Access.DESTROY)

    assert [hit.name for hit in reading] == ["outside.txt"]
    assert destroying == []


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


def test_the_trash_lies_in_the_state_directory(
    space: Workspace, tmp_path: Path
) -> None:
    assert space.trash() == tmp_path / "state/trash"


def test_without_a_state_directory_there_is_no_trash(tmp_path: Path) -> None:
    with pytest.raises(ToolError, match="no state_dir"):
        Workspace(working_dir=tmp_path).trash()


def test_configuration_is_read(tmp_path: Path) -> None:
    space = workspace_from(
        {
            "working_dir": str(tmp_path),
            "allowed_roots": [str(tmp_path)],
            "mode": "strict",
            "execute": False,
            "timeout": 5,
            "max_output": 7,
        }
    )

    assert space.working_dir == tmp_path
    assert space.boundary == Boundary((tmp_path,), "strict", execute=False)
    assert space.timeout == 5
    assert space.max_output == 7


def test_an_empty_configuration_still_works(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    space = workspace_from({})

    assert space.working_dir == tmp_path.resolve()
    assert space.boundary == Boundary()


def test_an_unknown_mode_in_the_configuration_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ToolError, match="no such mode"):
        workspace_from({"working_dir": str(tmp_path), "mode": "loose"})


def test_a_working_directory_that_is_no_directory_is_refused(tmp_path: Path) -> None:
    afile = tmp_path / "afile"
    afile.write_text("x", encoding="utf-8")

    with pytest.raises(ToolError):
        workspace_from({"working_dir": str(afile)})
