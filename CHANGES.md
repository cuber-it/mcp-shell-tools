# Changes

## 37df37a

- Refusals and the message for an unusable grant file name the absolute path of
  `scripts/grant.sh` instead of the interpreter and `tools/mcp_shell_grant.py`
- Server instructions and README point to `scripts/grant.sh`

## 2d8686b

- `scripts/grant.sh` runs `tools/mcp_shell_grant.py` with the repository's
  venv interpreter, from anywhere and through symlinks; without a venv it says
  how to create one

## 9383871

- The grant program is `tools/mcp_shell_grant.py`, no longer an entry point
  of the package; the library keeps only what the server needs to read grants
- Refusals name the full call: interpreter, program path, state directory

## 97dc6b1

- `guarded` now confines writing as well as deleting and moving; reading stays
  free
- Shell commands are a switch of their own (`execute`), apart from the mode
- `mcp-shell-grant set|show|reset` raises or lowers the boundary of a running
  server for a required duration, through `grant.json` in the state directory
- The tools cannot change the grant file; an unusable grant file refuses every
  check
- A refusal names the `mcp-shell-grant` command that would lift it
- Server defaults: root is the home directory, commands off (`--exec` switches
  them on), state directory `~/.mcp-shell-tools`
- Tool descriptions carry an English and a German paragraph and search words;
  the server instructions are bilingual

## fafef45

- HTTP server as OAuth resource server, configured through `MCP_OAUTH_ENABLED`,
  `MCP_OAUTH_SERVER_URL`, `MCP_PUBLIC_URL` and `MCP_AUTH_METHOD`
- Token checks exchangeable: `server/auth.py` holds them without the SDK;
  `introspection` (RFC 7662, five-minute memory) is the first
- Resource is the public URL plus the endpoint path; scope `user` required
- Refuses to listen beyond this machine without authentication
- HTTP is sessionless; `--host` and `--port` default to `MCP_HOST` and
  `MCP_PORT`
- The SDK is imported at the top of `server/app.py`; the lazy import with its
  own error message is gone

## dfac9ae

- Boundary in its own module: roots, mode and kind of access decide
- Modes `open`, `guarded` (default) and `strict`; guarded confines deleting,
  moving and `find_replace` with `apply` to the roots, strict also reading,
  writing and commands
- `file_delete` moves into `trash` under `state_dir` instead of removing
- Server option `--mode`; the legacy SSE transport is gone

## 9147a90

- Library split into errors, workspace, output and the tool modules
- Server split into a neutral catalogue (`server/registry.py`) and the SDK
  binding (`server/app.py`)
- Boundary checks in one place; search hits and symlinks no longer escape
  `allowed_roots`
- `tree` skips `.git` and `.venv`; the skip check looks only below the search
  root
- `session_resume` checks before it restores; `find_replace` reports the limit
  and partial writes
- Unusable glob patterns and unreadable files are refused in words

## 6.0.0 (585e98d)

- Complete restart with a new history, to make better use of the new MCP SDK
  (`mcp` 2.x, protocol revision 2026-07-28).
