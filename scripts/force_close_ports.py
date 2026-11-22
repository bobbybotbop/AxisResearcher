"""
Force-close everything that can block `npm run dev` for this project.

Kills, in order:
  1. Any process holding a project port in ANY TCP state (LISTENING,
     ESTABLISHED server-side, CLOSE_WAIT, ...). Scans backend :5000 and the
     Vite port-walk range :4000-4010.
  2. Any node.exe / python process whose command line belongs to this
     project (stale Vite servers, orphaned `npm run dev` / concurrently
     wrappers, stale `python app.py` backends) — even if it is no longer
     bound to a port.

Sockets left in TIME_WAIT by Windows (PID 0) cannot be killed; the script
reports them and waits for the bind to succeed instead.

Usage:
    python scripts/force_close_ports.py
    npm run force-close
"""

import os
import socket
import subprocess
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BACKEND_PORT = 5000
FRONTEND_PORTS = range(4000, 4011)  # Vite walks 4000, 4001, 4002, ... when busy
ALL_PORTS = (BACKEND_PORT, *FRONTEND_PORTS)


def _run(cmd, timeout=20):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return None


def _pids_on_ports() -> dict[str, set[int]]:
    """Map PID -> set of project ports it appears on (any TCP state, local side)."""
    result = _run(["netstat", "-ano", "-p", "tcp"])
    if not result or not result.stdout:
        return {}
    hits: dict[str, set[int]] = {}
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0] != "TCP":
            continue
        local = parts[1]
        pid = parts[-1]
        if pid == "0" or not pid.isdigit():
            continue
        for port in ALL_PORTS:
            if local.endswith(f":{port}"):
                hits.setdefault(pid, set()).add(port)
    return hits


def _stale_project_pids() -> set[str]:
    """PIDs of node/python processes whose command line references this project."""
    # WQL LIKE uses backslash as its escape character — double every
    # backslash in the path or the query is rejected as invalid.
    root_like = PROJECT_ROOT.replace("\\", "\\\\").replace("'", "''")
    wql = (
        "(Name='node.exe' OR Name LIKE 'python%.exe') AND "
        f"CommandLine LIKE '%{root_like}%'"
    )
    result = _run([
        "powershell", "-NoProfile", "-Command",
        f"Get-CimInstance Win32_Process -Filter \"{wql}\" | "
        "Select-Object -ExpandProperty ProcessId",
    ])
    if not result or not result.stdout:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip().isdigit()}


def _port_is_free(port: int) -> bool:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind(("127.0.0.1", port))
    except OSError:
        return False
    finally:
        probe.close()
    return True


def force_close() -> None:
    own_pid = str(os.getpid())
    killed: set[str] = set()

    port_hits = _pids_on_ports()
    stale = _stale_project_pids()

    targets = (set(port_hits) | stale) - {own_pid}

    if not targets:
        print("No stale project processes or port holders found.")
    for pid in sorted(targets, key=int):
        ports = sorted(port_hits.get(pid, ()))
        reason = f"holding port(s) {ports}" if ports else "stale project process"
        print(f"Killing PID {pid} ({reason}) ...", end=" ")
        result = _run(["taskkill", "/PID", pid, "/T", "/F"])
        if result is not None and result.returncode == 0:
            print("done.")
            killed.add(pid)
        else:
            print("FAILED.")

    if killed:
        time.sleep(1)

    blocked = [p for p in (4000, BACKEND_PORT) if not _port_is_free(p)]
    if blocked:
        print(
            f"\nWARNING: port(s) {blocked} still refuse a bind — most likely "
            "sockets stuck in TIME_WAIT (unowned, cannot be killed).\n"
            "Windows releases them within ~2 minutes. Wait a moment and run "
            "`npm run dev` again."
        )
        sys.exit(1)

    print("All project ports are free (backend :5000, frontend :4000).")


if __name__ == "__main__":
    force_close()
