"""Feedback loop for the MakerWorld "verify login closes the browser early" bug.

The bug: verify_login_headed() owns the browser in a `with SB(...)` block and
returns (closing the window) on scripted guesses — _is_logged_in() false
positives during page load / on the SSO ticket page, or a hard 150s cap while
the human fetches an email code. The window closes before the human finishes.

The fix: a session API where the HUMAN decides when the session is done —
open_session() leaves the browser open, session_status() reports it,
close_session() (or the user closing the window) ends it gracefully, persisting
cookies to the profile.

Isolation: empty credentials + a throwaway profile dir, so the real login
profile is never touched. Launches a real HEADED browser window for ~30s.

Modes:
  --old   RED check against the legacy verify_login_headed(): times how long
          the browser stays usable for a human. The old code returns (closing
          the window) with zero human interaction -> RED.
  (none)  GREEN check against the new session API:
          1. open_session() leaves the browser open; it must stay open for a
             full 20s poll window (the script never closes it on its own).
          2. The profile lock is held while the session is open.
          3. close_session() ends it gracefully, releases the lock, and the
             profile dir persists on disk (cookies saved).

Exit code 1 = RED (bug present), 0 = GREEN.
"""

import os
import sys
import threading
import time

# No credentials: nothing may auto-complete; the human is the only actor.
os.environ["MAKERWORLD_EMAIL"] = ""
os.environ["MAKERWORLD_PASSWORD"] = ""

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from backend.downloaders import makerworld

# Throwaway profile — never touch the real login session.
makerworld._PROFILE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "mw_session_loop_profile"
)

# A window that closes faster than this gave the human no real chance to act
# (read a page, open email, copy a code, type it in).
HUMAN_USABLE_SECONDS = 45


def run_old() -> int:
    """Time the legacy flow: it must NOT return (closing the window) before a
    human could possibly have finished. No human interacts in this test, so any
    return at all demonstrates the script deciding to close the browser."""
    result = {}

    def target():
        result["t0"] = time.time()
        result["ret"] = makerworld.verify_login_headed()
        result["elapsed"] = time.time() - result["t0"]

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout=180)
    if t.is_alive():
        # Still open after 180s with zero interaction: not the reported bug.
        print("INCONCLUSIVE: legacy flow kept the browser open >180s")
        return 2

    elapsed = result["elapsed"]
    ok, message = result["ret"]
    print(f"[legacy verify_login_headed] returned after {elapsed:.1f}s -> ok={ok} message={message!r}")
    if elapsed < HUMAN_USABLE_SECONDS:
        print(f"RED: browser closed after {elapsed:.1f}s with zero human interaction "
              f"(< {HUMAN_USABLE_SECONDS}s human-usable window) — the script, not the user, decided to close it")
        return 1
    print("GREEN: legacy flow kept the window open a human-usable duration")
    return 0


def run_new() -> int:
    red = False

    if not hasattr(makerworld, "open_session"):
        print("RED: makerworld.open_session does not exist (session API not implemented)")
        return 1

    ok, message = makerworld.open_session()
    print(f"[open_session] ok={ok} message={message!r}")
    if not ok:
        print("RED: open_session failed to open the browser")
        return 1

    # The browser must stay open for the whole poll window — the script may
    # never close it on its own (that was the bug).
    for i in range(20):
        time.sleep(1)
        status = makerworld.session_status()
        if not status.get("open"):
            print(f"RED: browser closed on its own after ~{i + 1}s (status={status})")
            red = True
            break
    else:
        print("[poll 20s] browser stayed open the whole window — good")

    if not makerworld._PROFILE_LOCK.locked():
        print("RED: profile lock is not held while the session browser is open")
        red = True
    else:
        print("[lock] profile lock held during session — good")

    ok, message = makerworld.close_session()
    print(f"[close_session] ok={ok} message={message!r}")
    if not ok:
        print("RED: close_session failed")
        red = True

    status = makerworld.session_status()
    if status.get("open"):
        print(f"RED: session still reports open after close_session (status={status})")
        red = True

    if makerworld._PROFILE_LOCK.locked():
        print("RED: profile lock still held after close_session — probe/download would deadlock")
        red = True
    else:
        print("[lock] profile lock released after close — good")

    if not os.path.isdir(makerworld._PROFILE_DIR):
        print("RED: profile dir missing after close — cookies would not persist")
        red = True
    else:
        print("[profile] profile dir persists on disk — good")

    if red:
        return 1
    print("GREEN: session lifecycle behaves — human owns the window, cookies persist")
    return 0


if __name__ == "__main__":
    code = run_old() if "--old" in sys.argv else run_new()
    sys.exit(code)
