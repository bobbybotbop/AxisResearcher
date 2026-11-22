"""
Tests for the Copy Seller title-simplification hook (ticket 07).

The seam under test is ``simplify_title_to_phrase`` — the single swappable
function the pipeline routes through. The deterministic trim (sales-term
stripping, short-phrase output, determinism) is verified against worked
examples; the config read/save seam and the HTTP endpoint are verified against
the preferences table in axis.db using the shared ``config_file`` fixture from
tests/conftest.py. Nothing here touches the network.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import backend.db as db
from backend import copy_seller
from app import app


@pytest.fixture()
def client():
    return app.test_client()


# ---------------------------------------------------------------------------
# simplify_title_to_phrase — deterministic sales-term trim
# ---------------------------------------------------------------------------

def test_simplify_strips_quantity_and_pack_terms():
    phrase = copy_seller.simplify_title_to_phrase(
        "3D Printed Dragon Bookend Set of 2 Pack Lot New"
    )
    for term in ("set", "2", "pack", "lot", "new"):
        assert term not in phrase.split()
    assert "dragon" in phrase
    assert "bookend" in phrase


def test_simplify_strips_color_and_condition_terms():
    phrase = copy_seller.simplify_title_to_phrase(
        "Purple Gold Dragon Bookend - Brand New Condition!"
    )
    words = phrase.split()
    for term in ("purple", "gold", "brand", "new", "condition"):
        assert term not in words
    assert "dragon" in words
    assert "bookend" in words


def test_simplify_produces_short_common_search_phrase():
    title = "3D Printed Articulated Dragon Fidget Toy Purple & Gold, New Condition!"
    phrase = copy_seller.simplify_title_to_phrase(title)
    assert isinstance(phrase, str)
    assert phrase == phrase.lower()
    assert "  " not in phrase
    assert len(phrase.split()) <= copy_seller.DEFAULT_TITLE_MAX_WORDS


def test_simplify_is_deterministic():
    title = "  3D Printed Dragon Bookend - Purple & Gold, New Condition!  "
    assert copy_seller.simplify_title_to_phrase(title) == \
        copy_seller.simplify_title_to_phrase(title)


def test_simplify_strips_punctuation_and_collapses_whitespace():
    phrase = copy_seller.simplify_title_to_phrase("Dragon,  Bookend!! (Decor) [Home]")
    assert "  " not in phrase
    for ch in ",!()[]":
        assert ch not in phrase


def test_simplify_empty_title_returns_empty_string():
    assert copy_seller.simplify_title_to_phrase("") == ""
    assert copy_seller.simplify_title_to_phrase(None) == ""


def test_simplify_respects_config_max_words():
    config = {"stopwords": [], "max_words": 2}
    phrase = copy_seller.simplify_title_to_phrase(
        "dragon bookend decor home office", config=config
    )
    assert len(phrase.split()) <= 2


def test_simplify_respects_config_custom_stopwords():
    config = {"stopwords": ["dragon"], "max_words": 6}
    phrase = copy_seller.simplify_title_to_phrase(
        "dragon bookend decor", config=config
    )
    assert "dragon" not in phrase.split()
    assert "bookend" in phrase.split()


# ---------------------------------------------------------------------------
# Config persistence seam: get/save_title_simplification_config
# ---------------------------------------------------------------------------

def test_get_config_returns_defaults(config_file):
    config = copy_seller.get_title_simplification_config()
    assert config["max_words"] == copy_seller.DEFAULT_TITLE_MAX_WORDS
    assert isinstance(config["stopwords"], list)
    assert len(config["stopwords"]) > 0


def test_save_config_roundtrip(config_file):
    saved = copy_seller.save_title_simplification_config(
        stopwords=["foo", "bar"], max_words=4
    )
    assert saved["stopwords"] == ["foo", "bar"]
    assert saved["max_words"] == 4

    reread = copy_seller.get_title_simplification_config()
    assert reread == saved

    assert db.get_preference("title_simplification_stopwords") == ["foo", "bar"]
    assert db.get_preference("title_simplification_max_words") == 4


def test_save_config_partial_update(config_file):
    copy_seller.save_title_simplification_config(max_words=3)
    config = copy_seller.get_title_simplification_config()
    assert config["max_words"] == 3
    # stopwords untouched -> still the non-empty default list
    assert len(config["stopwords"]) > 0


@pytest.mark.parametrize("kwargs", [
    {"max_words": 0},
    {"max_words": -1},
    {"max_words": "abc"},
    {"stopwords": "notalist"},
    {"stopwords": [1, 2, 3]},
])
def test_save_config_rejects_invalid_values(config_file, kwargs):
    with pytest.raises(ValueError):
        copy_seller.save_title_simplification_config(**kwargs)


# ---------------------------------------------------------------------------
# HTTP seam: /api/research/title-simplification
# ---------------------------------------------------------------------------

def test_route_get_defaults(client, config_file):
    res = client.get("/api/research/title-simplification")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["max_words"] == copy_seller.DEFAULT_TITLE_MAX_WORDS
    assert isinstance(payload["stopwords"], list)


def test_route_post_roundtrip(client, config_file):
    res = client.post(
        "/api/research/title-simplification",
        json={"stopwords": ["x", "y"], "max_words": 5},
    )
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["stopwords"] == ["x", "y"]
    assert payload["max_words"] == 5

    reread = client.get("/api/research/title-simplification").get_json()
    assert reread == payload


def test_route_post_rejects_invalid(client, config_file):
    res = client.post(
        "/api/research/title-simplification",
        json={"max_words": 0},
    )
    assert res.status_code == 400
