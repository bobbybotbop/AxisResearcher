"""
eBay Single Functions Module

This module contains the singleSearch function and related dependencies
extracted from main_ebay_commands.py for better code organization.
"""

import os
import requests
import json
from dotenv import load_dotenv
from helper_functions import helper_get_valid_token, refreshToken

# Load environment variables
load_dotenv()

# Constants
ZIP_CODE = 14853
API_KEY = os.getenv('api_key')
CLIENT_ID = os.getenv('client_id')
CLIENT_SECRET = os.getenv('client_secret')
USER_TOKEN = os.getenv('user_token')
REFRESH_TOKEN = os.getenv('refresh_token')


def singleSearch(query):
    """
    Search for items on eBay using the Browse API.
    
    Args:
        query (str): Search query string
    
    Returns:
        None: Prints search results to console
    """
    # Get a valid token, refresh if needed
    valid_token = helper_get_valid_token()
    
    if not valid_token:
        print("❌ Error: Could not get valid access token")
        return

    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

    # Headers for Browse API
    headers = {
        'X-EBAY-C-ENDUSERCTX': f'contextualLocation=country=US,zip={ZIP_CODE}',
        'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US',
        'Authorization': f'Bearer {valid_token}',
        'Content-Type': 'application/json'
    }

    # Parameters for Browse API
    params = {
        'q': query,
        'limit': 10,
        'offset': 0,
        'fieldgroups': 'EXTENDED',  # Get additional item details
        'sort': 'BEST_MATCH',  # Sort by best match
        'filter': 'buyingOptions:{FIXED_PRICE}'  # Only show Buy It Now items
    }

    # Make request with headers
    try:
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            """Parse and display the API response"""
            data = response.json()
            print("✅ Success! Browse API Response:")
            
            # Extract key information from Browse API response
            total = data.get('total', 0)
            items = data.get('itemSummaries', [])
            
            print(f"Total items found: {total}")
            print(f"Items returned: {len(items)}")
            print("\nFirst few items:")
            
            for i, item in enumerate(items[:3]):  # Show first 3 items
                print(f"\nItem {i+1}:")
                print(f"  Title: {item.get('title', 'N/A')}")
                print(f"  Price: {item.get('price', {}).get('value', 'N/A')} {item.get('price', {}).get('currency', '')}")
                print(f"  Condition: {item.get('condition', 'N/A')}")
                print(f"  Seller: {item.get('seller', {}).get('username', 'N/A')}")
                print(f"  Item URL: {item.get('itemWebUrl', 'N/A')}")
            
            print(f"\nFull response structure:")
            print(f"Keys in response: {list(data.keys())}")
            
        elif response.status_code == 401:
            print("🔄 Token expired, refreshing...")
            # new_token = refreshToken()
            if new_token:
                # Retry the request with new token
                headers['Authorization'] = f'Bearer {new_token}'
                response = requests.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    parse(response)
                else:
                    print(f"❌ Still failed after refresh: {response.status_code}")
            else:
                print("❌ Could not refresh token")
        else:
            print(f"❌ Error occurred: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"Error parsing JSON: {e}")
        print("Raw response:")
        print(response.text)


def single_search_by_seller(seller_username, query="", limit=50, offset=0):
    """
    Search for all items from a specific eBay seller/store.
    
    Args:
        seller_username (str): The eBay username of the seller
        query (str): Optional keyword search to filter within seller's items
        limit (int): Number of items to return (max 200)
        offset (int): Offset for pagination
    
    Returns:
        dict: Search results with items from the specified seller
    """
    # Get a valid token, refresh if needed
    valid_token = helper_get_valid_token()
    
    if not valid_token:
        print("❌ Error: Could not get valid access token")
        return None
    
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    
    # Headers for Browse API
    headers = {
        'X-EBAY-C-ENDUSERCTX': f'contextualLocation=country=US,zip={ZIP_CODE}',
        'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US',
        'Authorization': f'Bearer {valid_token}',
        'Content-Type': 'application/json'
    }
    
    # Parameters for Browse API with seller filter
    params = {
        'limit': min(limit, 200),  # Max 200 per request
        'offset': offset,
        'fieldgroups': 'EXTENDED',
        'sort': 'BEST_MATCH',
        'filter': f'sellers:{{{seller_username}}}'  # Filter by specific seller
    }
    
    # Add keyword search if provided
    if query:
        params['q'] = query
    
    try:
        print(f"🔍 Searching items from seller: {seller_username}")
        if query:
            print(f"🔍 With keyword filter: {query}")
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            items = data.get('itemSummaries', [])
            print(data)
            print(f"✅ Found {total} total items from {seller_username}")
            print(f"📦 Retrieved {len(items)} items in this response")
            
            # Display first few items
            if items:
                print(f"\n📋 First few items from {seller_username}:")
                for i, item in enumerate(items[:5]):  # Show first 5 items
                    print(f"\nItem {i+1}:")
                    print(f"  Title: {item.get('title', 'N/A')}")
                    print(f"  Price: {item.get('price', {}).get('value', 'N/A')} {item.get('price', {}).get('currency', '')}")
                    print(f"  Condition: {item.get('condition', 'N/A')}")
                    print(f"  Item ID: {item.get('itemId', 'N/A')}")
                    print(f"  Item URL: {item.get('itemWebUrl', 'N/A')}")
            
            return {
                'total_items': total,
                'items': items,
                'seller': seller_username,
                'query': query,
                'has_more': len(items) < total
            }
            
        elif response.status_code == 401:
            print("🔄 Token expired, refreshing...")
            # new_token = refreshToken()
            if new_token:
                # Retry with new token
                headers['Authorization'] = f'Bearer {new_token}'
                response = requests.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    return single_search_by_seller(seller_username, query, limit, offset)
            print("❌ Could not refresh token")
            return None
        else:
            print(f"❌ Error occurred: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error searching by seller: {e}")
        return None
