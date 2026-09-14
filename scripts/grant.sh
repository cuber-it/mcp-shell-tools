#!/usr/bin/env bash
# Raise or lower the boundary of a running mcp-shell-tools server.
#
# Runs mcp_shell_tools.tools.mcp_shell_grant with the interpreter of this
# repository's venv, so it can be called from anywhere, also through a symlink:
#
#   scripts/grant.sh set --root /opt/data --for 2h
#   scripts/grant.sh set --exec --for 30m
#   scripts/grant.sh show
#   scripts/grant.sh reset
#
# Every argument is passed on unchanged; scripts/grant.sh --help lists them.
set -euo pipefail

repo="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
python="$repo/.venv/bin/python"

if [[ ! -x "$python" ]]; then
    echo "grant.sh: no interpreter at $python" >&2
    echo "grant.sh: create it with: python3 -m venv .venv && .venv/bin/pip install -e ." >&2
    exit 2
fi

exec "$python" -m mcp_shell_tools.tools.mcp_shell_grant "$@"
