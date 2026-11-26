"""
Force-close everything that can block `npm run dev` for this checkout.

Kills, in order:
  1. Any process holding a project port in ANY TCP state (LISTENING,
     ESTABLISHED server-side, CLOSE_WAIT, ...). Scans the backend port and
     the Vite port-walk range (frontend port through frontend port + 10).
  2. Any node / python process whose command line belongs to this
     checkout (stale Vite servers, orphaned `npm run dev` / concurrently
     wrappers, stale `python app.py` backends) — even if it is no longer
     bound to a port.

Ports come from AXIS_FRONTEND_PORT / AXIS_BACKEND_PORT (environment first,
then the repo-root .env), defaulting to 4000/5000 — so a worktree with its
own ports only ever kills its own dev servers, never the main checkout's
or another worktree's.

Sockets left behind by a dead process (zombie LISTENING / TIME_WAIT) cannot
be killed. Instead of failing immediately, the script waits and retries the
bind for up to WAIT_TIMEOUT_SECONDS, which is almost always enough for the
OS to release the port. It only exits non-zero if the port is still blocked
after the wait.

Usage:
    python scripts/force_close_ports.py
    npm run force-close
"""

import os
import re
import signal
import socket
import subprocess
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# How long to wait for the OS to reap a dead process's socket before giving up.
WAIT_TIMEOUT_SECONDS = 120
WAIT_POLL_SECONDS = 2


def _project_ports() -> tuple[int, int]:
    """Resolve (frontend, backend) ports: env vars, then repo-root .env, then defaults."""
    values: dict[str, str] = {}
    env_file = os.path.join(PROJECT_ROOT, ".env")
    try:
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    values[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    values.update({k: v for k, v in os.environ.items() if k in ("AXIS_FRONTEND_PORT", "AXIS_BACKEND_PORT")})
    frontend = int(values.get("AXIS_FRONTEND_PORT", "4000"))
    backend = int(values.get("AXIS_BACKEND_PORT", "5000"))
    return frontend, backend


FRONTEND_PORT, BACKEND_PORT = _project_ports()
FRONTEND_PORTS = range(FRONTEND_PORT, FRONTEND_PORT + 11)  # Vite walks 4000, 4001, ... when busy
ALL_PORTS = (BACKEND_PORT, *FRONTEND_PORTS)
ALL_PORTS_SET = set(ALL_PORTS)


def _run(cmd, timeout=20):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return None


def _port_is_free(port: int) -> bool:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind(("127.0.0.1", port))
    except OSError:
        return False
    finally:
        probe.close()
    return True


if sys.platform == "win32":
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
        """PIDs of node/python processes whose command line references this checkout."""
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

    def _ancestor_pids() -> set[str]:
        """PIDs of this process's whole parent chain (npm / concurrently / shell)."""
        result = _run([
            "powershell", "-NoProfile", "-Command",
            f"$id = {os.getpid()}; "
            "$chain = @(); "
            "while ($id) {{ "
            "  $proc = Get-CimInstance Win32_Process -Filter \"ProcessId=$id\" 2>$null; "
            "  if (-not $proc) {{ break }}; "
            "  $chain += $proc.ProcessId; "
            "  $id = $proc.ParentProcessId "
            "}}; "
            "$chain",
        ])
        chain: set[str] = {str(os.getpid())}
        if result and result.stdout:
            chain |= {line.strip() for line in result.stdout.splitlines() if line.strip().isdigit()}
        return chain

    def _kill_pid(pid: str) -> bool:
        result = _run(["taskkill", "/PID", pid, "/T", "/F"])
        return result is not None and result.returncode == 0

    def _blocked_message(blocked: list[int]) -> str:
        return (
            f"\nPort(s) {blocked} are held by a dead process's socket (no live PID to kill).\n"
            f"Waiting up to {WAIT_TIMEOUT_SECONDS}s for Windows to release them ..."
        )

    def _timeout_message(blocked: list[int]) -> str:
        return (
            f"\nERROR: port(s) {blocked} still refuse a bind after {WAIT_TIMEOUT_SECONDS}s.\n"
            "A process outside this project may be holding them. Check with:\n"
            "  netstat -ano | findstr " + " ".join(f":{p}" for p in blocked)
        )

else:  # Linux / macOS
    def _pids_on_ports() -> dict[str, set[int]]:
        """Map PID -> set of project ports it appears on (any TCP state, local side)."""
        result = _run(["ss", "-tanp"])
        if not result or not result.stdout:
            return {}
        hits: dict[str, set[int]] = {}
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) < 5:
                continue
            # ss -tanp columns: State Recv-Q Send-Q Local:Port Peer:Port [Process]
            local = parts[3]
            port_match = re.search(r':(\d+)$', local)
            if not port_match:
                continue
            port = int(port_match.group(1))
            if port not in ALL_PORTS_SET:
                continue
            for m in re.finditer(r'pid=(\d+)', line):
                hits.setdefault(m.group(1), set()).add(port)
        return hits

    def _stale_project_pids() -> set[str]:
        """PIDs of node/python dev-server processes that belong to this checkout."""
        # Match only specific dev-server markers to avoid killing npm/concurrently itself.
        # Mirrors the Windows WQL filter: node.exe/python*.exe AND project path.
        dev_markers = [
            os.path.join(PROJECT_ROOT, ".venv"),  # venv Python processes (Flask backend)
            "vite",                                # Vite frontend dev server
            "concurrently",                        # dev orchestrator
        ]
        result = _run(["ps", "-eo", "pid,comm,args"])
        if not result or not result.stdout:
            return set()
        pids: set[str] = set()
        for line in result.stdout.splitlines()[1:]:
            parts = line.split(None, 2)
            if len(parts) < 3:
                continue
            pid, comm, args = parts
            if not pid.isdigit():
                continue
            if not (comm == "node" or comm.startswith("python")):
                continue
            if any(marker in args for marker in dev_markers):
                pids.add(pid)
        return pids

    def _ancestor_pids() -> set[str]:
        """PIDs of this process's whole parent chain (npm / concurrently / shell)."""
        pids: set[str] = set()
        pid = os.getpid()
        while pid > 1:
            pids.add(str(pid))
            try:
                with open(f"/proc/{pid}/status") as f:
                    for line in f:
                        if line.startswith("PPid:"):
                            pid = int(line.split()[1])
                            break
                    else:
                        break
            except OSError:
                break
        return pids

    def _kill_pid(pid: str) -> bool:
        try:
            os.kill(int(pid), signal.SIGTERM)
            return True
        except ProcessLookupError:
            return True  # already gone
        except OSError:
            return False

    def _blocked_message(blocked: list[int]) -> str:
        return (
            f"\nPort(s) {blocked} are held by a dead process's socket (no live PID to kill).\n"
            f"Waiting up to {WAIT_TIMEOUT_SECONDS}s for the OS to release them ..."
        )

    def _timeout_message(blocked: list[int]) -> str:
        return (
            f"\nERROR: port(s) {blocked} still refuse a bind after {WAIT_TIMEOUT_SECONDS}s.\n"
            "A process outside this project may be holding them. Check with:\n"
            "  ss -tlnp | grep -E '" + "|".join(f":{p}" for p in blocked) + "'"
        )


def force_close() -> None:
    port_hits = _pids_on_ports()
    stale = _stale_project_pids()

    # Never kill our own process or any ancestor (npm / concurrently / shell):
    # doing so tears down the very `npm run dev` tree that launched us.
    protected = _ancestor_pids()

    targets = (set(port_hits) | stale) - protected
    killed: set[str] = set()

    if not targets:
        print("No stale project processes or port holders found.")
    for pid in sorted(targets, key=int):
        ports = sorted(port_hits.get(pid, ()))
        reason = f"holding port(s) {ports}" if ports else "stale project process"
        print(f"Killing PID {pid} ({reason}) ...", end=" ")
        if _kill_pid(pid):
            print("done.")
            killed.add(pid)
        else:
            print("FAILED.")

    if killed:
        time.sleep(1)

    blocked = [p for p in (FRONTEND_PORT, BACKEND_PORT) if not _port_is_free(p)]
    if not blocked:
        print(f"All project ports are free (backend :{BACKEND_PORT}, frontend :{FRONTEND_PORT}).")
        return

    # A port is still blocked but there is no live process to kill: a dead
    # process left its socket behind. Wait for the OS to release it.
    print(_blocked_message(blocked))
    deadline = time.monotonic() + WAIT_TIMEOUT_SECONDS
    while True:
        blocked = [p for p in (FRONTEND_PORT, BACKEND_PORT) if not _port_is_free(p)]
        if not blocked:
            print(f"All project ports are free (backend :{BACKEND_PORT}, frontend :{FRONTEND_PORT}).")
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        print(f"  still blocked: {blocked} ({int(remaining)}s left) ...", end="\r")
        time.sleep(min(WAIT_POLL_SECONDS, remaining))

    print(_timeout_message(blocked))
    sys.exit(1)


if __name__ == "__main__":
    force_close()
