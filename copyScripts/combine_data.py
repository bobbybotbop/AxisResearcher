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

# Config file path
CONFIG_FILE = "listingPreferences.json"

def load_config():
    """
    Load configuration from listingPreferences.json file.
    
    Returns:
        dict: Configuration dictionary
        
    Raises:
        FileNotFoundError: If listingPreferences.json does not exist
        ValueError: If listingPreferences.json is missing required keys, has invalid structure, or contains invalid JSON
    """
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(
            f"Config file '{CONFIG_FILE}' not found. "
            f"Please create {CONFIG_FILE} with required configuration."
        )
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON in config file '{CONFIG_FILE}': {e.msg}"
        ) from e
    
    # Validate required keys
    required_keys = [
        "counter",
        "merchant_location_key",
        "default_quantity",
        "default_dimensions",
        "default_weight"
    ]
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        raise ValueError(
            f"Config file '{CONFIG_FILE}' is missing required keys: {', '.join(missing_keys)}"
        )
    
    # Validate default_dimensions structure
    if not isinstance(config["default_dimensions"], dict):
        raise ValueError("'default_dimensions' must be a dictionary")
    required_dimension_keys = ["length", "width", "height", "unit"]
    missing_dim_keys = [key for key in required_dimension_keys if key not in config["default_dimensions"]]
    if missing_dim_keys:
        raise ValueError(
            f"'default_dimensions' is missing required keys: {', '.join(missing_dim_keys)}"
        )
    
    # Validate default_weight structure
    if not isinstance(config["default_weight"], dict):
        raise ValueError("'default_weight' must be a dictionary")
    required_weight_keys = ["value", "unit"]
    missing_weight_keys = [key for key in required_weight_keys if key not in config["default_weight"]]
    if missing_weight_keys:
        raise ValueError(
            f"'default_weight' is missing required keys: {', '.join(missing_weight_keys)}"
        )
    
    return config

def save_config(config):
    """
    Save configuration to listingPreferences.json file.
    
    Args:
        config (dict): Configuration dictionary to save
    """
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Error saving config: {e}")

def get_sku(return_counter=False):
    """
    Get the current counter and/or SKU based on the counter value.
    Format: AXIS_[counter]
    
    Args:
        return_counter (bool): If True, returns both counter and SKU as a tuple
    
    Returns:
        str or tuple: Current SKU in format AXIS_[counter], or (counter, SKU) if return_counter is True
    """
    config = load_config()
    counter = config["counter"]
    sku = f"AXIS_{counter}"
    
    if return_counter:
        return counter, sku
    return sku

def get_next_sku(return_counter=False):
    """
    Increment the counter and return the new counter and/or SKU.
    Format: AXIS_[counter]
    
    Args:
        return_counter (bool): If True, returns both counter and SKU as a tuple
    
    Returns:
        str or tuple: New SKU in format AXIS_[counter] after incrementing, 
                     or (counter, SKU) if return_counter is True
    """
    config = load_config()
    config["counter"] = config["counter"] + 1
    save_config(config)
    
    counter = config["counter"]
    sku = f"AXIS_{counter}"
    
    if return_counter:
        return counter, sku
    return sku

# Load configuration on import
_config = load_config()

# Item Data Preferences (loaded from config)
MERCHANT_LOCATION_KEY = _config["merchant_location_key"]
DEFAULT_QUANTITY = _config["default_quantity"]
DEFAULT_DIMESIONS = _config["default_dimensions"]
DEFAULT_WEIGHT = _config["default_weight"]

# Test Data Constants (loaded from config)
# SKU is generated from counter: AXIS_[counter]
TEST_SKU = get_sku()

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


def create_listing_with_metadata(
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
