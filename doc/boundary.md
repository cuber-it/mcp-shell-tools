# Boundary and grants

The boundary decides how far the tools reach. It is checked for every path a
tool resolves and for every hit a search pattern turns up, so a `..` in a
pattern or a symlink pointing elsewhere does not get past it.

## Roots, mode and commands

A boundary has three parts.

**Roots** are the directories the tools are confined to. Without roots there is
no limit. The server uses the home directory unless `--allowed-root` names
others.

**The mode** decides what the roots confine:

| Mode | Reading | Writing, deleting, moving |
|---|---|---|
| `open` | anywhere | anywhere |
| `guarded` (default) | anywhere | inside the roots |
| `strict` | inside the roots | inside the roots |

**Commands** are a switch of their own. A shell command reaches past every path
check, so no mode can confine it. The server starts with commands off;
`--exec` switches them on for good, a grant for a while.

As long as commands run, the boundary guards against a slip, not against
intent.

## What each tool needs

| Access | Tools |
|---|---|
| reading | `file_read`, `file_list`, `tree`, `file_info`, `head`, `tail`, `diff_preview`, `glob_search`, `grep`, `cd`, `project_context`, `disk_usage`, `find_replace` without `apply` |
| writing | `file_write`, `file_append`, `str_replace`, the destination of `file_copy` |
| destroying | `file_delete`, both ends of `file_move`, every file `find_replace` changes with `apply` |
| commands | `exec` |
| none | `env`, `set_env`, `which`, `ps`, `sysinfo`, `port_check`, `cwd`, `memory_*`, `session_*` |

Sessions and the trash live in the state directory, which the server manages
itself. `session_resume` restores a working directory only if reading may reach
it.

## Refusals

A refused path raises `OutsideBoundaryError`, a switched-off command
`NotPermittedError`. Both messages end with the grant that would lift them:

```text
shell commands are switched off; a person on the host can allow it with:
/path/to/mcp-shell-tools/scripts/grant.sh --state-dir /home/you/.mcp-shell-tools
set --exec --for 1h
```

The suggested root is the refused path if it is a directory, otherwise the
directory it lies in. The suggested duration is always one hour.

## Grants

A grant widens or narrows the boundary of a running server for a limited time.
It takes effect at the next tool call and lapses on its own; the server does not
restart.

```bash
scripts/grant.sh set --root /opt/data --for 2h   # writing reaches /opt/data too
scripts/grant.sh set --exec --for 30m            # commands run
scripts/grant.sh set --mode open --for 15m       # no confinement at all
scripts/grant.sh set --mode strict --for 1d      # reading confined as well
scripts/grant.sh set --no-exec --for 1d          # commands off, even with --exec
scripts/grant.sh show
scripts/grant.sh reset
```

| Option | Effect |
|---|---|
| `--for` | required; a number with `s`, `m`, `h` or `d`, for instance `30m` |
| `--root PATH` | adds a root; repeatable. Without configured roots there is no limit, and a grant adds none |
| `--mode` | replaces the configured mode |
| `--exec`, `--no-exec` | switch commands on or off |
| `--state-dir` | state directory of the server, `~/.mcp-shell-tools` unless given |

A grant has to change something. A new grant replaces the previous one. Lasting
changes belong in the server's own options.

`scripts/grant.sh` finds the repository from its own location, also through a
symlink, and runs `tools/mcp_shell_grant.py` with the interpreter of the
repository's `.venv`.

## The grant file

The grant is `grant.json` in the state directory, readable by its owner only:

```json
{
  "until": 1789000000.0,
  "mode": "open",
  "roots": ["/opt/data"],
  "execute": true
}
```

`until` is a Unix time. `mode` and `execute` may be `null`, meaning unchanged.
`roots` must be absolute.

- The file is written to a temporary name and renamed, so the server sees the
  old grant or the new one, never half of either.
- The tools cannot change the file. Writing is refused for the file and its
  directory; deleting or moving is refused for the file and every directory
  above it.
- A grant file that cannot be read or does not hold a valid grant makes every
  check fail with `GrantError` until it is fixed or removed with
  `scripts/grant.sh reset`. Ignoring it could lift a restriction it imposes.
- Without a state directory there are no grants, and refusals say so.
