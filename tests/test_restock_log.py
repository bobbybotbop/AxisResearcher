"""
Fixture-based tests for the restock log payload (POST /api/listings/restock).

All eBay network calls and listing-file helpers are monkeypatched — no network
or eBay credentials are needed. log_event is replaced with a capture stub so we
assert exactly what gets written to the activity log.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app as app_module


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


@pytest.fixture()
def client(monkeypatch):
    captured = []

    monkeypatch.setattr(app_module, "log_event", lambda *a, **k: captured.append((a, k)))
    # Treat every SKU as automated (non-manual) so we exercise the Sell
    # Inventory API path only.
    monkeypatch.setattr(app_module, "_is_manual_sku", lambda sku: False)
    monkeypatch.setattr(app_module, "update_local_listing_quantity", lambda sku, quantity: None)
    monkeypatch.setattr(app_module, "set_listing_ebay_status", lambda sku, status: True)
    monkeypatch.setattr(app_module, "_load_listing_file", lambda sku: None)
    # Token present so the automated path runs.
    monkeypatch.setenv("user_token", "fake-token")

    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        c.captured_logs = captured
        yield c


def _restock_payload():
    # bulk_update_price_quantity: AXIS_OK succeeds, AXIS_FAIL fails with an
    # exact eBay error, AXIS_GONE fails (will be confirmed not-found).
    return _FakeResponse(
        status_code=207,
        payload={
            "responses": [
                {"sku": "AXIS_OK", "statusCode": 200},
                {
                    "sku": "AXIS_FAIL",
                    "statusCode": 400,
                    "errors": [{"message": "Quantity must be greater than zero"}],
                },
                {"sku": "AXIS_GONE", "statusCode": 400, "errors": [{"message": "Invalid SKU"}]},
            ]
        },
    )


def test_restock_log_includes_failed_errors(client, monkeypatch):
    # AXIS_GONE is confirmed not-found by the verify step.
    monkeypatch.setattr(app_module, "_verify_failed_skus", lambda manual, axis: {"AXIS_GONE"})

    def _fake_post(url, headers=None, json=None, timeout=None):
        return _restock_payload()

    def _fake_get(url, headers=None, timeout=None):
        # offer lookup per SKU: return no offers (fine for the test)
        return _FakeResponse(status_code=200, payload={"offers": []})

    monkeypatch.setattr(app_module.requests, "post", _fake_post)
    monkeypatch.setattr(app_module.requests, "get", _fake_get)

    res = client.post(
        "/api/listings/restock",
        json={"skus": ["AXIS_OK", "AXIS_FAIL", "AXIS_GONE"], "quantity": 5},
    )
    assert res.status_code == 200

    restock_logs = [k for (a, k) in client.captured_logs if a and a[0] == "restock"]
    assert len(restock_logs) == 1
    payload = restock_logs[0]

    # Successes logged as before
    assert payload["skus"] == ["AXIS_OK"]
    # failed_skus is the union of real failures + not-found (existing behavior)
    assert payload["failed_skus"] == ["AXIS_FAIL", "AXIS_GONE"]
    assert payload["not_found_skus"] == ["AXIS_GONE"]

    # NEW: exact per-SKU error strings, only for SKUs that actually failed
    # (not-found SKUs must have been removed from failed_errors).
    assert payload["failed_errors"] == {"AXIS_FAIL": ["Quantity must be greater than zero"]}
