"""Behaviour of the tools that look at the machine.

What ps or sysinfo report depends on the machine, so these tests pin what must
always be true instead of a value that cannot be known here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_shell_tools import ToolError, Workspace, system


def test_ps_lists_this_process(space: Workspace) -> None:
    rows = system.ps(space, "python").splitlines()

    assert rows[0].split() == ["PID", "USER", "MEMORY", "NAME"]
    assert len(rows) > 1


def test_ps_says_so_when_nothing_matches(space: Workspace) -> None:
    assert "no process matches" in system.ps(space, "no-such-process-xyz")


def test_ps_has_no_column_it_cannot_measure(space: Workspace) -> None:
    assert "CPU" not in system.ps(space).splitlines()[0]


def test_sysinfo_claims_no_cpu_share_it_cannot_measure(space: Workspace) -> None:
    lines = system.sysinfo(space).splitlines()

    assert "%" not in next(line for line in lines if line.startswith("cpu:"))


def test_sysinfo_reports_every_line(space: Workspace) -> None:
    out = system.sysinfo(space)

    for label in ("system:", "cpu:", "memory:", "disk:", "uptime:", "load:"):
        assert label in out


def test_port_check_answers_for_a_free_port(space: Workspace) -> None:
    assert "65000" in system.port_check(space, 65000)


def test_disk_usage_reports_the_filesystem_and_subdirectories(
    space: Workspace, tmp_path: Path
) -> None:
    (tmp_path / "big").mkdir()
    (tmp_path / "big/data").write_text("x" * 5000, encoding="utf-8")
    (tmp_path / "small").mkdir()

    out = system.disk_usage(space, ".", 1)

    assert out.startswith("filesystem at")
    assert "big" in out


def test_disk_usage_counts_each_file_once_per_ancestor(
    space: Workspace, tmp_path: Path
) -> None:
    (tmp_path / "d1/d2").mkdir(parents=True)
    (tmp_path / "d1/d2/f").write_text("x" * 3000, encoding="utf-8")

    rows = system.disk_usage(space, ".", 2).splitlines()
    measured = {row.split()[-1]: row.split()[0] for row in rows if "d1" in row}

    assert measured["d1"] == measured["d1/d2"] == "2.9K"


def test_disk_usage_refuses_a_file(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "a").write_text("a", encoding="utf-8")

    with pytest.raises(ToolError):
        system.disk_usage(space, "a")
