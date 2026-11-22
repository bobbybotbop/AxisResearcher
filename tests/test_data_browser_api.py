"""
Tests for the Data Browser API endpoint (GLOSSARY: "Data Browser Tab").

Seam under test: GET /api/data-browser/<table>?page=1&page_size=25
exercised through the Flask test client against a tmp axis.db.

The endpoint serves paginated rows from whitelisted SQLite tables for the
Data Browser tab — purely visual browsing, no SQL query interface.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import backend.db as db
from app import app


@pytest.fixture()
def client():
    return app.test_client()


def _seed_listings(count):
    """Insert `count` listings into the tmp database."""
    for i in range(1, count + 1):
        sku = f"AXIS_{i}"
        db.save_listing({
            "sku": sku,
            "ebayListingId": f"100000000{i:03d}",
            "createdDateTime": "2026-01-15T10:00:00.000Z",
            "inventoryItem": {
                "product": {
                    "title": f"Listing {i}",
                    "imageUrls": [f"https://example.com/img{i}.png"],
                    "description": f"Description {i}",
                },
                "condition": "New",
                "availability": {"shipToLocationAvailability": {"quantity": 5}},
            },
            "offer": {
                "categoryId": "181415",
                "pricingSummary": {"price": {"value": "10.00", "currency": "USD"}},
                "quantity": 5,
            },
        })


# --- table whitelist ---

def test_rejects_unknown_table(client, config_file):
    resp = client.get("/api/data-browser/unknown_table")
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


def test_rejects_sql_injection_attempt(client, config_file):
    resp = client.get("/api/data-browser/listings;DROP TABLE listings")
    assert resp.status_code == 400


def test_accepts_all_whitelisted_tables(client, config_file):
    for table in ("listings", "preferences", "logs", "prompts"):
        resp = client.get(f"/api/data-browser/{table}")
        assert resp.status_code == 200, f"table={table} returned {resp.status_code}"


# --- pagination ---

def test_returns_paginated_rows(client, config_file):
    _seed_listings(30)
    resp = client.get("/api/data-browser/listings?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["table"] == "listings"
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["total_rows"] == 30
    assert data["total_pages"] == 3
    assert len(data["rows"]) == 10


def test_second_page_returns_remaining_rows(client, config_file):
    _seed_listings(15)
    resp = client.get("/api/data-browser/listings?page=2&page_size=10")
    data = resp.get_json()
    assert data["page"] == 2
    assert len(data["rows"]) == 5


def test_default_pagination(client, config_file):
    _seed_listings(5)
    resp = client.get("/api/data-browser/listings")
    data = resp.get_json()
    assert data["page"] == 1
    assert data["page_size"] == 25
    assert len(data["rows"]) == 5


def test_page_beyond_range_returns_empty(client, config_file):
    _seed_listings(3)
    resp = client.get("/api/data-browser/listings?page=99&page_size=10")
    data = resp.get_json()
    assert len(data["rows"]) == 0
    assert data["total_rows"] == 3


def test_page_size_clamped_to_max(client, config_file):
    _seed_listings(5)
    resp = client.get("/api/data-browser/listings?page_size=9999")
    data = resp.get_json()
    assert data["page_size"] <= 200


# --- row shape ---

def test_listing_rows_contain_expected_columns(client, config_file):
    _seed_listings(1)
    resp = client.get("/api/data-browser/listings")
    data = resp.get_json()
    row = data["rows"][0]
    assert "sku" in row
    assert "title" in row
    assert "raw_json" in row


def test_preferences_rows_contain_key_and_value(client, config_file):
    resp = client.get("/api/data-browser/preferences")
    data = resp.get_json()
    assert len(data["rows"]) > 0
    row = data["rows"][0]
    assert "key" in row
    assert "value" in row


def test_logs_rows_contain_expected_columns(client, config_file):
    db.log("test_event", "success", detail="hello")
    resp = client.get("/api/data-browser/logs")
    data = resp.get_json()
    assert len(data["rows"]) == 1
    row = data["rows"][0]
    assert "id" in row
    assert "timestamp" in row
    assert "event" in row
    assert "status" in row
    assert "details" in row


def test_prompts_rows_contain_expected_columns(client, config_file):
    db.save_prompt("title/test.txt", "prompt content")
    resp = client.get("/api/data-browser/prompts")
    data = resp.get_json()
    assert len(data["rows"]) == 1
    row = data["rows"][0]
    assert "name" in row
    assert "content" in row
    assert "updated_at" in row


def test_columns_list_returned(client, config_file):
    resp = client.get("/api/data-browser/listings")
    data = resp.get_json()
    assert "columns" in data
    assert isinstance(data["columns"], list)
    assert len(data["columns"]) > 0
