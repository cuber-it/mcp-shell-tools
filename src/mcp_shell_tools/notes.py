"""Notes and saved sessions.

Notes live in the workspace and are gone when the process ends — they are a
scratchpad for one stretch of work. Sessions are written to disk, so they
outlive the process; that is the whole difference between the two.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcp_shell_tools.workspace import ToolError, Workspace

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
    return space.cut("\n".join(space.notes))


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
    besides that is not restored, because it was never saved.

    Raises:
        ToolError: There is no such session, or it cannot be read.
    """
    target = _session_file(space, name)
    payload = _read_session(target)
    space.notes = list(payload.get("notes", []))
    saved_dir = payload.get("working_dir")
    if isinstance(saved_dir, str):
        # Through resolve, so a session file cannot move the workspace out of
        # allowed_roots.
        restored = space.resolve(saved_dir)
        if restored.is_dir():
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
    directory = _state_dir(space)
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


def _state_dir(space: Workspace) -> Path:
    """Return where sessions are written.

    Raises:
        ToolError: No directory is configured.
    """
    if space.state_dir is None:
        raise ToolError("no state_dir configured, sessions cannot be saved")
    return space.state_dir


def _session_file(space: Workspace, name: str) -> Path:
    """Return the file a session is stored in.

    Raises:
        ToolError: The name would escape the state directory.
    """
    if not name or "/" in name or name.startswith("."):
        raise ToolError(f"not a usable session name: {name!r}")
    return _state_dir(space) / f"{name}{SESSION_SUFFIX}"


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
