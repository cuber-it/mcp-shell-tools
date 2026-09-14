"""Grants: what they change, how long they hold, and the program that writes them."""

from __future__ import annotations

import importlib.util
import os
import stat
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType

import pytest

from mcp_shell_tools import Boundary, GrantError
from mcp_shell_tools.grant import (
    GRANT_FILE,
    GRANT_SCRIPT,
    Grant,
    boundary_in_force,
    hint,
    parse_duration,
    read_grant,
    write_grant,
)

TOOL = Path(__file__).resolve().parents[1] / "tools" / "mcp_shell_grant.py"
SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "grant.sh"
HOME = Path("/home/someone")
BASE = Boundary((HOME,), "guarded", execute=False)


def _load_tool() -> ModuleType:
    """Load the grant program from tools/ as a module."""
    spec = importlib.util.spec_from_file_location("mcp_shell_grant", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def later(seconds: float = 3600) -> float:
    """Return a moment the given seconds from now."""
    return time.time() + seconds


@pytest.mark.parametrize(
    ("text", "seconds"), [("45s", 45), ("30m", 1800), ("2h", 7200), ("1d", 86400)]
)
def test_a_duration_is_read_in_its_unit(text: str, seconds: int) -> None:
    assert parse_duration(text) == seconds


@pytest.mark.parametrize("text", ["", "2", "h", "0h", "2x", "-1h", "1.5h", "2h30m"])
def test_an_unusable_duration_is_refused(text: str) -> None:
    with pytest.raises(GrantError, match="not a duration"):
        parse_duration(text)


def test_a_grant_replaces_the_mode() -> None:
    assert Grant(later(), mode="open").applied(BASE) == Boundary(
        (HOME,), "open", execute=False
    )


def test_a_grant_adds_roots_once() -> None:
    grant = Grant(later(), roots=(Path("/opt"), HOME))

    assert grant.applied(BASE).roots == (HOME, Path("/opt"))


def test_a_grant_does_not_limit_what_had_no_limit() -> None:
    assert Grant(later(), roots=(Path("/opt"),)).applied(Boundary()) == Boundary()


@pytest.mark.parametrize(("execute", "expected"), [(True, True), (False, False)])
def test_a_grant_switches_commands(execute: bool, expected: bool) -> None:
    on = Boundary((HOME,), execute=True)

    assert Grant(later(), execute=execute).applied(BASE).execute is expected
    assert Grant(later(), execute=execute).applied(on).execute is expected


def test_a_grant_without_a_word_on_commands_leaves_them() -> None:
    assert Grant(later(), mode="open").applied(BASE).execute is False


def test_without_a_state_directory_the_configured_boundary_holds() -> None:
    assert boundary_in_force(BASE, None) == BASE


def test_without_a_grant_file_the_configured_boundary_holds(tmp_path: Path) -> None:
    assert boundary_in_force(BASE, tmp_path) == BASE


def test_a_written_grant_is_in_force(tmp_path: Path) -> None:
    write_grant(tmp_path, Grant(later(), mode="open", execute=True))

    assert boundary_in_force(BASE, tmp_path) == Boundary((HOME,), "open", True)


def test_a_lapsed_grant_leaves_the_configured_boundary(tmp_path: Path) -> None:
    write_grant(tmp_path, Grant(time.time() - 1, mode="open"))

    assert boundary_in_force(BASE, tmp_path) == BASE


def test_a_rewritten_grant_is_read_again(tmp_path: Path) -> None:
    write_grant(tmp_path, Grant(later(), mode="open"))
    boundary_in_force(BASE, tmp_path)

    write_grant(tmp_path, Grant(later(7200), mode="strict", roots=(Path("/opt"),)))

    assert boundary_in_force(BASE, tmp_path).mode == "strict"


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "[]",
        '{"mode": "open"}',
        '{"until": "soon"}',
        '{"until": 1e12, "mode": "loose"}',
        '{"until": 1e12, "execute": "yes"}',
        '{"until": 1e12, "execute": 1}',
        '{"until": 1e12, "roots": ["relative"]}',
        '{"until": 1e12, "roots": [7]}',
    ],
)
def test_an_unusable_grant_file_stops_every_check(tmp_path: Path, content: str) -> None:
    (tmp_path / GRANT_FILE).write_text(content, encoding="utf-8")

    with pytest.raises(GrantError, match="reset"):
        boundary_in_force(BASE, tmp_path)


def test_the_grant_file_is_for_its_owner_only(tmp_path: Path) -> None:
    where = write_grant(tmp_path, Grant(later(), mode="open"))

    assert stat.S_IMODE(where.stat().st_mode) == 0o600


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes into read-only directories")
def test_a_failed_write_keeps_the_previous_grant(tmp_path: Path) -> None:
    write_grant(tmp_path, Grant(later(), mode="open"))
    tmp_path.chmod(0o500)
    try:
        with pytest.raises(GrantError, match="previous grant stays"):
            write_grant(tmp_path, Grant(later(), mode="strict"))
        remaining = read_grant(tmp_path)
    finally:
        tmp_path.chmod(0o700)

    assert remaining is not None
    assert remaining.mode == "open"


def test_the_hint_names_the_script_and_the_change(tmp_path: Path) -> None:
    text = hint(tmp_path, "--exec")

    assert f"with: {SCRIPT} --state-dir {tmp_path} set --exec --for 1h" in text


def test_the_hint_points_at_the_wrapper_script() -> None:
    assert GRANT_SCRIPT == SCRIPT
    assert GRANT_SCRIPT.is_file()


def test_without_a_state_directory_the_hint_says_what_is_missing() -> None:
    assert "--state-dir" in hint(None, "--exec")


def test_the_program_runs_from_the_command_line(tmp_path: Path) -> None:
    finished = subprocess.run(
        [sys.executable, str(TOOL), "--state-dir", str(tmp_path), "show"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert finished.returncode == 0
    assert f"no grant in {tmp_path}" in finished.stdout


def test_the_wrapper_script_runs_the_program_from_anywhere(tmp_path: Path) -> None:
    link = tmp_path / "grant"
    link.symlink_to(SCRIPT)

    finished = subprocess.run(
        [str(link), "--state-dir", str(tmp_path), "set", "--exec", "--for", "1h"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    grant = read_grant(tmp_path)
    assert finished.returncode == 0, finished.stderr
    assert grant is not None
    assert grant.execute is True


def test_the_wrapper_script_without_a_venv_says_how_to_make_one(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    copy = tmp_path / "scripts" / "grant.sh"
    copy.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    copy.chmod(0o755)

    finished = subprocess.run(
        [str(copy), "show"], capture_output=True, text=True, check=False
    )

    assert finished.returncode == 2
    assert "python3 -m venv .venv" in finished.stderr


def test_set_writes_a_grant_that_is_in_force(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    extra = tmp_path / "extra"
    argv = ["--state-dir", str(tmp_path), "set", "--mode", "open"]

    code = tool.main([*argv, "--root", str(extra), "--exec", "--for", "2h"])

    grant = read_grant(tmp_path)
    assert code == 0
    assert "mode open" in capsys.readouterr().out
    assert grant is not None
    assert (grant.mode, grant.roots, grant.execute) == ("open", (extra,), True)
    assert 7100 < grant.until - time.time() <= 7200


def test_set_can_switch_commands_off(tmp_path: Path) -> None:
    tool.main(["--state-dir", str(tmp_path), "set", "--no-exec", "--for", "1h"])

    grant = read_grant(tmp_path)
    assert grant is not None
    assert grant.execute is False


def test_set_without_a_change_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = tool.main(["--state-dir", str(tmp_path), "set", "--for", "1h"])

    assert code == tool.REFUSED
    assert "has to change something" in capsys.readouterr().err
    assert read_grant(tmp_path) is None


def test_set_without_a_duration_is_refused(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        tool.main(["--state-dir", str(tmp_path), "set", "--exec"])

    assert read_grant(tmp_path) is None


def test_set_with_an_unusable_duration_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = ["--state-dir", str(tmp_path), "set", "--exec", "--for", "forever"]

    assert tool.main(argv) == tool.REFUSED
    assert "not a duration" in capsys.readouterr().err
    assert read_grant(tmp_path) is None


def test_show_reports_the_grant_and_when_it_lapses(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tool.main(["--state-dir", str(tmp_path), "set", "--exec", "--for", "2h"])
    capsys.readouterr()

    assert tool.main(["--state-dir", str(tmp_path), "show"]) == 0
    shown = capsys.readouterr().out
    assert "commands on" in shown
    assert "lapses in 1h 59m" in shown


def test_show_of_a_lapsed_grant_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_grant(tmp_path, Grant(time.time() - 1, execute=True))

    tool.main(["--state-dir", str(tmp_path), "show"])

    assert "has lapsed" in capsys.readouterr().out


def test_show_without_a_grant_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert tool.main(["--state-dir", str(tmp_path), "show"]) == 0
    assert "no grant" in capsys.readouterr().out


def test_show_of_an_unusable_grant_file_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / GRANT_FILE).write_text("not json", encoding="utf-8")

    assert tool.main(["--state-dir", str(tmp_path), "show"]) == tool.REFUSED
    assert "cannot be used" in capsys.readouterr().err


def test_reset_removes_the_grant(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tool.main(["--state-dir", str(tmp_path), "set", "--exec", "--for", "1h"])

    assert tool.main(["--state-dir", str(tmp_path), "reset"]) == 0
    assert "removed" in capsys.readouterr().out
    assert read_grant(tmp_path) is None


def test_reset_without_a_grant_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert tool.main(["--state-dir", str(tmp_path), "reset"]) == 0
    assert "no grant" in capsys.readouterr().out
