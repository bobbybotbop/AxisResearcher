"""
Module for creating eBay inventory and offer objects and saving them to JSON files.
"""

import os
import json
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# eBay Business Policy IDs (from .env)
FULFILLMENT_POLICY_ID = os.getenv('fulfillment_policy_id')
PAYMENT_POLICY_ID = os.getenv('payment_policy_id')
RETURN_POLICY_ID = os.getenv('return_policy_id')

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
        "title": "GoPro Hero4 Helmet Cam", # need to change
        "description": "New GoPro Hero4 Helmet Cam. Unopened box. Perfect for capturing your adventures in stunning HD quality.",  # need to change
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
        ]  # need to change
    }
}

# Test Offer Data
TEST_OFFER_DATA = {
    "marketplaceId": "EBAY_US",
    "format": "FIXED_PRICE",
    "quantity": DEFAULT_QUANTITY,
    "pricingSummary": {
        "price": {
            "value": "199.99", # need to change
            "currency": "USD"
        }
    },
    "listingDuration": "GTC", 
    "categoryId": "181415",  # need to change
}


def get_listing_policies():
    """
    Get listing policies from environment variables.
    
    Returns:
        dict: Dictionary with policy IDs, or None if no policies are set
    """
    policies = {}
    if FULFILLMENT_POLICY_ID:
        policies["fulfillmentPolicyId"] = FULFILLMENT_POLICY_ID
    if PAYMENT_POLICY_ID:
        policies["paymentPolicyId"] = PAYMENT_POLICY_ID
    if RETURN_POLICY_ID:
        policies["returnPolicyId"] = RETURN_POLICY_ID
    return policies if policies else None


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
    
    # Add listing policies from .env if available and not already present
    if "listingPolicies" not in offer_data:
        policies = get_listing_policies()
        if policies:
            offer_data["listingPolicies"] = policies
    
    # Get current date and time
    created_datetime = datetime.now().isoformat()
    
    # Create the combined listing object
    listing_object = {
        "sku": sku,
        "createdDateTime": created_datetime,
        "inventoryItem": inventory_item_data,
        "offer": offer_data
    }
    
    # Create Generated_Listings directory if it doesn't exist
    output_dir = "Generated_Listings"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename if not provided (simply use SKU)
    if output_filename is None:
        output_filename = f"{sku}.json"
    
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


def load_listing_data(sku=None, filename=None):
    """
    Load inventory and offer data from a JSON file in Generated_Listings folder.
    
    Args:
        sku (str, optional): SKU for the listing to load. If None, uses TEST_SKU.
                             If filename is provided, sku is ignored.
        filename (str, optional): Specific filename to load. If None, finds most recent file for SKU.
    
    Returns:
        dict: Dictionary with "sku", "inventoryItem", and "offer" keys, or None if file doesn't exist
    """
    output_dir = "Generated_Listings"
    
    # If specific filename provided, use it
    if filename:
        filepath = os.path.join(output_dir, filename)
        if not filepath.endswith(".json"):
            filepath += ".json"
    else:
        # Use SKU to find the file (simply {sku}.json)
        if sku is None:
            sku = TEST_SKU
        
        # File is simply {sku}.json
        filepath = os.path.join(output_dir, f"{sku}.json")
    
    try:
        if not os.path.exists(filepath):
            print(f"⚠️  Listing data file not found: {filepath}")
            return None
        
        # Load from JSON file
        with open(filepath, 'r', encoding='utf-8') as f:
            listing_data = json.load(f)
        
        print(f"✅ Loaded listing data from: {os.path.basename(filepath)}")
        return listing_data
    except Exception as e:
        print(f"❌ Error loading listing data file: {e}")
        return None
