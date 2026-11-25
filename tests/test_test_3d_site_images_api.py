import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import app as app_module
from app import app


@pytest.fixture()
def client():
    return app.test_client()


def _patch_all_probes(monkeypatch, overrides=None):
    results = {
        "probe_images_thingiverse": (True, "3 image(s) found"),
        "probe_images_printables": (True, "2 image(s) found"),
        "probe_images_makerworld": (True, "4 image(s) found"),
        "probe_images_cults3d": (True, "1 image(s) found"),
        "probe_images_thangs": (True, "5 image(s) found"),
    }
    results.update(overrides or {})
    for name, (ok, message) in results.items():
        monkeypatch.setattr(app_module, name, lambda ok=ok, message=message: (ok, message))


def test_test_3d_site_images_returns_per_site_status(client, monkeypatch):
    _patch_all_probes(monkeypatch)
    res = client.get("/api/test-3d-site-images")
    assert res.status_code == 200
    results = res.get_json()["results"]
    assert set(results) == {
        "thingiverse.com", "printables.com", "makerworld.com", "cults3d.com", "thangs.com"
    }
    for site in results:
        assert results[site]["ok"] is True
        assert "image(s) found" in results[site]["message"]


def test_test_3d_site_images_reports_failures(client, monkeypatch):
    _patch_all_probes(monkeypatch, {"probe_images_thangs": (False, "no __NEXT_DATA__")})
    res = client.get("/api/test-3d-site-images")
    results = res.get_json()["results"]
    assert results["thangs.com"]["ok"] is False
    assert results["thangs.com"]["message"] == "no __NEXT_DATA__"
    assert results["printables.com"]["ok"] is True


def test_test_3d_site_images_survives_probe_exception(client, monkeypatch):
    _patch_all_probes(monkeypatch)

    def boom():
        raise RuntimeError("browser exploded")
    monkeypatch.setattr(app_module, "probe_images_cults3d", boom)

    res = client.get("/api/test-3d-site-images")
    assert res.status_code == 200
    results = res.get_json()["results"]
    assert results["cults3d.com"]["ok"] is False
    assert "browser exploded" in results["cults3d.com"]["message"]


def test_test_3d_site_images_times_out_hanging_probe(client, monkeypatch):
    import time

    _patch_all_probes(monkeypatch)
    monkeypatch.setattr(app_module, "_PROBE_TIMEOUT", 1)

    def hang():
        time.sleep(5)
        return (True, "too late")
    monkeypatch.setattr(app_module, "probe_images_thangs", hang)

    res = client.get("/api/test-3d-site-images")
    assert res.status_code == 200
    results = res.get_json()["results"]
    assert results["thangs.com"]["ok"] is False
    assert "timed out" in results["thangs.com"]["message"]
    assert results["printables.com"]["ok"] is True
