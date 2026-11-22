"""
Force-close all ports used by the AxisResearcher project.

Kills any process holding ports 4000 (frontend) or 5000 (backend).
Useful when dev servers crash or terminals die without cleaning up.

Usage:
    python scripts/force_close_ports.py
"""

import subprocess
import sys
import time


PORTS = (4000, 5000)


def _pids_on_port(port: int) -> set[str]:
    """Return PIDs of processes listening on the given TCP port."""
    try:
        out = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            timeout=15,
        ).stdout
    except Exception:
        return set()

    pids = set()
    for line in out.splitlines():
        parts = line.split()
        if (
            len(parts) >= 5
            and parts[0] == "TCP"
            and parts[1].endswith(f":{port}")
            and parts[3].upper() == "LISTENING"
        ):
            pids.add(parts[-1])
    return pids


def _kill_pid(pid: str) -> bool:
    """Force-kill a PID and its children. Returns True on success."""
    try:
        result = subprocess.run(
            ["taskkill", "/PID", pid, "/T", "/F"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0
    except Exception:
        return False


def force_close_ports() -> None:
    killed_any = False
    for port in PORTS:
        pids = _pids_on_port(port)
        if not pids:
            print(f"Port {port}: no listeners found.")
            continue
        for pid in pids:
            print(f"Port {port}: killing PID {pid} ...", end=" ")
            if _kill_pid(pid):
                print("done.")
                killed_any = True
            else:
                print("FAILED.")

    if killed_any:
        # Give the OS a moment to release the sockets
        time.sleep(1)
        for port in PORTS:
            remaining = _pids_on_port(port)
            if remaining:
                print(f"WARNING: port {port} still held by PID(s): {', '.join(remaining)}")
            else:
                print(f"Port {port}: confirmed free.")
    else:
        print("No project ports were in use.")


if __name__ == "__main__":
    force_close_ports()
