# mcp-shell-tools

Workstation tools: files, editing, searching, running commands, notes that
survive a restart, and a look at the machine.

Thirty-three functions, grouped by subject, with no dependency beyond `psutil`.
They know nothing about MCP or any other protocol — a server is one caller
among others.

## Installation

```bash
pip install mcp-shell-tools            # the tools
pip install "mcp-shell-tools[server]"  # and the MCP server
```

## As an MCP server

```bash
mcp-shell-tools                                          # stdio
mcp-shell-tools --transport streamable-http --port 12204
```

In a client that starts the server itself:

```json
{
  "mcpServers": {
    "shell": {
      "command": "mcp-shell-tools",
      "args": ["--working-dir", "/home/you/projects"]
    }
  }
}
```

`--allowed-root` confines the tools to a directory and may be repeated;
without it they may touch the whole disk. `--path` moves the HTTP endpoint off
`/mcp`.

The server speaks protocol revision 2026-07-28, where a request carries its own
version and capabilities and there is no `initialize` handshake. The SDK still
answers the older handshake for clients that need it.

Only `server.py` imports the SDK. `registry.py` publishes the tools on
anything whose `tool()` returns a decorator, so a proxy or a server of your own
can hand it its own registrar:

```python
from mcp_shell_tools import Workspace
from mcp_shell_tools.registry import register

register(your_server, Workspace(working_dir=Path.cwd()))
```

One thing to take over with it: the SDK decides by exception class whether a
failure was anticipated. Its own `ToolError` reaches the caller with its
message; anything else is a crash, and the caller learns only that some tool
failed. The tools raise `mcp_shell_tools.ToolError`, so a server of your own
should catch it and re-raise it as whatever its protocol layer calls an
anticipated failure — otherwise "no such file" arrives as a blank error.
`server.py` does this in `_Anticipated`.

## Use

Every tool takes the workspace it acts on as its first argument. The workspace
holds the working directory, the limits and the notes, so the caller owns that
state and nothing hides in a module global.

```python
from pathlib import Path

from mcp_shell_tools import Workspace, files, find, run

space = Workspace(working_dir=Path.cwd())

print(files.file_read(space, "README.md"))
print(find.grep(space, "def resolve", glob="**/*.py"))
print(run.shell_exec(space, "git status --short"))
```

A tool that will not do what it was asked raises `ToolError` with a sentence
saying why. `OutsideBoundaryError` is the one case worth catching separately:
the path was outside `allowed_roots`.

```python
from mcp_shell_tools import ToolError

try:
    files.file_read(space, "nowhere.txt")
except ToolError as err:
    print(err)          # no such file: /home/you/nowhere.txt
```

## The workspace

```python
Workspace(
    working_dir=Path("/home/you/projects"),
    allowed_roots=(),      # empty means the tools may touch the whole disk
    timeout=120.0,         # seconds a command may run
    max_output=200_000,    # characters of output kept
    max_results=200,       # rows a listing or search returns
    state_dir=None,        # where sessions are written
)
```

`allowed_roots` confines every path the tools resolve. Left empty there is no
limit, which is what a workstation tool set is for; set it when the tools are
reachable by someone who should not have the whole disk.

`workspace_from(mapping)` builds the same thing from a configuration dict, for
a caller that reads its settings from a file.

## What there is

| Module | Tools |
|---|---|
| `files` | `file_read`, `file_write`, `file_append`, `file_list`, `file_delete`, `file_move`, `file_copy`, `tree`, `file_info`, `head`, `tail` |
| `edit` | `str_replace`, `diff_preview`, `find_replace` |
| `find` | `glob_search`, `grep` |
| `run` | `shell_exec`, `which`, `env`, `set_env` |
| `place` | `cwd`, `cd`, `project_context` |
| `notes` | `memory_add`, `memory_show`, `memory_clear`, `session_save`, `session_resume`, `session_list` |
| `system` | `ps`, `sysinfo`, `port_check`, `disk_usage` |

`file_write` earns its place next to `shell_exec`: a heredoc inside a long
command line is where quoting goes wrong, and writing a file is too common to
leave to that.

`str_replace` insists on exactly one match. No match means the caller is
looking at a different file than they think; several matches mean the change
is ambiguous. Both are refused rather than guessed.

`find_replace` does nothing until `apply` is true, and it never descends into
`.git`, `.venv`, `node_modules` or `__pycache__`.

`ps` reports memory, not a CPU share. A share is a measurement over a span of
time, and a single listing has no span to measure over.

Notes live in the workspace and end with the process. Sessions are written to
`state_dir` and outlive it. That is the whole difference between `memory_*`
and `session_*`.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
ruff check src tests
pylint src tests
pytest
```
