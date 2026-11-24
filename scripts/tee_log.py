"""
Run a command, mirroring its stdout/stderr to both the terminal and a log file.

Used by `npm run dev` so agents can read dev-server output from latest_logs/
instead of probing ports. The log is truncated on each run.

Usage:
    python scripts/tee_log.py <log-file> <command...>
"""

import os
import subprocess
import sys


def main() -> None:
    # Windows consoles default to cp1252; server output (e.g. Vite's ➜) is UTF-8.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    log_path, command = sys.argv[1], sys.argv[2:]
    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    proc = subprocess.Popen(
        " ".join(command),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    with open(log_path, "w", encoding="utf-8", buffering=1) as log:
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            log.write(line)
    sys.exit(proc.wait())


if __name__ == "__main__":
    main()
