import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.downloaders import makerworld


def test_probe_reports_down_when_pipeline_fails(monkeypatch):
    """The probe must genuinely exercise the download pipeline: when a real
    fetch cannot succeed (e.g. pending Bambu Lab email verification), the site
    must not report operational."""
    def failing_download(*args, **kwargs):
        raise RuntimeError("MakerWorld requires an email verification code for this login.")

    monkeypatch.setattr(makerworld, "download_3mf", failing_download)
    ok, message = makerworld.probe()
    assert not ok
    assert "verification code" in message


def test_probe_reports_operational_when_pipeline_fetches_a_file(monkeypatch):
    monkeypatch.setattr(makerworld, "download_3mf", lambda *a, **k: ("probe_model.3mf", b"\x00" * 2048))
    ok, message = makerworld.probe()
    assert ok
    assert "probe_model.3mf" in message


def test_probe_reports_down_on_empty_file(monkeypatch):
    monkeypatch.setattr(makerworld, "download_3mf", lambda *a, **k: ("probe_model.3mf", b""))
    ok, _ = makerworld.probe()
    assert not ok
