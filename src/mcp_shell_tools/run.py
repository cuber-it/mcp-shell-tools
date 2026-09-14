"""Running commands and looking at the environment they run in."""

from __future__ import annotations

import os
import shutil
import subprocess

from mcp_shell_tools.workspace import ToolError, Workspace


def shell_exec(space: Workspace, command: str, timeout: float = 0) -> str:
    """Run a shell command in the working directory and return its output.

    Standard output and standard error come back together, because a caller
    reading a failure needs both. The exit status is named when it is not
    zero: a command that failed must not look like one that said nothing.

    Returns:
        The output, with the exit status if it was not zero.

    Raises:
        ToolError: The command did not finish in time, or could not be
            started at all.
    """
    limit = timeout if timeout > 0 else space.timeout
    try:
        finished = subprocess.run(
            command,
            shell=True,
            cwd=space.working_dir,
            capture_output=True,
            text=True,
            timeout=limit,
            check=False,
        )
    except subprocess.TimeoutExpired as err:
        raise ToolError(f"command did not finish within {limit:g}s: {command}") from err
    except OSError as err:
        raise ToolError(f"could not run the command: {err}") from err

    output = finished.stdout + finished.stderr
    if finished.returncode != 0:
        output = f"{output}\n[exit status {finished.returncode}]"
    return space.cut(output) if output.strip() else "[no output]"


def which(space: Workspace, name: str) -> str:
    """Report where a command is found, following the current PATH.

    Returns:
        The full path, or a line saying it is not on the PATH.
    """
    del space
    found = shutil.which(name, path=os.environ.get("PATH"))
    if not found:
        return f"{name} is not on the PATH"
    return f"{name}: {found}"


def env(space: Workspace, name: str = "") -> str:
    """Show the environment the commands run in.

    Returns:
        One ``NAME=value`` per line, or the single value.

    Raises:
        ToolError: The named variable is not set.
    """
    if name:
        value = os.environ.get(name)
        if value is None:
            raise ToolError(f"not set: {name}")
        return f"{name}={value}"
    rows = [f"{key}={value}" for key, value in sorted(os.environ.items())]
    return space.cut("\n".join(rows))


def set_env(space: Workspace, name: str, value: str) -> str:
    """Set an environment variable for the commands that follow.

    It holds as long as this process runs and is gone afterwards, because the
    environment belongs to the process, not to a file.

    Raises:
        ToolError: The name is empty or not usable as a variable name.
    """
    del space
    if not name or "=" in name or name[0].isdigit():
        raise ToolError(f"not a usable variable name: {name!r}")
    os.environ[name] = value
    return f"{name}={value}"
