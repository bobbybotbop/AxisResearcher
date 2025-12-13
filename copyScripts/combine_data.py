"""
Module for creating eBay inventory and offer objects and saving them to JSON files.
"""

import os
import json
from datetime import datetime

# eBay API base URL
EBAY_INVENTORY_API_BASE = "https://api.ebay.com/sell/inventory/v1"

# Item Data Preferences
MERCHANT_LOCATION_KEY = "PlasticLoveShopLocation"
DEFAULT_QUANTITY = 15
DEFAULT_DIMESIONS = {
    "length": "9",
    "width": "6",
    "height": "3",
    "unit": "INCH"
}
# Might change later
DEFAULT_WEIGHT = {
    "value": "0.4",
    "unit": "POUND"
}

# Test Data Constants (organized at top for easy modification)
TEST_SKU = "TEST_007"

# Test Inventory Item Data
TEST_INVENTORY_ITEM_DATA = {
    "availability": {
        "shipToLocationAvailability": {
            "quantity": DEFAULT_QUANTITY
        }
    },
    "condition": "NEW",
    "packageWeightAndSize": {
        "weight": DEFAULT_WEIGHT,
        "dimensions": DEFAULT_DIMESIONS
    },
    "product": {
        "title": "GoPro Hero4 Helmet Cam",
        "description": "New GoPro Hero4 Helmet Cam. Unopened box. Perfect for capturing your adventures in stunning HD quality.",
        "aspects": {
            "Brand": ["GoPro"],
            "Type": ["Helmet/Action"],
            "Storage Type": ["Removable"],
            "Recording Definition": ["High Definition"],
            "Media Format": ["Flash Drive (SSD)"],
            "Optical Zoom": ["10x"]
        },
        "imageUrls": [
            "http://i.ebayimg.com/images/i/182196556219-0-1/s-l1000.jpg",
            "http://i.ebayimg.com/images/i/182196556219-0-1/s-l1001.jpg",
            "http://i.ebayimg.com/images/i/182196556219-0-1/s-l1002.jpg"
        ]
    }
}

# Test Offer Data
TEST_OFFER_DATA = {
    "marketplaceId": "EBAY_US",
    "format": "FIXED_PRICE",
    "quantity": DEFAULT_QUANTITY,
    "pricingSummary": {
        "price": {
            "value": "199.99",
            "currency": "USD"
        }
    },
    "listingDuration": "GTC",  # Good 'Til Cancelled
    "categoryId": "181415",  # Cameras & Photo > Camcorders
}


def create_inventory_and_offer_listing(
    sku=None,
    inventory_item_data=None,
    offer_data=None,
    output_filename=None
):
    """
    Create an inventory and offer object and save it to a JSON file in Generated_Listings folder.
    
    Args:
        sku (str, optional): SKU for the listing. If None, uses TEST_SKU.
        inventory_item_data (dict, optional): Inventory item data. If None, uses TEST_INVENTORY_ITEM_DATA.
        offer_data (dict, optional): Offer data. If None, uses TEST_OFFER_DATA.
        output_filename (str, optional): Output filename. If None, generates timestamped filename.
    
    Returns:
        str: Path to the created JSON file
    """
    # Use defaults if not provided
    if sku is None:
        sku = TEST_SKU
    
    if inventory_item_data is None:
        inventory_item_data = TEST_INVENTORY_ITEM_DATA.copy()
    
    if offer_data is None:
        offer_data = TEST_OFFER_DATA.copy()
    
    # Add merchant location key to offer data if not present
    if "merchantLocationKey" not in offer_data:
        offer_data["merchantLocationKey"] = MERCHANT_LOCATION_KEY
    
    # Create the combined listing object
    listing_object = {
        "sku": sku,
        "inventoryItem": inventory_item_data,
        "offer": offer_data
    }
    
    # Create Generated_Listings directory if it doesn't exist
    output_dir = "Generated_Listings"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename if not provided
    if output_filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"listing_{sku}_{timestamp}.json"
    
    # Ensure filename ends with .json
    if not output_filename.endswith(".json"):
        output_filename += ".json"
    
    # Full path to output file
    output_path = os.path.join(output_dir, output_filename)
    
    # Write to JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(listing_object, f, indent=2, ensure_ascii=False)
    
    print(f"Created listing file: {output_path}")
    print(f"   SKU: {sku}")
    
    return output_path

