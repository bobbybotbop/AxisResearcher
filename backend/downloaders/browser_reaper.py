"""Kill orphaned Chrome processes that hold a downloader's profile dir hostage.

A Chrome launched with `user_data_dir=<profile>` that survives its driver
(a crashed run, a killed server) leaves the profile locked: the next launch
hangs on "cannot connect to chrome". The per-module _PROFILE_LOCK guarantees
no *live* session of this process is using the profile when this runs, so
any Chrome still holding the profile dir is by definition a zombie.
"""

import os
import subprocess
import sys
import threading

# One automated Chrome at a time, process-wide. Concurrent UC-mode launches
# (even on different profiles) kill each other mid-run — the driver then dies
# with "window/handles connection refused" minutes into the probe. The headed
# sign-in session browsers deliberately do NOT take this lock so an open
# login window never blocks the pipeline; the per-profile locks already
# prevent same-site conflicts.
BROWSER_SESSION_LOCK = threading.Lock()

_BROWSER_DEATH_MARKERS = (
    "window/handles",
    "invalid session id",
    "chrome not reachable",
    "no such window",
    "connection refused",
    "cannot connect",
    "target closed",
)


def is_browser_death(exc: Exception) -> bool:
    """True when the exception means the Chrome/driver process died mid-run —
    a transient condition worth one retry, not a site failure."""
    msg = str(exc).lower()
    return any(m in msg for m in _BROWSER_DEATH_MARKERS)


def reap_stale_profile_chromes(profile_dir: str) -> None:
    """Force-kill chrome.exe processes whose command line references profile_dir.
    No-op off Windows and on any error — a failed reap must never block a launch."""
    if not sys.platform.startswith("win"):
        return
    needle = os.path.basename(os.path.normpath(profile_dir))
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" "
        f"| Where-Object {{ $_.CommandLine -match [regex]::Escape('{needle}') }} "
        "| ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {} }"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            timeout=20,
        )
    except Exception as e:
        print(f"[browser_reaper] reap skipped: {e}")
