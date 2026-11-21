import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path

import pytest

from backend.render import (
    RenderError,
    UnsupportedFormatError,
    render_model,
)
from backend.constants.render import (
    DEFAULT_RENDER_COLOR,
    DEFAULT_RENDER_RESOLUTION,
    DEFAULT_RENDER_ROUGHNESS,
    NATIVE_RENDER_EXTENSIONS,
)


def test_native_extensions_cover_stl_obj_ply():
    assert ".stl" in NATIVE_RENDER_EXTENSIONS
    assert ".obj" in NATIVE_RENDER_EXTENSIONS
    assert ".ply" in NATIVE_RENDER_EXTENSIONS


def test_defaults_match_spec():
    assert DEFAULT_RENDER_COLOR == "#1a1a1a"
    assert DEFAULT_RENDER_ROUGHNESS == pytest.approx(0.3)
    assert DEFAULT_RENDER_RESOLUTION == 1024


def test_missing_blender_raises_friendly_error(tmp_path):
    mesh = tmp_path / "model.stl"
    mesh.write_text("solid x\nendsolid x\n")
    with pytest.raises(RenderError, match="[Bb]lender"):
        render_model(
            mesh,
            tmp_path / "out.png",
            blender_path=str(tmp_path / "no-such-blender.exe"),
        )


def test_unsupported_extension_rejected(tmp_path):
    mesh = tmp_path / "model.amf"
    mesh.write_text("<amf/>")
    with pytest.raises(UnsupportedFormatError, match="\\.amf"):
        render_model(mesh, tmp_path / "out.png")


def test_hung_blender_is_killed_with_friendly_timeout(tmp_path, monkeypatch):
    """A Blender process exceeding the hard kill surfaces a friendly error."""
    import subprocess

    from backend.render import get_blender_path

    class HungProcess:
        stdout = iter(())
        stderr = ""

        def __init__(self):
            self.killed = False

        def wait(self, timeout=None):
            if not self.killed:
                raise subprocess.TimeoutExpired(cmd="blender", timeout=timeout)
            return 0

        def kill(self):
            self.killed = True

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: HungProcess())
    mesh = tmp_path / "model.stl"
    mesh.write_text("solid x\nendsolid x\n")
    if not os.path.exists(get_blender_path()):
        pytest.skip("Blender not installed on this machine")
    with pytest.raises(RenderError, match="too long"):
        render_model(mesh, tmp_path / "out.png")


def test_silent_hang_is_killed_within_timeout(tmp_path, monkeypatch):
    """A Blender that prints nothing and never exits is killed within ~timeout.

    The read must not block on stdout: with a silent hang there is no line to
    wake the loop, so the deadline has to be enforced while waiting for output.
    """
    import subprocess
    import threading

    blender = _blender_path_or_skip()

    class SilentHangProcess:
        """stdout never yields a line and never EOFs; the process never exits."""

        stderr = ""

        def __init__(self):
            self.killed = threading.Event()
            self.returncode = None

        def _read(self):
            # Block until killed: a silent Blender hang produces no output.
            while not self.killed.is_set():
                self.killed.wait(0.05)
            raise StopIteration

        @property
        def stdout(self):
            return iter(self._read, None)

        def wait(self, timeout=None):
            if self.killed.is_set():
                self.returncode = -9
                return self.returncode
            raise subprocess.TimeoutExpired(cmd="blender", timeout=timeout)

        def kill(self):
            self.killed.set()

    process = SilentHangProcess()
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: process)

    mesh = tmp_path / "model.stl"
    mesh.write_text("solid x\nendsolid x\n")

    import time
    start = time.monotonic()
    with pytest.raises(RenderError, match="too long"):
        render_model(mesh, tmp_path / "out.png", blender_path=blender, timeout=1)
    elapsed = time.monotonic() - start

    assert process.killed.is_set(), "silent hang must be killed, not waited on forever"
    assert elapsed < 10, f"kill took {elapsed:.1f}s for a 1s timeout — the read blocked on stdout"


class _FakeProcess:
    """Minimal Popen stand-in: canned stdout lines, exit code 0."""

    def __init__(self, lines, output_path):
        self._lines = lines
        self._output_path = output_path
        self.stderr = ""
        self.returncode = 0

    @property
    def stdout(self):
        return iter(self._lines)

    def wait(self, timeout=None):
        # Simulate Blender having written the image by the time it exits.
        Path(self._output_path).write_bytes(b"\x89PNG\r\n\x1a\n")
        return 0

    def kill(self):
        pass


def _blender_path_or_skip():
    from backend.render import get_blender_path
    if not os.path.exists(get_blender_path()):
        pytest.skip("Blender not installed on this machine")
    return get_blender_path()


def test_render_model_reports_sample_progress(tmp_path, monkeypatch):
    """Cycles' 'Sample N/M' and 'Remaining:MM:SS' checkpoints reach on_progress."""
    import subprocess

    blender = _blender_path_or_skip()
    out = tmp_path / "out.png"
    lines = [
        "Fra:1 Mem:9.95M | Time:00:00.00 | Mem:1.01M | Scene, ViewLayer | Sample 0/48\n",
        "Fra:1 | Time:00:00.04 | Remaining:00:08.00 | Mem:9.51M | Scene, ViewLayer | Sample 1/48\n",
        "noise and unrelated Blender chatter\n",
        "Fra:1 | Time:00:01.80 | Remaining:00:02.50 | Mem:9.51M | Scene, ViewLayer | Sample 48/48\n",
    ]
    monkeypatch.setattr(
        subprocess, "Popen",
        lambda *a, **k: _FakeProcess(lines, out),
    )

    mesh = tmp_path / "model.stl"
    mesh.write_text("solid x\nendsolid x\n")
    events = []
    render_model(mesh, out, blender_path=blender, on_progress=lambda *e: events.append(e))

    assert (0, 48, None) in events
    assert (1, 48, 8.0) in events
    assert (48, 48, 2.5) in events


def test_render_model_without_callback_still_works(tmp_path, monkeypatch):
    """Backwards compatible: no on_progress -> no parsing, same return value."""
    import subprocess

    blender = _blender_path_or_skip()
    out = tmp_path / "out.png"
    lines = ["Fra:1 | Scene, ViewLayer | Sample 48/48\n"]
    monkeypatch.setattr(
        subprocess, "Popen",
        lambda *a, **k: _FakeProcess(lines, out),
    )

    mesh = tmp_path / "model.stl"
    mesh.write_text("solid x\nendsolid x\n")
    result = render_model(mesh, out, blender_path=blender)
    assert result == out
    assert out.exists()
