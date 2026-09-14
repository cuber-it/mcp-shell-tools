"""Behaviour of the tools that run commands and read the environment."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_shell_tools import ToolError, Workspace, run


def test_a_command_returns_its_output(space: Workspace) -> None:
    assert run.shell_exec(space, "echo hello") == "hello\n"


def test_a_command_runs_in_the_working_directory(
    space: Workspace, tmp_path: Path
) -> None:
    assert run.shell_exec(space, "pwd").strip() == str(tmp_path)


def test_a_failing_command_names_its_status(space: Workspace) -> None:
    assert "exit status 3" in run.shell_exec(space, "exit 3")


def test_a_command_without_output_says_so(space: Workspace) -> None:
    assert run.shell_exec(space, "true") == "[no output]"


def test_error_output_comes_back_too(space: Workspace) -> None:
    assert "trouble" in run.shell_exec(space, "echo trouble >&2")


def test_a_command_that_hangs_is_stopped(space: Workspace) -> None:
    with pytest.raises(ToolError, match="did not finish"):
        run.shell_exec(space, "sleep 5", timeout=0.2)


def test_long_output_is_cut(tmp_path: Path) -> None:
    space = Workspace(working_dir=tmp_path, max_output=10)

    assert "more characters" in run.shell_exec(space, "seq 1 100")


def test_the_environment_can_be_read(
    space: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MCP_SHELL_PROBE", "value")

    assert run.env(space, "MCP_SHELL_PROBE") == "MCP_SHELL_PROBE=value"


def test_an_unset_variable_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError):
        run.env(space, "MCP_SHELL_DEFINITELY_UNSET")


@pytest.mark.parametrize("name", ["", "not=usable", "1digit"])
def test_a_broken_variable_name_is_refused(space: Workspace, name: str) -> None:
    with pytest.raises(ToolError):
        run.set_env(space, name, "x")


def test_a_set_variable_reaches_the_command(
    space: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("MCP_SHELL_PROBE2", raising=False)

    run.set_env(space, "MCP_SHELL_PROBE2", "reached")

    assert run.shell_exec(space, "echo $MCP_SHELL_PROBE2") == "reached\n"


def test_which_finds_a_command_that_exists(space: Workspace) -> None:
    assert run.which(space, "sh").startswith("sh: /")


def test_which_says_so_when_a_command_is_absent(space: Workspace) -> None:
    assert "not on the PATH" in run.which(space, "no-such-command-xyz")
