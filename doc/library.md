# Using the library

The tools are plain functions in `mcp_shell_tools`, one module per subject. None
of them imports the MCP SDK; `pip install mcp-shell-tools` without `[server]`
is enough.

| Module | Functions |
|---|---|
| `files` | `file_read`, `file_write`, `file_append`, `file_list`, `file_delete`, `file_move`, `file_copy`, `tree`, `file_info`, `head`, `tail` |
| `edit` | `str_replace`, `diff_preview`, `find_replace` |
| `find` | `glob_search`, `grep` |
| `run` | `shell_exec`, `which`, `env`, `set_env` |
| `place` | `cwd`, `cd`, `project_context` |
| `notes` | `memory_add`, `memory_show`, `memory_clear`, `session_save`, `session_resume`, `session_list` |
| `system` | `ps`, `sysinfo`, `port_check`, `disk_usage` |

The parameters are those of the [tool reference](tools.md), with the workspace
in front. `run.shell_exec` is published as `exec`.

## The workspace

Every function takes the workspace it acts on as its first argument. The caller
owns that state; nothing hides in a module global.

```python
from pathlib import Path

from mcp_shell_tools import Boundary, Workspace, edit, run

space = Workspace(
    working_dir=Path("/home/you/project"),
    boundary=Boundary(roots=(Path("/home/you"),), mode="guarded", execute=True),
    timeout=120.0,  # seconds a command may run
    max_output=200_000,  # characters kept before output is cut
    max_results=200,  # rows a listing or search returns
    state_dir=Path("/home/you/.mcp-shell-tools"),  # sessions, trash, grant
)

print(edit.find_replace(space, "old_name", "new_name", glob="*.py"))
print(run.shell_exec(space, "git status --short"))
```

`Workspace(working_dir=...)` alone has no roots, runs commands and has no state
directory: no limit, and no trash, sessions or grants. The server starts
stricter, see [server options](server.md#options).

`workspace_from(mapping)` builds a workspace from configuration:

| Key | Default |
|---|---|
| `working_dir` | current directory |
| `allowed_roots` | none |
| `mode` | `guarded` |
| `execute` | `true` |
| `timeout` | `120` |
| `max_output` | `200000` |
| `max_results` | `200` |
| `state_dir` | none |

`space.current()` returns the boundary in force, that is the configured one as
a grant changes it.

## Errors

A function that will not do what it was asked raises an exception with a
sentence saying why. Anything else escaping a function is a bug.

| Exception | Meaning |
|---|---|
| `ToolError` | the base of every refusal: no such file, ambiguous passage, unusable pattern |
| `OutsideBoundaryError` | the boundary does not let this access reach the path |
| `NotPermittedError` | the action is not permitted at all, such as a command while commands are off |
| `GrantError` | the grant file cannot be used; every check fails until it is fixed |

```python
from mcp_shell_tools import ToolError, files

try:
    files.file_read(space, "nowhere.txt")
except ToolError as err:
    print(err)  # no such file: /home/you/project/nowhere.txt
```

## Grants from code

`mcp_shell_tools.grant` reads and writes grant files; `scripts/grant.sh` is
built on it.

```python
import time

from mcp_shell_tools.grant import Grant, read_grant, remove_grant, write_grant

state = Path("/home/you/.mcp-shell-tools")
write_grant(state, Grant(until=time.time() + 3600, execute=True))
print(read_grant(state))
remove_grant(state)
```

## Serving the tools from a server of your own

`mcp_shell_tools.server.registry.catalogue(space)` returns every tool bound to
one workspace, by the name it is published under. The catalogue imports no SDK.
Each function's docstring is its description, with an English paragraph, a
German paragraph and a line of German search words, and its signature is the
input schema.

```python
from mcp_shell_tools.server.registry import catalogue

for name, tool in catalogue(space).items():
    your_server.add_tool(tool, name=name)
```

The MCP SDK passes the message of its own `ToolError` to the caller and reduces
every other exception to `Error executing tool <name>`. Translate
`mcp_shell_tools.ToolError` into your server's anticipated error, or the reason
of a refusal is lost. `src/mcp_shell_tools/server/app.py` does this in
`_anticipated`.

Names carry no prefix. If several servers end up in one client catalogue, give
them one when registering.
