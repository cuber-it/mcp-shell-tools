"""Looking at the machine: processes, resources, ports, disk usage."""

from __future__ import annotations

import platform
import shutil
from datetime import datetime
from pathlib import Path

import psutil

from mcp_shell_tools.errors import ToolError
from mcp_shell_tools.output import cut, render, size, span
from mcp_shell_tools.workspace import Workspace


def ps(space: Workspace, name: str = "") -> str:
    """List running processes, optionally only those matching a name.

    A process shows its memory, not its CPU share: a share is a measurement
    over a span of time, and a single listing has no span to measure over.

    Returns:
        One line per process: pid, user, memory, name.
    """
    wanted = name.lower()
    rows: list[tuple[int, str]] = []

    for proc in psutil.process_iter(["pid", "name", "username", "memory_info"]):
        try:
            info = proc.info
            label = info["name"] or ""
            if wanted and wanted not in label.lower():
                continue
            memory = info["memory_info"].rss if info["memory_info"] else 0
            rows.append(
                (
                    memory,
                    f"{info['pid']:>7}  {(info['username'] or '-')[:12]:<12} "
                    f"{size(memory):>9}  {label}",
                )
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    empty = f"no process matches '{name}'" if name else "no processes"
    if not rows:
        return empty

    rows.sort(key=lambda row: row[0], reverse=True)
    header = f"{'PID':>7}  {'USER':<12} {'MEMORY':>9}  NAME"
    listing = [header] + [row[1] for row in rows]
    return cut(render(listing, space.max_results + 1, empty), space.max_output)


def sysinfo(space: Workspace) -> str:
    """Report the machine: system, CPU, memory, disk, uptime, load."""
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage(str(space.working_dir))
    booted = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - booted
    load = psutil.getloadavg()

    lines = [
        f"system:   {platform.system()} {platform.release()}",
        f"host:     {platform.node()}",
        f"python:   {platform.python_version()}",
        f"cpu:      {psutil.cpu_count(logical=False) or '?'} cores, "
        f"{psutil.cpu_count()} threads, {psutil.cpu_percent(None):.1f}% busy",
        f"memory:   {size(memory.used)} of {size(memory.total)} "
        f"({memory.percent:.0f}%), {size(memory.available)} available",
        f"swap:     {size(swap.used)} of {size(swap.total)}",
        f"disk:     {size(disk.used)} of {size(disk.total)} "
        f"({disk.percent:.0f}%) at {space.working_dir}",
        f"uptime:   {span(int(uptime.total_seconds()))}, "
        f"booted {booted:%Y-%m-%d %H:%M}",
        f"load:     {load[0]:.2f} {load[1]:.2f} {load[2]:.2f}",
    ]
    return "\n".join(lines)


def port_check(space: Workspace, port: int = 0) -> str:
    """Say what listens on a port, or list everything that listens.

    Returns:
        One line per listening socket: address, port, pid, process.

    Raises:
        ToolError: Listening sockets cannot be read with the current rights.
    """
    try:
        connections = psutil.net_connections(kind="inet")
    except psutil.AccessDenied as err:
        raise ToolError(
            "listening sockets can only be read with sufficient rights"
        ) from err

    rows = []
    for conn in connections:
        if conn.status != psutil.CONN_LISTEN or not conn.laddr:
            continue
        if port and conn.laddr.port != port:
            continue
        rows.append(
            f"{conn.laddr.ip:<28} {conn.laddr.port:>6}  "
            f"{conn.pid or '-':>7}  {_process_name(conn.pid)}"
        )

    empty = f"nothing listens on port {port}" if port else "nothing listens"
    if not rows:
        return empty

    rows.sort()
    header = f"{'ADDRESS':<28} {'PORT':>6}  {'PID':>7}  PROCESS"
    return cut(render([header] + rows, space.max_results + 1, empty), space.max_output)


def disk_usage(space: Workspace, path: str = ".", depth: int = 1) -> str:
    """Report how much space a directory and its subdirectories take.

    Returns:
        The filesystem summary, then the largest entries, biggest first.

    Raises:
        ToolError: The path does not exist or is not a directory.
    """
    target = space.directory(path)
    usage = shutil.disk_usage(target)
    lines = [
        f"filesystem at {target}: {size(usage.used)} used, "
        f"{size(usage.free)} free of {size(usage.total)}",
        "",
    ]

    measured = _measure(target, max(depth, 1))
    rows = [
        f"{size(measured_bytes):>9}  {entry.relative_to(target)}"
        for entry, measured_bytes in sorted(measured.items(), key=lambda it: -it[1])
        if entry != target
    ]
    body = render(rows, space.max_results, "(no subdirectories)")
    return cut("\n".join(lines + [body]), space.max_output)


def _measure(target: Path, depth: int) -> dict[Path, int]:
    """Return the total size of every directory down to the given depth.

    One walk, adding each file's size to every ancestor it belongs to. The
    obvious alternative, measuring each directory on its own, reads the deep
    files once per level above them.

    Returns:
        The size below each directory, the starting one included.
    """
    sizes: dict[Path, int] = {target: 0}
    for item in target.rglob("*"):
        try:
            if not item.is_file() or item.is_symlink():
                continue
            amount = item.stat().st_size
        except OSError:
            continue
        for parent in item.parents:
            if parent == target:
                sizes[target] += amount
                break
            if len(parent.relative_to(target).parts) <= depth:
                sizes[parent] = sizes.get(parent, 0) + amount
    return sizes


def _process_name(pid: int | None) -> str:
    """Return the name of a process, or a dash when it cannot be read."""
    if not pid:
        return "-"
    try:
        return psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return "-"
