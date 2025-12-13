"""
eBay Inventory API - Complete Listing Workflow

This module provides functions to create inventory items, create offers, and publish
listings to eBay using the Inventory API.

The complete workflow:
1. Create/Replace Inventory Item (defines product details)
2. Create Offer (defines pricing and listing policies)
3. Publish Offer (makes listing live on eBay)

Additional functions:
- Create Inventory Location (creates warehouse locations for inventory management)

Required environment variables:
- user_token: OAuth user token with sell.inventory scope
- application_token: OAuth application token (fallback)

API Documentation:
- Inventory Item: https://developer.ebay.com/api-docs/sell/inventory/resources/inventory_item/methods/createOrReplaceInventoryItem
- Create Offer: https://developer.ebay.com/api-docs/sell/inventory/resources/offer/methods/createOffer
- Publish Offer: https://developer.ebay.com/api-docs/sell/inventory/resources/offer/methods/publishOffer
- Create Location: https://developer.ebay.com/api-docs/sell/inventory/resources/location/methods/createInventoryLocation
"""

import os
import requests
import json
from dotenv import load_dotenv
from helper_functions import helper_get_valid_token, handle_http_error

# Load environment variables
load_dotenv()

# Constants
USER_TOKEN = os.getenv('user_token')
APPLICATION_TOKEN = os.getenv('application_token')

# Import constants and test data from combine_data module
# Handle import when loaded via importlib (add directory to path)
import sys
import os
copy_scripts_dir = os.path.dirname(os.path.abspath(__file__))
if copy_scripts_dir not in sys.path:
    sys.path.insert(0, copy_scripts_dir)

from combine_data import (
    EBAY_INVENTORY_API_BASE,
    MERCHANT_LOCATION_KEY,
    DEFAULT_QUANTITY,
    DEFAULT_DIMESIONS,
    DEFAULT_WEIGHT,
    TEST_SKU,
    TEST_INVENTORY_ITEM_DATA,
    TEST_OFFER_DATA,
    load_listing_data,
    get_listing_policies
)


def create_ebay_listing(sku, inventory_item_data, locale="en-US", use_user_token=True):
    """
    Create or replace an inventory item using the eBay Inventory API.
    
    This is Step 1 of the listing workflow. The inventory item defines the product
    details but does NOT create a live listing. You must also create and publish an offer.
    
    Args:
        sku (str): Seller-defined SKU value for the inventory item (required, max 50 chars)
        inventory_item_data (dict): Dictionary containing inventory item data:
            - availability: dict with shipToLocationAvailability.quantity
            - condition: str (e.g., "NEW", "LIKE_NEW", "USED_EXCELLENT")
            - product: dict with title, description, aspects, imageUrls
            - packageWeightAndSize: dict (optional but recommended for shipping)
        locale (str): Locale code (e.g., "en-US"). Default: "en-US"
        use_user_token (bool): If True, use user_token. Default: True
    
    Returns:
        dict: Success dict with SKU and status, or None on failure
    """
    # Get a valid token
    if use_user_token:
        valid_token = USER_TOKEN
        if not valid_token:
            print("❌ Error: Could not get valid user token")
            print("💡 Make sure user_token is set in your .env file")
            return None
    else:
        valid_token = helper_get_valid_token()
        if not valid_token:
            print("❌ Error: Could not get valid access token")
            return None
    
    # Endpoint for creating/replacing a single inventory item
    url = f"{EBAY_INVENTORY_API_BASE}/inventory_item/{sku}"
    
    # Headers required by eBay API
    headers = {
        'Authorization': f'Bearer {valid_token}',
        'Content-Language': locale,
        'Content-Type': 'application/json'
    }
    
    try:
        print(f"📦 Step 1: Creating/updating inventory item with SKU: {sku}")
        print(f"🌐 Locale: {locale}")
        
        response = requests.put(url, headers=headers, json=inventory_item_data, timeout=30)
        
        # According to eBay API docs, 204 (No Content) is the expected success response
        # for createOrReplaceInventoryItem - it means success with no response body
        if response.status_code == 204:
            print(f"✅ Successfully created/updated inventory item")
            print(f"🆔 SKU: {sku}")
            # 204 responses have no body, so return a success dict
            return {
                "success": True,
                "sku": sku,
                "status_code": 204,
                "message": "Inventory item created/updated successfully"
            }
        elif response.status_code == 200 or response.status_code == 201:
            # Handle other success codes if they occur (though 204 is standard)
            result = response.json()
            print(f"✅ Successfully created/updated inventory item")
            print(f"🆔 SKU: {result.get('sku', sku)}")
            
            # Check for warnings
            warnings = result.get('warnings', [])
            if warnings:
                print(f"⚠️ Warnings:")
                for warning in warnings:
                    print(f"   - {warning.get('message', 'Unknown warning')}")
            
            return result
        else:
            handle_http_error(response, f"create_ebay_listing (SKU: {sku})")
            try:
                error_data = response.json()
                print(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Response text: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def create_offer(sku, offer_data, locale="en-US", use_user_token=True):
    """
    Create an offer for an inventory item using the eBay Inventory API.
    
    This is Step 2 of the listing workflow. The offer defines pricing, listing duration,
    and policies. The listing is still not live until you publish the offer.
    
    Args:
        sku (str): Seller-defined SKU value for the inventory item
        offer_data (dict): Dictionary containing offer data:
            - marketplaceId: str (e.g., "EBAY_US")
            - format: str (e.g., "FIXED_PRICE")
            - quantity: int (optional, defaults to inventory item quantity)
            - pricingSummary: dict with price.value and price.currency
            - listingDuration: str (e.g., "GTC" for Good 'Til Cancelled)
            - categoryId: str (eBay category ID)
            - listingPolicies: dict (optional):
                - fulfillmentPolicyId: str
                - paymentPolicyId: str
                - returnPolicyId: str
            - merchantLocationKey: str (optional, defaults to primary location)
        locale (str): Locale code (e.g., "en-US"). Default: "en-US"
        use_user_token (bool): If True, use user_token. Default: True
    
    Returns:
        dict: Response containing offerId and status, or None on failure
    """
    if use_user_token:
        valid_token = USER_TOKEN
        if not valid_token:
            print("❌ Error: Could not get valid user token")
            return None
    else:
        valid_token = helper_get_valid_token()
        if not valid_token:
            print("❌ Error: Could not get valid access token")
            return None
    
    url = f"{EBAY_INVENTORY_API_BASE}/offer"
    
    headers = {
        'Authorization': f'Bearer {valid_token}',
        'Content-Language': locale,
        'Content-Type': 'application/json'
    }
    
    # Add SKU to offer data
    offer_data['sku'] = sku
    
    try:
        print(f"📝 Step 2: Creating offer for SKU: {sku}")
        print(f"💰 Price: ${offer_data.get('pricingSummary', {}).get('price', {}).get('value', 'N/A')}")
        
        response = requests.post(url, headers=headers, json=offer_data, timeout=30)
        
        if response.status_code == 201:
            result = response.json()
            offer_id = result.get('offerId')
            print(f"✅ Successfully created offer")
            print(f"🆔 Offer ID: {offer_id}")
            
            # Check for warnings
            warnings = result.get('warnings', [])
            if warnings:
                print(f"⚠️ Warnings:")
                for warning in warnings:
                    print(f"   - {warning.get('message', 'Unknown warning')}")
            
            return result
        else:
            # Check if offer already exists - if so, extract the offer ID and continue
            try:
                error_data = response.json()
                errors = error_data.get('errors', [])
                
                # Check for "Offer entity already exists" error (errorId 25002)
                for error in errors:
                    if error.get('errorId') == 25002 and 'already exists' in error.get('message', ''):
                        # Extract offer ID from error parameters
                        parameters = error.get('parameters', [])
                        offer_id = None
                        for param in parameters:
                            if param.get('name') == 'offerId':
                                offer_id = param.get('value')
                                break
                        
                        if offer_id:
                            print(f"ℹ️  Offer already exists for SKU: {sku}")
                            print(f"🆔 Using existing Offer ID: {offer_id}")
                            # Return a result dict similar to successful creation
                            return {
                                'offerId': offer_id,
                                'sku': sku,
                                'existing': True
                            }
            except:
                pass  # Fall through to normal error handling
            
            handle_http_error(response, f"create_offer (SKU: {sku})")
            try:
                error_data = response.json()
                print(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Response text: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def publish_offer(offer_id, locale="en-US", use_user_token=True):
    """
    Publish an offer to make it live on eBay.
    
    This is Step 3 of the listing workflow. This makes the listing visible and
    searchable on eBay.
    
    Args:
        offer_id (str): The offer ID returned from create_offer
        locale (str): Locale code (e.g., "en-US"). Default: "en-US"
        use_user_token (bool): If True, use user_token. Default: True
    
    Returns:
        dict: Response containing listingId and status, or None on failure
    """
    if use_user_token:
        valid_token = USER_TOKEN
        if not valid_token:
            print("❌ Error: Could not get valid user token")
            return None
    else:
        valid_token = helper_get_valid_token()
        if not valid_token:
            print("❌ Error: Could not get valid access token")
            return None
    
    url = f"{EBAY_INVENTORY_API_BASE}/offer/{offer_id}/publish"
    
    headers = {
        'Authorization': f'Bearer {valid_token}',
        'Content-Language': locale,
        'Content-Type': 'application/json'
    }
    
    try:
        print(f"🚀 Step 3: Publishing offer: {offer_id}")
        response = requests.post(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            listing_id = result.get('listingId')
            print(f"✅ Successfully published offer!")
            print(f"🆔 Listing ID: {listing_id}")
            print(f"🔗 View listing: https://www.ebay.com/itm/{listing_id}")
            
            # Check for warnings
            warnings = result.get('warnings', [])
            if warnings:
                print(f"⚠️ Warnings:")
                for warning in warnings:
                    print(f"   - {warning.get('message', 'Unknown warning')}")
            
            return result
        else:
            handle_http_error(response, f"publish_offer (Offer ID: {offer_id})")
            try:
                error_data = response.json()
                print(f"Error details: {json.dumps(error_data, indent=2)}")
                
                # Check for country-related errors and provide helpful guidance
                errors = error_data.get('errors', [])
                for error in errors:
                    error_msg = error.get('message', '')
                    if 'Country' in error_msg or error.get('errorId') == 25002:
                        print("\n💡 This error usually means you need to set up Business Policies in your eBay account.")
                        print("   Business Policies include:")
                        print("   - Fulfillment Policy (shipping/country information)")
                        print("   - Payment Policy")
                        print("   - Return Policy")
                        print("\n   To set up Business Policies:")
                        print("   1. Go to: https://www.ebay.com/sh/landing")
                        print("   2. Navigate to Account > Site Preferences > Business Policies")
                        print("   3. Create policies for Fulfillment, Payment, and Returns")
                        print("   4. Then add the policy IDs to your offer_data['listingPolicies']")
                        print("\n   Example:")
                        print('   "listingPolicies": {')
                        print('       "fulfillmentPolicyId": "YOUR_FULFILLMENT_POLICY_ID",')
                        print('       "paymentPolicyId": "YOUR_PAYMENT_POLICY_ID",')
                        print('       "returnPolicyId": "YOUR_RETURN_POLICY_ID"')
                        print('   }')
            except:
                print(f"Response text: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def create_inventory_location(merchant_location_key="PlasticLoveShopLocation", location_name="PlasticLoveShopLocation", postal_code="11545", country="US", locale="en-US", use_user_token=True):
    """
    Create a new inventory location using the eBay Inventory API.
    
    This function creates a warehouse location that can be used for inventory management
    and fulfillment. The location can be referenced in offers using merchantLocationKey.
    
    Args:
        merchant_location_key (str): Unique identifier for the location (default: "PlasticLoveShopLocation")
        location_name (str): Display name for the location (default: "PlasticLoveShopLocation")
        postal_code (str): Zip code (default: "11545")
        country (str): Country code (default: "US")
        locale (str): Locale code (e.g., "en-US"). Default: "en-US"
        use_user_token (bool): If True, use user_token. Default: True
    
    Returns:
        dict: Response containing location details and status, or None on failure
    
    API Documentation:
        https://developer.ebay.com/api-docs/sell/inventory/resources/location/methods/createInventoryLocation
    """
    # Get a valid token
    if use_user_token:
        valid_token = USER_TOKEN
        if not valid_token:
            print("❌ Error: Could not get valid user token")
            print("💡 Make sure user_token is set in your .env file")
            return None
    else:
        valid_token = helper_get_valid_token()
        if not valid_token:
            print("❌ Error: Could not get valid access token")
            return None
    
    # Endpoint for creating a new inventory location
    url = f"{EBAY_INVENTORY_API_BASE}/location/{merchant_location_key}"
    
    # Headers required by eBay API
    headers = {
        'Authorization': f'Bearer {valid_token}',
        'Content-Language': locale,
        'Content-Type': 'application/json'
    }
    
    # Request body for creating a warehouse location
    location_data = {
        "location": {
            "address": {
                "postalCode": postal_code,
                "country": country
            }
        },
        "name": location_name,
        "merchantLocationStatus": "ENABLED",
        "locationTypes": ["WAREHOUSE"]
    }
    
    try:
        print(f"📍 Creating inventory location: {location_name}")
        print(f"🆔 Merchant Location Key: {merchant_location_key}")
        print(f"📮 Postal Code: {postal_code}")
        print(f"🌍 Country: {country}")
        
        response = requests.post(url, headers=headers, json=location_data, timeout=30)
        
        # According to eBay API docs, 201 (Created) is the expected success response
        if response.status_code == 201:
            result = response.json()
            print(f"✅ Successfully created inventory location")
            print(f"🆔 Location Key: {merchant_location_key}")
            print(f"📛 Name: {location_name}")
            
            # Check for warnings
            warnings = result.get('warnings', [])
            if warnings:
                print(f"⚠️ Warnings:")
                for warning in warnings:
                    print(f"   - {warning.get('message', 'Unknown warning')}")
            
            return result
        else:
            handle_http_error(response, f"create_inventory_location (Location Key: {merchant_location_key})")
            try:
                error_data = response.json()
                print(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Response text: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def upload_complete_listing(sku, inventory_item_data, offer_data, locale="en-US", use_user_token=True):
    """
    Complete workflow to upload a listing to eBay.
    
    This function performs all three steps:
    1. Create/Replace inventory item
    2. Create offer
    3. Publish offer
    
    Args:
        sku (str): Seller-defined SKU value
        inventory_item_data (dict): Data for create_ebay_listing
        offer_data (dict): Data for create_offer
        locale (str): Locale code. Default: "en-US"
        use_user_token (bool): If True, use user_token. Default: True
    
    Returns:
        dict: Final result with listing ID, or None on failure
    """
    print("=" * 60)
    print("🚀 Starting Complete eBay Listing Workflow")
    print("=" * 60)
    
    # Step 1: Create inventory item
    inventory_result = create_ebay_listing(sku, inventory_item_data, locale, use_user_token)
    if not inventory_result:
        print("❌ Failed at Step 1: Creating inventory item")
        return None
    
    print()  # Blank line for readability
    
    # Step 2: Create offer (or use existing if it already exists)
    offer_result = create_offer(sku, offer_data, locale, use_user_token)
    if not offer_result:
        print("❌ Failed at Step 2: Creating offer")
        return None
    
    offer_id = offer_result.get('offerId')
    if not offer_id:
        print("❌ No offer ID returned from create_offer")
        print(f"   Debug: offer_result keys: {list(offer_result.keys()) if offer_result else 'None'}")
        return None
    
    # Check if this was an existing offer
    if offer_result.get('existing'):
        print("✅ Using existing offer, proceeding to publish...")
    
    print()  # Blank line for readability
    
    # Step 3: Publish offer
    print(f"🔗 Passing offer_id '{offer_id}' to publish_offer()")
    publish_result = publish_offer(offer_id, locale, use_user_token)
    if not publish_result:
        print("❌ Failed at Step 3: Publishing offer")
        return None
    
    print()
    print("=" * 60)
    print("✅ Complete listing workflow successful!")
    print("=" * 60)
    
    return publish_result


def create_test_listing(locale="en-US", use_user_token=True, sku=None, listing_filename=None):
    """
    Create a test listing using data loaded from JSON files in Generated_Listings folder.
    
    This function loads test data from the Generated_Listings folder (created by combine command)
    and loads listing policies from environment variables.
    
    Args:
        locale (str): Locale code. Default: "en-US"
        use_user_token (bool): If True, use user_token. Default: True
        sku (str, optional): SKU to load. If None, uses TEST_SKU.
        listing_filename (str, optional): Specific listing filename to load. If None, finds most recent for SKU.
    
    Returns:
        dict: Final result with listing ID, or None on failure
    """
    # Use provided SKU or default
    listing_sku = sku if sku else TEST_SKU
    print(f"🚀 Publishing complete listing to eBay with SKU: {listing_sku}")
    
    # Load data from JSON file
    listing_data = load_listing_data(sku=listing_sku, filename=listing_filename)
    if not listing_data:
        print(f"❌ Failed to load listing data for SKU: {listing_sku}")
        print(f"💡 Make sure to create the listing data file first using: combine {listing_sku}")
        return None
    
    # Extract inventory and offer data from loaded JSON
    test_inventory_item_data = listing_data.get("inventoryItem", {}).copy()
    test_offer_data = listing_data.get("offer", {}).copy()
    
    # Ensure merchant location key is set
    if "merchantLocationKey" not in test_offer_data:
        test_offer_data["merchantLocationKey"] = MERCHANT_LOCATION_KEY
    
    # Use SKU from loaded data or provided/default
    actual_sku = listing_data.get("sku", listing_sku)
    
    # Add listing policies from .env if available
    policies = get_listing_policies()
    if policies:
        test_offer_data["listingPolicies"] = policies
    
    # Run the complete workflow (creates inventory item, creates offer, and publishes)
    result = upload_complete_listing(
        sku=actual_sku,
        inventory_item_data=test_inventory_item_data,
        offer_data=test_offer_data,
        locale=locale,
        use_user_token=use_user_token
    )
    
    if result:
        listing_id = result.get('listingId')
        if listing_id:
            print(f"\n🎉 Listing is now live on eBay!")
            print(f"🔗 View it at: https://www.ebay.com/itm/{listing_id}")
        else:
            print(f"✅ Listing workflow completed successfully")
    else:
        print(f"❌ Listing workflow failed. Check the error messages above.")
    
    return result


# Example usage with test data
if __name__ == "__main__":
    """
    Example: Upload a GoPro Hero4 listing to eBay
    
    This demonstrates the complete workflow with test data.
    Modify the data below to match your product and eBay account settings.
    """
    
    # Example: Create inventory location
    print("=" * 60)
    print("📍 Example: Creating Inventory Location")
    print("=" * 60)
    location_result = create_inventory_location(
        merchant_location_key=MERCHANT_LOCATION_KEY,
        location_name=MERCHANT_LOCATION_KEY,
        postal_code="11545",
        country="US"
    )
    if location_result:
        print(f"\n✅ Location created successfully!")
    else:
        print(f"\n❌ Location creation failed. Check the error messages above.")
    
    print("\n" + "=" * 60 + "\n")
    
    # Test SKU
    test_sku = "TEST-005"
    
    # Step 1: Inventory Item Data
    test_inventory_item_data = {
        "availability": {
            "shipToLocationAvailability": {
                "quantity": 12
            }
        },
        "condition": "NEW",
        "packageWeightAndSize": {
            "weight": {
                "value": "0.5",
                "unit": "POUND"
            },
            "dimensions": {
                "length": "6",
                "width": "4",
                "height": "3",
                "unit": "INCH"
            }
        },
        "product": {
            "title": "GoPro Hero4 Helmet Cam 2",
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
    
    # Step 2: Offer Data (using centralized test data from top of file)
    test_offer_data = TEST_OFFER_DATA.copy()
    test_offer_data["quantity"] = 1  # Override quantity for this example
    test_offer_data["merchantLocationKey"] = MERCHANT_LOCATION_KEY
    
    # Add listing policies from .env if available
    policies = get_listing_policies()
    if policies:
        test_offer_data["listingPolicies"] = policies
    
    # Run the complete workflow
    result = upload_complete_listing(
        sku=test_sku,
        inventory_item_data=test_inventory_item_data,
        offer_data=test_offer_data,
        locale="en-US",
        use_user_token=True
    )
    
    if result:
        print(f"\n🎉 Listing is now live on eBay!")
        listing_id = result.get('listingId')
        if listing_id:
            print(f"🔗 View it at: https://www.ebay.com/itm/{listing_id}")
    else:
        print("\n❌ Listing workflow failed. Check the error messages above.")

