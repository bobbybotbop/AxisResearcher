import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import importlib
import types


def test_warm_rembg_triggers_lazy_import(monkeypatch):
    fake_rembg = types.ModuleType("rembg")
    fake_rembg.remove = lambda data: data
    monkeypatch.setitem(sys.modules, "rembg", fake_rembg)

    import backend.copyScripts.imageEditing as image_editing
    importlib.reload(image_editing)

    image_editing.warm_rembg()

    assert sys.modules["rembg"] is fake_rembg


def test_warm_rembg_is_failure_safe(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "rembg" or name.startswith("rembg."):
            raise ImportError("boom: rembg unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(sys.modules, "rembg", raising=False)
    monkeypatch.setattr(builtins, "__import__", fake_import)

    import backend.copyScripts.imageEditing as image_editing
    importlib.reload(image_editing)

    # Must not raise even though the rembg import blows up.
    image_editing.warm_rembg()
