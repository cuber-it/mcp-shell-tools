"""The tools that were added back: file facts, head, tail, find_replace, which.

The system tools are checked for shape rather than content: what ps or
sysinfo report depends on the machine, so the test pins what must always be
true instead of a value that cannot be known here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_shell_tools import edit, files, run, system
from mcp_shell_tools.workspace import ToolError, Workspace


@pytest.fixture
def space(tmp_path: Path) -> Workspace:
    """Return a workspace rooted in a fresh temporary directory."""
    return Workspace(working_dir=tmp_path)


def test_file_info_names_kind_and_size(space: Workspace) -> None:
    target = space.working_dir / "note.txt"
    target.write_text("hello")

    out = files.file_info(space, "note.txt")

    assert "kind:      file" in out
    assert "size:      5 bytes" in out
    assert "modified:" in out


def test_file_info_counts_directory_entries(space: Workspace) -> None:
    (space.working_dir / "sub").mkdir()
    (space.working_dir / "sub" / "a").write_text("a")
    (space.working_dir / "sub" / "b").write_text("b")

    out = files.file_info(space, "sub")

    assert "kind:      directory" in out
    assert "entries:   2" in out


def test_file_info_on_a_missing_path_fails(space: Workspace) -> None:
    with pytest.raises(ToolError):
        files.file_info(space, "nowhere")


def test_head_and_tail_take_opposite_ends(space: Workspace) -> None:
    (space.working_dir / "log").write_text("\n".join(str(n) for n in range(1, 21)))

    assert files.head(space, "log", 3) == "1\n2\n3"
    assert files.tail(space, "log", 3) == "18\n19\n20"


def test_head_and_tail_cope_with_short_files(space: Workspace) -> None:
    (space.working_dir / "short").write_text("only one line")

    assert files.head(space, "short", 10) == "only one line"
    assert files.tail(space, "short", 10) == "only one line"


def test_find_replace_reports_without_writing(space: Workspace) -> None:
    target = space.working_dir / "a.py"
    target.write_text("alt und alt")

    out = edit.find_replace(space, "alt", "neu", ".", "*.py")

    assert "would replace 2 occurrences in 1 files" in out
    assert target.read_text() == "alt und alt"


def test_find_replace_writes_when_asked(space: Workspace) -> None:
    target = space.working_dir / "a.py"
    target.write_text("alt und alt")

    out = edit.find_replace(space, "alt", "neu", ".", "*.py", apply=True)

    assert "replaced 2 occurrences in 1 files" in out
    assert target.read_text() == "neu und neu"


def test_find_replace_honours_the_glob(space: Workspace) -> None:
    (space.working_dir / "a.py").write_text("alt")
    (space.working_dir / "b.txt").write_text("alt")

    edit.find_replace(space, "alt", "neu", ".", "*.py", apply=True)

    assert (space.working_dir / "a.py").read_text() == "neu"
    assert (space.working_dir / "b.txt").read_text() == "alt"


def test_find_replace_says_so_when_nothing_matches(space: Workspace) -> None:
    (space.working_dir / "a.py").write_text("nichts")

    assert "appears in no file" in edit.find_replace(space, "alt", "neu")


def test_which_finds_a_command_that_exists(space: Workspace) -> None:
    out = run.which(space, "sh")

    assert "is not on the PATH" not in out
    assert out.startswith("sh: /")


def test_which_says_so_when_a_command_is_absent(space: Workspace) -> None:
    assert "not on the PATH" in run.which(space, "gibtesnichtxyz")


def test_ps_lists_this_process(space: Workspace) -> None:
    out = system.ps(space, "python")

    assert "PID" in out
    assert "NAME" in out


def test_ps_says_so_when_nothing_matches(space: Workspace) -> None:
    assert "no process matches" in system.ps(space, "gibtesnichtxyz")


def test_sysinfo_reports_every_line(space: Workspace) -> None:
    out = system.sysinfo(space)

    for label in ("system:", "cpu:", "memory:", "disk:", "uptime:", "load:"):
        assert label in out


def test_port_check_answers_for_a_free_port(space: Workspace) -> None:
    out = system.port_check(space, 65000)

    assert "65000" in out


def test_disk_usage_reports_the_filesystem_and_subdirectories(
    space: Workspace,
) -> None:
    big = space.working_dir / "big"
    big.mkdir()
    (big / "data").write_text("x" * 5000)
    (space.working_dir / "small").mkdir()

    out = system.disk_usage(space, ".", 1)

    assert "filesystem at" in out
    assert "big" in out


def test_disk_usage_refuses_a_file(space: Workspace) -> None:
    (space.working_dir / "a").write_text("a")

    with pytest.raises(ToolError):
        system.disk_usage(space, "a")
