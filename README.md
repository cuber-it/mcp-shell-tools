# mcp-shell-tools

**Version 8.0 — completely rewritten and revised.**

Workstation tools for AI assistants: files, editing, searching, shell commands,
notes, sessions and a look at the machine. Thirty-three tools, usable as a
Python library or served over the Model Context Protocol.

- **Library**: plain functions grouped by subject, no dependency beyond
  `psutil`, nothing about MCP.
- **Server**: the same tools over stdio or streamable HTTP with the MCP SDK,
  protocol revision 2026-07-28, OAuth for HTTP.
- **Boundary**: reading reaches the whole system, writing stays inside allowed
  roots, shell commands are off. A person on the host widens or narrows that
  for a limited time with a grant.

## Installation

Python 3.12 or later.

```bash
pip install mcp-shell-tools            # the library
pip install "mcp-shell-tools[server]"  # and the MCP server
```

## Quick start

A client that starts the server itself, over stdio:

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

Over HTTP, with OAuth:

```bash
MCP_OAUTH_ENABLED=true \
MCP_OAUTH_SERVER_URL=https://auth.example.org/ \
MCP_PUBLIC_URL=https://mcp.example.org/ \
mcp-shell-tools --transport streamable-http --host 0.0.0.0 --port 12204 --path /shell
```

As a library:

```python
from pathlib import Path

from mcp_shell_tools import Workspace, files, find

space = Workspace(working_dir=Path.cwd())
print(files.file_read(space, "README.md"))
print(find.grep(space, "def main", glob="**/*.py"))
```

## What the server allows by default

Reading goes anywhere. Writing, deleting and moving stay below the home
directory. Shell commands do not run. A refusal says which grant lifts it:

```text
outside the allowed roots for write: /etc/example.conf; a person on the host
can allow it with: /path/to/mcp-shell-tools/scripts/grant.sh
--state-dir /home/you/.mcp-shell-tools set --root /etc --for 1h
```

Deleted entries go to a trash in the state directory, not away for good.

## Documentation

- [Running the server](https://github.com/cuber-it/mcp-shell-tools/blob/master/doc/server.md):
  options, environment, authentication, reverse proxy, systemd
- [Boundary and grants](https://github.com/cuber-it/mcp-shell-tools/blob/master/doc/boundary.md):
  modes, commands, grants
- [Tool reference](https://github.com/cuber-it/mcp-shell-tools/blob/master/doc/tools.md):
  all 33 tools with their parameters
- [Using the library](https://github.com/cuber-it/mcp-shell-tools/blob/master/doc/library.md):
  workspace, errors, serving the catalogue from a server of your own
- [Development](https://github.com/cuber-it/mcp-shell-tools/blob/master/doc/development.md):
  setup, checks, layout
- [Changes](https://github.com/cuber-it/mcp-shell-tools/blob/master/CHANGES.md)

## License

MIT, see [LICENSE](https://github.com/cuber-it/mcp-shell-tools/blob/master/LICENSE).
