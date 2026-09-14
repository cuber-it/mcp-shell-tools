# Changes

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
