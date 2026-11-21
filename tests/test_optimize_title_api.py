import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import app as app_module
from app import app


@pytest.fixture()
def client():
    return app.test_client()


def test_requires_title(client):
    resp = client.post("/api/optimize-title", json={})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]


def test_returns_optimized_title(client, monkeypatch):
    monkeypatch.setattr(
        app_module, "call_text_llm",
        lambda prompt, model=None: "Articulated Dragon Figurine",
    )
    resp = client.post("/api/optimize-title", json={
        "title": "3D Printed Articulated Dragon Figurine Blue New Fast Shipping Lot of 2",
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["optimized_title"] == "Articulated Dragon Figurine"


def test_prompt_contains_original_title_and_stripping_rules(client, monkeypatch):
    captured = {}

    def fake_llm(prompt, model=None):
        captured["prompt"] = prompt
        return "Dragon"

    monkeypatch.setattr(app_module, "call_text_llm", fake_llm)
    resp = client.post("/api/optimize-title", json={"title": "Blue Dragon New"})
    assert resp.status_code == 200
    assert "Blue Dragon New" in captured["prompt"]


def test_custom_prompt_overrides_default_file(client, monkeypatch):
    captured = {}

    def fake_llm(prompt, model=None):
        captured["prompt"] = prompt
        return "Dragon"

    monkeypatch.setattr(app_module, "call_text_llm", fake_llm)
    resp = client.post("/api/optimize-title", json={
        "title": "Blue Dragon",
        "prompt": "CUSTOM RULES\n\nTitle: {title}",
    })
    assert resp.status_code == 200
    assert captured["prompt"] == "CUSTOM RULES\n\nTitle: Blue Dragon"


def test_passes_requested_text_model(client, monkeypatch):
    captured = {}

    def fake_llm(prompt, model=None):
        captured["model"] = model
        return "Dragon"

    monkeypatch.setattr(app_module, "call_text_llm", fake_llm)
    resp = client.post("/api/optimize-title", json={
        "title": "Blue Dragon",
        "text_model": "anthropic/claude-haiku-4.5",
    })
    assert resp.status_code == 200
    assert captured["model"] == "anthropic/claude-haiku-4.5"


def test_defaults_to_haiku_model(client, monkeypatch):
    captured = {}

    def fake_llm(prompt, model=None):
        captured["model"] = model
        return "Dragon"

    monkeypatch.setattr(app_module, "call_text_llm", fake_llm)
    resp = client.post("/api/optimize-title", json={"title": "Blue Dragon"})
    assert resp.status_code == 200
    assert captured["model"] == "anthropic/claude-haiku-4.5"


def test_llm_failure_returns_502(client, monkeypatch):
    monkeypatch.setattr(app_module, "call_text_llm", lambda prompt, model=None: None)
    resp = client.post("/api/optimize-title", json={"title": "Blue Dragon"})
    assert resp.status_code == 502
    assert "error" in resp.get_json()


def test_empty_llm_response_returns_502(client, monkeypatch):
    monkeypatch.setattr(app_module, "call_text_llm", lambda prompt, model=None: "   ")
    resp = client.post("/api/optimize-title", json={"title": "Blue Dragon"})
    assert resp.status_code == 502
    assert "error" in resp.get_json()


def test_optimized_title_is_sanitized(client, monkeypatch):
    # Same contract as _sanitize_title: strip surrounding quotes
    monkeypatch.setattr(
        app_module, "call_text_llm",
        lambda prompt, model=None: '  "Articulated Dragon"  ',
    )
    resp = client.post("/api/optimize-title", json={"title": "Blue Dragon"})
    assert resp.status_code == 200
    assert resp.get_json()["optimized_title"] == "Articulated Dragon"


def test_get_default_prompt_returns_template_with_placeholder(client):
    resp = client.get("/api/optimize-title/prompt")
    assert resp.status_code == 200
    prompt = resp.get_json()["prompt"]
    assert "{title}" in prompt
    assert len(prompt) > 50
