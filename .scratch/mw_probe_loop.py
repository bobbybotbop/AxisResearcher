"""Feedback loop for the MakerWorld false-positive "operational" status.

The bug: /api/test-3d-sites reports makerworld.com as operational even when the
real download pipeline cannot fetch anything (expired session, pending Bambu Lab
email verification). probe() only hit the public metadata API and checked that
credentials/a profile exist.

Loop design (fast, deterministic, red-capable):
  - Stub makerworld.download_3mf to FAIL. A genuine probe must report not-OK.
    Current code never calls the pipeline, so it still reports OK -> RED.
  - Stub makerworld.download_3mf to SUCCEED. Probe must report OK.
    (Guards against an inverted fix that always reports failure.)

Optional --real mode: no stubs, bogus credentials, nonexistent profile dir.
A genuine probe runs the real pipeline, the login fails, and probe must report
not-OK. Slow (launches a browser) — used to confirm end-to-end after the fix.

Exit code 1 = RED (bug present), 0 = GREEN.
"""

import os
import sys

# Bogus credentials: no genuine fetch can succeed with these.
os.environ["MAKERWORLD_EMAIL"] = "not-a-real-user@example.invalid"
os.environ["MAKERWORLD_PASSWORD"] = "definitely-wrong-password"

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from backend.downloaders import makerworld

# Isolate from any real session profile on disk.
makerworld._PROFILE_DIR = os.path.join(
    os.path.dirname(makerworld.__file__), "mw_loop_nonexistent_profile"
)

REAL = "--real" in sys.argv

if not REAL:
    real_download = makerworld.download_3mf

    def failing_download(*args, **kwargs):
        raise RuntimeError("MakerWorld requires an email verification code for this login.")

    makerworld.download_3mf = failing_download
    ok_fail, msg_fail = makerworld.probe()
    print(f"[stub: pipeline FAILS]    probe() -> ok={ok_fail} message={msg_fail!r}")

    def succeeding_download(*args, **kwargs):
        return ("probe_model.3mf", b"\x00" * 2048)

    makerworld.download_3mf = succeeding_download
    ok_succ, msg_succ = makerworld.probe()
    print(f"[stub: pipeline SUCCEEDS] probe() -> ok={ok_succ} message={msg_succ!r}")

    makerworld.download_3mf = real_download

    red = False
    if ok_fail:
        print("RED: probe reports operational while the pipeline cannot fetch a file")
        red = True
    if not ok_succ:
        print("RED: probe reports failure while the pipeline succeeds (inverted check)")
        red = True
    if red:
        sys.exit(1)
    print("GREEN: probe verdict matches the real pipeline outcome")
else:
    ok, message = makerworld.probe()
    print(f"[real pipeline, bogus creds] probe() -> ok={ok} message={message!r}")
    if ok:
        print("RED: probe reports operational although no genuine fetch is possible")
        sys.exit(1)
    print("GREEN: probe correctly reports not operational")
