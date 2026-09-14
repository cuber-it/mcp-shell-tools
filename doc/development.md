# Development

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Checks

All of them have to pass before a change is committed.

```bash
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/python -m pylint src tests tools
.venv/bin/python -m pytest
shellcheck scripts/grant.sh
```

The limits are those in `pyproject.toml`: line length 88, cyclomatic complexity
10, and pylint's design checks. What a linter reports is taken apart, not
silenced.

The tests need no network beyond the loopback interface. A few start the server
or the grant program as a subprocess; the authentication tests run the server
against a stand-in authorization server in `tests/loopback.py`.

## Layout

```text
src/mcp_shell_tools/
  __init__.py        public names of the library
  errors.py          ToolError and its subclasses
  boundary.py        roots, mode, commands: what may be reached
  grant.py           reading and writing grants
  workspace.py       the shared state; every path check happens here
  output.py          reading text, cutting and rendering output
  files.py edit.py find.py run.py place.py notes.py system.py
  server/
    registry.py      the tools as a catalogue, no SDK
    auth.py          token checks and their configuration, no SDK
    app.py           the MCP server, the only module importing the SDK
tools/
  mcp_shell_grant.py the grant program
scripts/
  grant.sh           runs the grant program with the repository's venv
tests/
doc/
```

## Rules the code keeps

- **One module imports the SDK.** Only `server/app.py` imports `mcp`; Ruff
  refuses it anywhere else, and a test makes sure the library and the catalogue
  load without it. When the SDK changes, the change is felt in one place.
- **Every path check happens in `workspace.py`.** A tool names the access it
  needs and never checks a path itself, so the boundary can be replaced by
  another policy without touching the tools.
- **Refusals are `ToolError`s.** A tool that will not do what it was asked
  raises a subclass with a sentence for the caller; the server passes exactly
  those on.
- **The docstring of a catalogue entry is the description a client reads.** It
  has an English paragraph, a German paragraph and a line starting with
  `Stichworte:`; a test holds every tool to that.
- **The documentation keeps up.** Tests check that every tool has its section in
  [tools.md](tools.md) and every server option and environment variable
  appears in [server.md](server.md).
