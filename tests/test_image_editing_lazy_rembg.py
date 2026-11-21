import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import importlib
import subprocess
import types


REMBG_CHAIN = ("rembg", "pymatting", "numba", "onnxruntime")


def test_importing_image_editing_does_not_import_rembg():
    # Subprocess: the pytest process itself may already have rembg cached.
    code = (
        "import sys;"
        "import backend.copyScripts.imageEditing;"
        "leaked = [m for m in ('rembg', 'pymatting', 'numba', 'onnxruntime') if m in sys.modules];"
        "assert not leaked, f'eager heavy imports: {leaked}'"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=os.path.join(os.path.dirname(__file__), ".."),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_remove_background_delegates_to_rembg_and_returns_bytes(monkeypatch):
    sentinel = b"png-bytes-with-alpha"
    calls = []

    fake_rembg = types.ModuleType("rembg")
    def fake_remove(data):
        calls.append(data)
        return sentinel
    fake_rembg.remove = fake_remove
    monkeypatch.setitem(sys.modules, "rembg", fake_rembg)

    import backend.copyScripts.imageEditing as image_editing
    importlib.reload(image_editing)

    result = image_editing.remove_background(b"raw-image")

    assert result == sentinel
    assert calls == [b"raw-image"]
