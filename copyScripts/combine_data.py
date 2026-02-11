"""
Module for creating eBay inventory and offer objects and saving them to JSON files.
"""

import os
import json
import requests
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
    Get the current counter and/or SKU based on the counter value, then increment the counter.
    Format: AXIS_[counter]
    
    Args:
        return_counter (bool): If True, returns both counter and SKU as a tuple
    
    Returns:
        str or tuple: Current SKU in format AXIS_[counter], or (counter, SKU) if return_counter is True
    """
    config = load_config()
    counter = config["counter"]
    sku = f"AXIS_{counter}"
    
    # Increment the counter for next time using get_next_sku logic
    config["counter"] = config["counter"] + 1
    save_config(config)
    
    if return_counter:
        return counter, sku
    return sku

def get_next_sku(return_counter=False):
    """
    Increment the counter and return the new counter and/or SKU.
    Format: AXIS_[counter]
    
    This is the ONLY function that should increment the counter.
    Use get_current_sku() for reading the current SKU without incrementing.
    
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

def get_current_sku(return_counter=False):
    """
    Get the current counter and/or SKU WITHOUT incrementing.
    Format: AXIS_[counter]
    
    Use this function for reading/displaying the current SKU.
    Use get_next_sku() only when creating a new listing.
    
    Args:
        return_counter (bool): If True, returns both counter and SKU as a tuple
    
    Returns:
        str or tuple: Current SKU in format AXIS_[counter], 
                     or (counter, SKU) if return_counter is True
    """
    config = load_config()
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

# Note: TEST_SKU is no longer set at module level to prevent counter increments on import
# Use get_current_sku() for reading, or get_next_sku() when creating a new listing

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
        "title": "[need to change]",
        "description": "[need to change]", 
        "aspects": {}, #[need to change]
        "imageUrls": []  # need to change
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


def create_listing_with_preferences(
    sku=None,
    inventory_item_data=None,
    offer_data=None,
    output_filename=None
):
    """
    Create an inventory and offer object and save it to a JSON file in Generated_Listings folder.
    
    Args:
        sku (str, optional): SKU for the listing. If None, generates a new SKU using get_next_sku().
        inventory_item_data (dict, optional): Inventory item data. If None, uses TEST_INVENTORY_ITEM_DATA.
        offer_data (dict, optional): Offer data. If None, uses TEST_OFFER_DATA.
        output_filename (str, optional): Output filename. If None, generates timestamped filename.
    
    Returns:
        str: The SKU that was used/created
    """
    # Generate SKU if not provided (only when actually creating a listing)
    if sku is None:
        sku = get_next_sku()
    
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
    # Use absolute path to ensure we're saving in the right directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "Generated_Listings")
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
    
    return sku




def load_listing_data(sku=None, filename=None):
    """
    Load inventory and offer data from a JSON file in Generated_Listings folder.
    
    Args:
        sku (str, optional): SKU for the listing to load. If None, uses current SKU.
                             If filename is provided, sku is ignored.
        filename (str, optional): Specific filename to load. If None, finds most recent file for SKU.
    
    Returns:
        dict: Dictionary with "sku", "inventoryItem", and "offer" keys, or None if file doesn't exist
    """
    # Use absolute path to ensure we're looking in the right directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "Generated_Listings")
    
    # If specific filename provided, use it
    if filename:
        filepath = os.path.join(output_dir, filename)
        if not filepath.endswith(".json"):
            filepath += ".json"
    else:
        # Use SKU to find the file (simply {sku}.json)
        if sku is None:
            # If no SKU provided, use current SKU (for reading existing files)
            sku = get_current_sku()
        
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


def listing_file_exists(sku):
    """
    Check if a JSON file named {sku}.json exists in the Generated_Listings folder.
    
    Args:
        sku (str): The SKU to check
    
    Returns:
        bool: True if the file exists, False otherwise
    """
    # Use absolute path to ensure we're looking in the right directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "Generated_Listings")
    filepath = os.path.join(output_dir, f"{sku}.json")
    return os.path.exists(filepath)


def update_listing_title_description(sku, new_text):
    """
    Update the title and description in an existing listing JSON file.
    
    Args:
        sku (str): The SKU of the listing to update
        new_text (dict): Dictionary containing optimized content with 'edited_title' and 'edited_description' keys
    
    Returns:
        bool: True if update was successful, False otherwise
    """
    # Check if file exists using helper function
    if not listing_file_exists(sku):
        print(f"⚠️  Listing file not found for SKU: {sku}")
        return False
    
    # Extract edited_title and edited_description from new_text dict
    new_title = new_text.get('edited_title', '')
    new_description = new_text.get('edited_description', '')
    
    if not new_title or not new_description:
        print(f"❌ Error: new_text dict must contain 'edited_title' and 'edited_description' keys")
        return False
    
    # Use absolute path to ensure we're looking in the right directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "Generated_Listings")
    filepath = os.path.join(output_dir, f"{sku}.json")
    
    try:
        # Load the existing listing data
        with open(filepath, 'r', encoding='utf-8') as f:
            listing_data = json.load(f)
        
        # Update title and description
        listing_data["inventoryItem"]["product"]["title"] = new_title
        listing_data["inventoryItem"]["product"]["description"] = new_description
        
        # Save the updated data back to the file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(listing_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Updated listing file: {os.path.basename(filepath)}")
        print(f"   SKU: {sku}")
        print(f"   Title: {new_title}")
        print(f"   Description: {new_description[:50]}..." if len(new_description) > 50 else f"   Description: {new_description}")
        
        return True
    except KeyError as e:
        print(f"❌ Error: Missing required key in listing data: {e}")
        return False
    except Exception as e:
        print(f"❌ Error updating listing data file: {e}")
        return False


def update_listing_meta_data(sku, new_price, new_category_id):
    """
    Update the price and categoryId in an existing listing JSON file.
    
    Args:
        sku (str): The SKU of the listing to update
        new_price (str): New price value to set (as string, e.g., "199.99")
        new_category_id (str): New categoryId to set (as string, e.g., "181415")
    
    Returns:
        bool: True if update was successful, False otherwise
    """
    # Check if file exists using helper function
    if not listing_file_exists(sku):
        print(f"⚠️  Listing file not found for SKU: {sku}")
        return False
    
    # Use absolute path to ensure we're looking in the right directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "Generated_Listings")
    filepath = os.path.join(output_dir, f"{sku}.json")
    
    try:
        # Load the existing listing data
        with open(filepath, 'r', encoding='utf-8') as f:
            listing_data = json.load(f)
        
        # Update price and categoryId
        listing_data["offer"]["pricingSummary"]["price"]["value"] = new_price
        listing_data["offer"]["categoryId"] = new_category_id
        
        # Save the updated data back to the file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(listing_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Updated listing file: {os.path.basename(filepath)}")
        print(f"   SKU: {sku}")
        print(f"   Price: {new_price}")
        print(f"   Category ID: {new_category_id}")
        
        return True
    except KeyError as e:
        print(f"❌ Error: Missing required key in listing data: {e}")
        return False
    except Exception as e:
        print(f"❌ Error updating listing data file: {e}")
        return False


def update_listing_images(sku, image_urls):
    """
    Update the imageUrls in an existing listing JSON file.
    
    Args:
        sku (str): The SKU of the listing to update
        image_urls (list[str]): List of image URLs to set
    
    Returns:
        bool: True if update was successful, False otherwise
    """
    # Check if file exists using helper function
    if not listing_file_exists(sku):
        print(f"⚠️  Listing file not found for SKU: {sku}")
        return False
    
    if not image_urls or not isinstance(image_urls, list):
        print(f"❌ Error: image_urls must be a non-empty list")
        return False
    
    # Use absolute path to ensure we're looking in the right directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "Generated_Listings")
    filepath = os.path.join(output_dir, f"{sku}.json")
    
    try:
        # Load the existing listing data
        with open(filepath, 'r', encoding='utf-8') as f:
            listing_data = json.load(f)
        
        # Ensure product structure exists
        if "inventoryItem" not in listing_data:
            listing_data["inventoryItem"] = {}
        if "product" not in listing_data["inventoryItem"]:
            listing_data["inventoryItem"]["product"] = {}
        
        # Update imageUrls
        listing_data["inventoryItem"]["product"]["imageUrls"] = image_urls
        
        # Save the updated data back to the file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(listing_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Updated listing file: {os.path.basename(filepath)}")
        print(f"   SKU: {sku}")
        print(f"   Images: {len(image_urls)} image URL(s) added")
        for idx, url in enumerate(image_urls[:5], 1):  # Show first 5
            print(f"      {idx}. {url}")
        if len(image_urls) > 5:
            print(f"      ... and {len(image_urls) - 5} more")
        
        return True
    except KeyError as e:
        print(f"❌ Error: Missing required key in listing data: {e}")
        return False
    except Exception as e:
        print(f"❌ Error updating listing data file: {e}")
        return False


def get_item_aspects_for_category(category_id, category_tree_id="0"):
    """
    Get item aspects for a specific eBay category using the Taxonomy API.
    
    Args:
        category_id (str): The unique identifier of the leaf category for which aspects are being requested
        category_tree_id (str): The unique identifier of the eBay category tree. Default is "0" for US marketplace.
    
    Returns:
        dict: Response data containing aspects, or None on failure
    """
    # Import here to avoid circular import issues
    from helper_functions import helper_get_valid_token, handle_http_error
    
    # Get a valid token
    valid_token = helper_get_valid_token()
    if not valid_token:
        print("❌ Error: Could not get valid access token")
        return None
    
    # Build the API URL
    url = f"https://api.ebay.com/commerce/taxonomy/v1/category_tree/{category_tree_id}/get_item_aspects_for_category"
    params = {
        "category_id": category_id
    }
    
    headers = {
        'Authorization': f'Bearer {valid_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        print(f"🔍 Fetching aspects for category {category_id}...")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            aspects = data.get('aspects', [])
            
            print(f"\n📋 Aspects for category {category_id}:")
            print("=" * 80)
            
            for aspect in aspects:
                aspect_name = aspect.get('localizedAspectName', 'N/A')
                constraint = aspect.get('aspectConstraint', {})
                usage = constraint.get('aspectUsage', 'N/A')
                
                print(f"{aspect_name}: {usage}")
            
            print("=" * 80)
            return data
        else:
            handle_http_error(response, "get_item_aspects_for_category")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Error calling Taxonomy API: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def _find_matching_aspect_name(target_name, category_aspect_map):
    """
    Find a matching aspect name from category_aspect_map using flexible matching.
    First tries exact match (case-insensitive), then tries partial matches.
    
    Args:
        target_name (str): The aspect name to find
        category_aspect_map (dict): Dictionary mapping lowercase aspect names to actual names
    
    Returns:
        str or None: The matched aspect name from category, or None if no match found
    """
    target_lower = target_name.lower()
    
    # First try exact match
    if target_lower in category_aspect_map:
        return category_aspect_map[target_lower]
    
    # Try partial matches (e.g., "Brand" matches "Brand Name")
    for category_key, category_name in category_aspect_map.items():
        # Check if target is contained in category name or vice versa
        if target_lower in category_key or category_key in target_lower:
            return category_name
    
    # Try word-based matching (e.g., "Brand" matches "Brand Name")
    target_words = set(target_lower.split())
    for category_key, category_name in category_aspect_map.items():
        category_words = set(category_key.split())
        # If all words in target are in category, it's a match
        if target_words and target_words.issubset(category_words):
            return category_name
    
    return None


def update_listing_with_aspects(sku, localizedAspects=None):
    """
    Update a listing JSON file to add aspect values. Applies localized aspects first,
    then hardcoded aspects (which override localized aspects if there's a conflict).
    
    Hardcoded aspects (override localized aspects):
    - "Country of Origin": ["United States"]
    - "Brand": ["Plastic Love Shop"]
    - "Material": ["PETG"]
    - "Color": ["Black"]
    
    Args:
        sku (str): The SKU of the listing to update
        localizedAspects (list[dict], optional): List of aspect dictionaries with structure:
            {
                "type": "STRING",
                "name": "Brand",
                "value": "Speedway"
            }
            Defaults to None (empty list).
    
    Returns:
        bool: True if update was successful, False otherwise
    """
    # Define hardcoded aspect values (these override localized aspects)
    hardcoded_aspects = {
        "Country of Origin": ["United States"],
        "Brand": ["Plastic Love Shop"],
        "Material": ["PETG"],
        "Color": ["Black"]
    }
    
    # Normalize localizedAspects parameter
    if localizedAspects is None:
        localizedAspects = []
    
    # Check if file exists
    if not listing_file_exists(sku):
        print(f"⚠️  Listing file not found for SKU: {sku}")
        return False
    
    # Load the listing data
    listing_data = load_listing_data(sku=sku)
    if not listing_data:
        return False
    
    # Get category ID from the listing
    category_id = listing_data.get('offer', {}).get('categoryId')
    if not category_id:
        print(f"❌ Error: No categoryId found in listing data")
        return False
    
    # Get aspects for this category
    aspects_data = get_item_aspects_for_category(category_id)
    if not aspects_data:
        print(f"❌ Error: Could not get aspects for category {category_id}")
        return False
    
    # Get list of available aspects from API response
    aspects_list = aspects_data.get('aspects', [])
    
    # Create a mapping of category aspect names (case-insensitive) to their actual names
    category_aspect_map = {}
    for aspect in aspects_list:
        aspect_name = aspect.get('localizedAspectName', '')
        if aspect_name:
            category_aspect_map[aspect_name.lower()] = aspect_name
    
    # Debug: Print available aspects for this category
    print(f"\n📋 Available aspects for category {category_id}:")
    for aspect_name in category_aspect_map.values():
        print(f"   - {aspect_name}")
    
    # Start with matched aspects dictionary
    matched_aspects = {}
    
    # Step 1: Apply localized aspects first (if provided)
    if localizedAspects:
        print(f"\n🔄 Processing {len(localizedAspects)} localized aspects...")
        for localized_aspect in localizedAspects:
            if not isinstance(localized_aspect, dict):
                continue
            
            aspect_name = localized_aspect.get('name', '')
            aspect_value = localized_aspect.get('value', '')
            
            if not aspect_name or not aspect_value:
                continue
            
            # Use flexible matching to find the aspect in category
            actual_aspect_name = _find_matching_aspect_name(aspect_name, category_aspect_map)
            if actual_aspect_name:
                # Convert value to array format to match eBay format
                matched_aspects[actual_aspect_name] = [aspect_value]
                print(f"   ✓ Matched localized aspect: {actual_aspect_name} = {aspect_value}")
            else:
                print(f"   ⚠ Skipped localized aspect (not in category): {aspect_name}")
    
    # Step 2: Apply hardcoded aspects (these override localized aspects)
    print(f"\n🔧 Processing {len(hardcoded_aspects)} hardcoded aspects...")
    for hardcoded_name, hardcoded_value in hardcoded_aspects.items():
        # Use flexible matching to find the aspect in category
        actual_aspect_name = _find_matching_aspect_name(hardcoded_name, category_aspect_map)
        if actual_aspect_name:
            # Override with hardcoded value
            matched_aspects[actual_aspect_name] = hardcoded_value
            print(f"   ✓ Matched hardcoded aspect: {actual_aspect_name} = {hardcoded_value}")
        else:
            # If not found in category, try to add it anyway (eBay may accept it or reject it)
            # Use the hardcoded name as-is
            matched_aspects[hardcoded_name] = hardcoded_value
            print(f"   ⚠ Added hardcoded aspect (not verified in category): {hardcoded_name} = {hardcoded_value}")
    
    if not matched_aspects:
        print(f"ℹ️  No matching aspects found for category {category_id}")
        return False
    
    # Update the listing JSON file
    # Use absolute path to ensure we're looking in the right directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "Generated_Listings")
    filepath = os.path.join(output_dir, f"{sku}.json")
    
    try:
        # Ensure aspects dictionary exists
        if "aspects" not in listing_data["inventoryItem"]["product"]:
            listing_data["inventoryItem"]["product"]["aspects"] = {}
        
        # Add or update the matched aspects
        for aspect_name, aspect_value in matched_aspects.items():
            listing_data["inventoryItem"]["product"]["aspects"][aspect_name] = aspect_value
        
        # Save the updated data back to the file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(listing_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Updated listing file: {os.path.basename(filepath)}")
        print(f"   SKU: {sku}")
        for aspect_name, aspect_value in matched_aspects.items():
            print(f"   Added aspect: {aspect_name} = {aspect_value}")
        
        return True
    except KeyError as e:
        print(f"❌ Error: Missing required key in listing data: {e}")
        return False
    except Exception as e:
        print(f"❌ Error updating listing data file: {e}")
        return False
