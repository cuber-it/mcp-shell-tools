"""Notes and saved sessions.

Notes live in the workspace and end with the process. Sessions are written to
the state directory and outlive it.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcp_shell_tools.errors import ToolError
from mcp_shell_tools.output import cut
from mcp_shell_tools.workspace import Workspace

SESSION_SUFFIX = ".session.json"


def memory_add(space: Workspace, note: str) -> str:
    """Keep a note for the rest of this process's run.

    Raises:
        ToolError: The note is empty.
    """
    if not note.strip():
        raise ToolError("an empty note is not worth keeping")
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
    space.notes.append(f"{stamp}  {note.strip()}")
    return f"noted, {len(space.notes)} in total"


def memory_show(space: Workspace) -> str:
    """Return the notes kept so far, oldest first."""
    if not space.notes:
        return "nothing noted"
    return cut("\n".join(space.notes), space.max_output)


def memory_clear(space: Workspace) -> str:
    """Drop every note and say how many were dropped."""
    dropped = len(space.notes)
    space.notes.clear()
    return f"dropped {dropped} notes"


def session_save(space: Workspace, name: str, summary: str = "") -> str:
    """Write the current notes and working directory to disk.

    Raises:
        ToolError: The name is unusable, no state directory is configured, or
            the file cannot be written.
    """
    target = _session_file(space, name)
    payload = {
        "name": name,
        "saved_at": time.time(),
        "summary": summary,
        "working_dir": str(space.working_dir),
        "notes": list(space.notes),
    }
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as err:
        raise ToolError(f"could not save the session: {err}") from err
    return f"saved session {name} with {len(space.notes)} notes to {target}"


def session_resume(space: Workspace, name: str) -> str:
    """Load a saved session back into the workspace.

    The notes and the working directory are restored. What a caller did
    besides that is not restored, because it was never saved. Everything is
    checked before anything is restored, so a refusal leaves the workspace as
    it was.

    Raises:
        ToolError: There is no such session, it cannot be read, or its
            working directory lies outside the allowed roots.
    """
    payload = _read_session(_session_file(space, name))
    saved_dir = payload.get("working_dir")
    restored = space.resolve(saved_dir) if isinstance(saved_dir, str) else None

    space.notes = list(payload.get("notes", []))
    if restored is not None and restored.is_dir():
        space.working_dir = restored
    summary = payload.get("summary") or "no summary"
    return (
        f"resumed session {name}: {summary}\n"
        f"working directory {space.working_dir}, {len(space.notes)} notes"
    )


def session_list(space: Workspace) -> str:
    """List the saved sessions, most recently saved first.

    Returns:
        One session per line with its summary, or a line saying there are
        none.

    Raises:
        ToolError: No state directory is configured.
    """
    directory = space.state()
    if not directory.is_dir():
        return "no sessions saved"
    rows = []
    for path in directory.glob(f"*{SESSION_SUFFIX}"):
        try:
            payload = _read_session(path)
        except ToolError:
            continue
        rows.append(
            (
                float(payload.get("saved_at", 0)),
                f"{payload.get('name', path.stem)}  "
                f"{payload.get('summary') or 'no summary'}",
            )
        )
    if not rows:
        return "no sessions saved"
    rows.sort(reverse=True)
    return "\n".join(row for _, row in rows[: space.max_results])


def _session_file(space: Workspace, name: str) -> Path:
    """Return the file a session is stored in.

    Raises:
        ToolError: The name would escape the state directory, or no state
            directory is configured.
    """
    if not name or "/" in name or name.startswith("."):
        raise ToolError(f"not a usable session name: {name!r}")
    return space.state() / f"{name}{SESSION_SUFFIX}"


def _read_session(path: Path) -> dict[str, Any]:
    """Read one session file.

    Raises:
        ToolError: It is missing or not a readable session.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise ToolError(f"no such session: {path.name}") from err
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise ToolError(f"could not read {path.name}: {err}") from err
    if not isinstance(payload, dict):
        raise ToolError(f"not a session file: {path.name}")
    return payload
