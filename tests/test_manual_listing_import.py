"""
Regression tests for imported (MANUAL_*) listing metadata.

Bug: imported listings in the History tab showed the wrong quantity (lifetime
listed total instead of available stock), no category, and MANUAL_XXX as the
SKU — stale files were never rewritten once created because rewrites only
triggered on quantity changes.

No network or eBay credentials needed: the parser is tested against a fixture
GetSellerList <Item>, and the writer against a tmp Generated_Listings dir.
"""
import json
import os
import sys
import xml.etree.ElementTree as ET

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.ebay_cli import _parse_seller_list_item
from backend import ebay_cli
from backend.copyScripts import combine_data

NS = "{urn:ebay:apis:eBLBaseComponents}"

SELLER_ITEM_XML = """<Item xmlns="urn:ebay:apis:eBLBaseComponents">
  <ItemID>197523731100</ItemID>
  <Title>Refill Adaptor</Title>
  <SKU>1</SKU>
  <Quantity>85</Quantity>
  <SellingStatus>
    <CurrentPrice currencyID="USD">7.0</CurrentPrice>
    <QuantitySold>70</QuantitySold>
  </SellingStatus>
  <PrimaryCategory>
    <CategoryID>181415</CategoryID>
    <CategoryName>Sporting Goods:Camping &amp; Hiking</CategoryName>
  </PrimaryCategory>
  <ConditionDisplayName>New</ConditionDisplayName>
  <ListingDetails><StartTime>2025-07-13T03:59:16.000Z</StartTime></ListingDetails>
</Item>"""


def _item(quantity=15, seller_sku="1", category_id="181415"):
    return {
        "item_id": "197523731100",
        "title": "Refill Adaptor",
        "quantity": quantity,
        "price": "7.0",
        "image_urls": ["https://example.com/a.jpg"],
        "condition": "New",
        "start_time": "2025-07-13T03:59:16.000Z",
        "description": "",
        "seller_sku": seller_sku,
        "is_variation": False,
        "category_id": category_id,
    }


def test_parse_available_quantity_and_category():
    item = _parse_seller_list_item(ET.fromstring(SELLER_ITEM_XML), NS)
    # eBay <Quantity> is the lifetime listed total; available = Quantity - QuantitySold.
    assert item["quantity"] == 15
    assert item["seller_sku"] == "1"
    assert item["category_id"] == "181415"


@pytest.fixture()
def listings_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(combine_data, "_get_generated_listings_dir", lambda: str(tmp_path))
    return tmp_path


def _read(listings_dir):
    with open(listings_dir / "MANUAL_197523731100.json", encoding="utf-8") as f:
        return json.load(f)


def test_writes_category_sku_quantity(listings_dir):
    assert combine_data.write_manual_listing_json(_item()) is True
    d = _read(listings_dir)
    assert d["offer"]["categoryId"] == "181415"
    assert d["sellerSku"] == "1"
    assert d["offer"]["quantity"] == 15
    assert d["inventoryItem"]["availability"]["shipToLocationAvailability"]["quantity"] == 15


def test_unchanged_item_is_skipped(listings_dir):
    combine_data.write_manual_listing_json(_item())
    assert combine_data.write_manual_listing_json(_item()) is False


def test_quantity_change_rewrites(listings_dir):
    combine_data.write_manual_listing_json(_item(quantity=15))
    assert combine_data.write_manual_listing_json(_item(quantity=14)) is True
    assert _read(listings_dir)["offer"]["quantity"] == 14


def test_stale_file_heals_and_preserves_local_fields(listings_dir):
    """A stale import (missing sellerSku/categoryId) must heal even when the
    quantity is unchanged, and local-only fields must survive the rewrite."""
    combine_data.write_manual_listing_json(_item())
    path = listings_dir / "MANUAL_197523731100.json"
    d = _read(listings_dir)
    d["sellerSku"] = ""  # stale: missing seller SKU -> UI shows MANUAL_XXX
    d["offer"].pop("categoryId", None)  # stale: missing category
    d["models"] = {"stl": "model-ref"}  # local-only field to preserve
    d["ebay_status"] = "not_found"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f)

    assert combine_data.write_manual_listing_json(_item()) is True  # same quantity!
    healed = _read(listings_dir)
    assert healed["sellerSku"] == "1"
    assert healed["offer"]["categoryId"] == "181415"
    assert healed["models"] == {"stl": "model-ref"}
    assert healed["ebay_status"] == "not_found"


GET_ITEM_XML = """<GetItemResponse xmlns="urn:ebay:apis:eBLBaseComponents">
  <Ack>Success</Ack>
  <Item>
    <ItemID>197711484829</ItemID>
    <Quantity>59</Quantity>
    <SellingStatus>
      <CurrentPrice currencyID="USD">5.99</CurrentPrice>
      <QuantitySold>53</QuantitySold>
      <ListingStatus>Active</ListingStatus>
    </SellingStatus>
  </Item>
</GetItemResponse>"""


def test_get_item_available_quantity(monkeypatch):
    """GetItem must return available stock (Quantity - QuantitySold), not the
    lifetime listed total. Regression: a too-narrow OutputSelector made eBay
    drop QuantitySold from the response, yielding 59 instead of 6."""
    monkeypatch.setenv("user_token", "fake-token")

    class _Resp:
        status_code = 200
        text = GET_ITEM_XML

    captured = {}

    def fake_post(url, data, headers, timeout):
        captured["body"] = data.decode("utf-8")
        return _Resp()

    monkeypatch.setattr(ebay_cli.requests, "post", fake_post)
    assert ebay_cli.get_item_available_quantity("197711484829") == 6
    # The selector must request the whole SellingStatus node; eBay omits
    # QuantitySold when only SellingStatus.QuantitySold is selected.
    assert "<OutputSelector>ItemID,Quantity,SellingStatus</OutputSelector>" in captured["body"]


def test_get_item_available_quantity_failure(monkeypatch):
    monkeypatch.setenv("user_token", "fake-token")

    class _Resp:
        status_code = 200
        text = ('<GetItemResponse xmlns="urn:ebay:apis:eBLBaseComponents">'
                "<Ack>Failure</Ack></GetItemResponse>")

    monkeypatch.setattr(ebay_cli.requests, "post", lambda *a, **k: _Resp())
    assert ebay_cli.get_item_available_quantity("197711484829") is None
