"""
eBay Browse API Test Script

This script uses the eBay Browse API to search for items.
The Browse API requires OAuth authentication (user token), unlike the Finding API.

Required environment variables:
- api_key: Your eBay App ID
- user_token: Your OAuth user token (obtained through OAuth flow)

API Documentation: https://developer.ebay.com/api-docs/buy/browse/resources/item_summary/methods/search
"""

import os
import base64
from dotenv import load_dotenv, set_key
import requests
import json
import time
from datetime import datetime
import sys
import re


load_dotenv()
API_KEY = os.getenv('api_key')
CLIENT_ID = os.getenv('client_id')
CLIENT_SECRET = os.getenv('client_secret')
USER_TOKEN = os.getenv('user_token')
REFRESH_TOKEN = os.getenv('refresh_token')
OPENROUTER_API_KEY = os.getenv('openrouter_api_key')


def call_openrouter_llm(prompt):
    """Call OpenRouter Sonoma Sky Alpha API to generate optimized eBay listing content."""
    if not OPENROUTER_API_KEY:
        print("❌ OpenRouter API key not found. Please set OPENROUTER_API_KEY in your .env file")
        return None
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    
    data = {
        "model": "openrouter/sonoma-sky-alpha",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        print("🤖 Calling OpenRouter Sonoma Sky Alpha...")
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content']
            print("✅ Received response from OpenRouter")
            return content
        else:
            print("❌ Unexpected response format from OpenRouter")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error calling OpenRouter API: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing OpenRouter response: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def remove_html_tags(text):
    """Efficiently remove HTML tags from text using regex."""
    if not text or not isinstance(text, str):
        return text
    
    # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', '', text)
    
    # Decode common HTML entities
    html_entities = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
        '&nbsp;': ' '
    }
    
    for entity, replacement in html_entities.items():
        clean_text = clean_text.replace(entity, replacement)
    
    # Clean up extra whitespace
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    return clean_text

ZIP_CODE = 14853
# HELPER functions ===========================
def helper_get_valid_token():
    """Get a valid access token, refresh if needed"""
    if not USER_TOKEN:
        print("❌ No user token available")
        print("🔄 Attempting to refresh access token...")
        new_token = refreshToken()
        return new_token
    else:
        return USER_TOKEN

# Add this helper function near the top with your other helper functions (around line 29)

def handle_http_error(response, context=""):
    """
    Handle HTTP error responses with specific messages and suggestions.
    
    Args:
        response: requests.Response object
        context (str): Additional context for the error (e.g., item ID, operation)
    
    Returns:
        None
    """
    status_code = response.status_code
    
    if status_code == 401:
        print(f"❌ Authentication failed {context}")
        print("💡 Token may be expired or invalid")
    elif status_code == 403:
        print(f"❌ Access forbidden {context}")
        print("💡 Check if you have permission to access this resource")
    elif status_code == 404:
        print(f"❌ Resource not found {context}")
        print("💡 Item may have been removed or ID is incorrect")
    elif status_code == 429:
        print(f"❌ Rate limit exceeded {context}")
        print("💡 Too many requests - please wait before trying again")
    elif status_code >= 500:
        print(f"❌ Server error ({status_code}) {context}")
        print("💡 eBay servers are experiencing issues")
    else:
        print(f"❌ Unexpected error ({status_code}) {context}")
    

def refreshToken():

    import webbrowser
    webbrowser.open("https://developer.ebay.com/my/auth/?env=production&index=0")
    # """
    # Open eBay OAuth link and update user token with user input.
    # """
    # import webbrowser
    
    # # Open eBay OAuth authorization URL
    # oauth_url = "https://developer.ebay.com/my/auth/?env=production&index=0"
    # print(refresh_token)
    # print(f"📱 Please complete the OAuth flow and copy your user token")
    
    # # Get new user token from user input
    # if refresh_token is None:
    #     webbrowser.open(oauth_url)
    #     new_user_token = input("Enter your new user token: ").strip()
    #     if not new_user_token:
    #         print("❌ User token is required")
    #         return None
    # else:
    #     new_user_token = refresh_token
    #     print(f"Using provided user token: {refresh_token[:20]}...")
    
    # # Update the user token in .env file
    # set_key('.env', 'user_token', new_user_token)
    # print(f"✅ User token updated successfully!")
    # print(f"New token: {new_user_token[:20]}...")
    
    # return new_user_token

# SINGLE functions ===========================


def singleSearch(query):
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

        # print(f"Status Code: {response.status_code}")
        # print(f"Response Headers: {dict(response.headers)}")

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
                    return search_by_seller(seller_username, query, limit, offset)
            print("❌ Could not refresh token")
            return None
        else:
            print(f"❌ Error occurred: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error searching by seller: {e}")
        return None

def single_get_detailed_item_data(item_id, verbose=True):
    """
    Get detailed sales data for a specific item including estimatedSoldQuantity
    
    Args:
        item_id (str): The eBay item ID (e.g., "v1|123456789|0")
        verbose (bool): If True, prints detailed information. Default: False (echo off)
    
    Returns:
        dict: Item details including estimated sales data
    """

    if item_id[0] != 'v':
        item_id = "v1|" + item_id + "|0"
 
    # Get a valid token
    valid_token = helper_get_valid_token()
    if not valid_token:
        print("❌ Error: Could not get valid access token")
        return None
    
    url = f"https://api.ebay.com/buy/browse/v1/item/{item_id}"
    
    headers = {
        'X-EBAY-C-ENDUSERCTX': f'contextualLocation=country=US,zip={ZIP_CODE}',
        'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US',
        'Authorization': f'Bearer {valid_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        if verbose:
            print(f"🔍 Fetching sales data for item: {item_id}")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            item = response.json()
            
            if verbose:
                print(f"✅ Item Details Retrieved:")
            # print(f"Title: {item.get('title', 'N/A')}")
            # print(f"Price: ${item.get('price', {}).get('value', 'N/A')} {item.get('price', {}).get('currency', '')}")
            # print(f"Seller: {item.get('seller', {}).get('username', 'N/A')}")
            
            # Extract estimated sales data
            estimated_availabilities = item.get('estimatedAvailabilities', [])
            
            if estimated_availabilities: # might cause error later
                if verbose:
                    print(f"\n📊 Sales Data:")
                for i, availability in enumerate(estimated_availabilities):
                    estimated_sold = availability.get('estimatedSoldQuantity')
                    estimated_available = availability.get('estimatedAvailableQuantity')
                    
                    item_title = item.get('title', 'N/A')
                    if verbose:
                        print(f"Title: {item_title}")
                    if estimated_sold is not None:
                        if verbose:
                            print(f"    Estimated Sold: {estimated_sold} units")
                    else:
                        if verbose:
                            print(f"    Estimated Sold: Not available")
                    
                    if estimated_available is not None:
                        if verbose:
                            print(f"    Estimated Available: {estimated_available} units")
            
            # Get price information
            price_info = item.get('price', {})
            price_value = price_info.get('value', 'N/A')
            currency = price_info.get('currency', 'USD')
            formatted_price = f"${price_value} {currency}" if price_value != 'N/A' else 'N/A'
            
            # Get description (shortDescription or description) and remove HTML
            description = item.get('description') or item.get('description', 'No description available')
            description = remove_html_tags(description)
            
            # Get date (item creation date)
            item_creation_date = item.get('itemCreationDate', 'N/A')
            
            # Get number of pictures
            images = item.get('image', {})
            image_urls = images.get('imageUrl', []) if isinstance(images.get('imageUrl'), list) else [images.get('imageUrl')] if images.get('imageUrl') else []
            number_of_pictures = len([url for url in image_urls if url])
            
            # Get thumbnail URL
            thumbnail_url = images.get('thumbnailUrl') or images.get('imageUrl') if isinstance(images.get('imageUrl'), str) else (image_urls[0] if image_urls else 'N/A')
            
            return {
                'item_id': item_id,
                'title': item_title,
                'description': description,
                'date': item_creation_date,
                'numbersold': estimated_availabilities[0].get('estimatedSoldQuantity') if estimated_availabilities else None,
                'price': formatted_price,
                'numberOfPictures': number_of_pictures,
                'thumbnailURL': thumbnail_url
            }
            
        else:
            handle_http_error(response, "single_get_detailed_item_data")
    except Exception as e:
        print(f"❌ Error fetching item sales data: {e}")
        return None

def getItemIds(seller_username, query=" ", limit_per_request=200,save_to_file=True, filename="IDExport"):
    

    """
    Get all item IDs from a specific eBay seller with pagination and rate limiting.
    
    Args:
        seller_username (str): The eBay username of the seller
        query (str): Optional keyword search to filter within seller's items
        limit_per_request (int): Number of items per request (max 200)
    
    Returns:
        list: Array of all item IDs from the seller
    """
    import time
    
    all_item_ids = []
    offset = 0
    total_found = 0
    request_count = 0
    
    print(f"�� Collecting all item IDs from seller: {seller_username}")
    if query:
        print(f"🔍 With keyword filter: {query}")
    
    while True:
        # Get a valid token for each request
        valid_token = helper_get_valid_token()
        
        if not valid_token:
            print("❌ Error: Could not get valid access token")
            return all_item_ids
        
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
            'limit': limit_per_request,
            'offset': offset,
            'fieldgroups': 'EXTENDED',
            'sort': 'BEST_MATCH',
            'filter': f'sellers:{{{seller_username}}}'  # Filter by specific seller
        }
        
        # Add keyword search if provided
        if query:
            params['q'] = query
        
        try:
            request_count += 1
            print(f"\n📦 Request #{request_count} - Offset: {offset}, Limit: {limit_per_request}")
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                total = data.get('total', 0)
                items = data.get('itemSummaries', [])
                
                # Update total found on first request
                if offset == 0:
                    total_found = total
                    print(f"✅ Total items available: {total_found}")
                
                print(f"📦 Retrieved {len(items)} items in this request")
                
                # Extract item IDs
                batch_item_ids = []
                for item in items:
                    item_id = item.get('itemId')
                    if item_id:
                        batch_item_ids.append(item_id)
                        all_item_ids.append(item_id)
                
                print(f"🆔 Collected {len(batch_item_ids)} item IDs in this batch")
                print(f"📊 Total item IDs collected so far: {len(all_item_ids)}")
                
                # Check if we've got all items
                if len(items) < limit_per_request or len(all_item_ids) >= total_found:
                    print(f"✅ Completed! Collected all {len(all_item_ids)} item IDs")
                    break
                
                # Update offset for next request
                offset += limit_per_request
                
                # Pause between requests to avoid rate limiting
                print(f"⏳ Pausing .1 seconds before next request...")
                time.sleep(.1)
                
            elif response.status_code == 401:
                print("🔄 Token expired, refreshing...")
                # new_token = refreshToken()
                if new_token:
                    # Retry with new token
                    headers['Authorization'] = f'Bearer {new_token}'
                    response = requests.get(url, headers=headers, params=params)
                    if response.status_code == 200:
                        # Process the response
                        data = response.json()
                        items = data.get('itemSummaries', [])
                        
                        batch_item_ids = []
                        for item in items:
                            item_id = item.get('itemId')
                            if item_id:
                                batch_item_ids.append(item_id)
                                all_item_ids.append(item_id)
                        
                        print(f"🆔 Collected {len(batch_item_ids)} item IDs in this batch")
                        print(f"📊 Total item IDs collected so far: {len(all_item_ids)}")
                        
                        if len(items) < limit_per_request:
                            print(f"✅ Completed! Collected all {len(all_item_ids)} item IDs")
                            break
                        
                        offset += limit_per_request
                        print(f"⏳ Pausing .1 seconds before next request...")
                        time.sleep(.1)
                        continue
                print("❌ Could not refresh token")
                break
            else:
                print(f"❌ Error occurred: {response.status_code}")
                print(f"Response: {response.text}")
                break
                
        except Exception as e:
            print(f"❌ Error in request #{request_count}: {e}")
            break
    
    print(f"\n📊 Final Summary:")
    print(f"Total requests made: {request_count}")
    print(f"Total item IDs collected: {len(all_item_ids)}")
    print(f"Seller: {seller_username}")
    if query:
        print(f"Query filter: {query}")
    
    # Save to file if requested
    if save_to_file and all_item_ids:
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_seller = seller_username.replace(" ", "_").replace("/", "_")
            if query:
                safe_query = query.replace(" ", "_").replace("/", "_")
                filename = f"item_ids_{safe_seller}_{safe_query}_{timestamp}.json"
            else:
                filename = f"item_ids_{safe_seller}_{timestamp}.json"
        
        # Prepare data to save
        save_data = {
            'seller_username': seller_username,
            'query': query,
            'total_items': len(all_item_ids),
            'collection_date': datetime.now().isoformat(),
            'total_requests_made': request_count,
            'item_ids': all_item_ids
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Item IDs saved to: {filename}")
            print(f"📁 File contains {len(all_item_ids)} item IDs")
            
        except Exception as e:
            print(f"❌ Error saving to file: {e}")
    
    return all_item_ids
def processSalesExportFromFile(input_filename, output_filename):
    """
    Load item IDs from IDExport.json, get sales data for each item, sort by estimated sold quantity,
    and export the sorted data to SalesExport.json.
    
    Args:
        input_filename (str): Name of the file containing item IDs (default: IDExport.json)
        output_filename (str): Name of the output file for sales data (default: SalesExport.json)
    
    Returns:
        list: Sorted list of items with sales data
    """
    print(f"📁 Loading item IDs from: {input_filename}")
    
    # Load item IDs from file
    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        item_ids = data.get('item_ids', [])
        seller_username = data.get('seller_username', 'Unknown')
        query = data.get('query', '')
        
        print(f"✅ Loaded {len(item_ids)} item IDs from {seller_username}")
        if query:
            print(f"Query filter: {query}")
            
    except FileNotFoundError:
        print(f"❌ File not found: {input_filename}")
        return []
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON file: {input_filename}")
        return []
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return []
    
    if not item_ids:
        print("❌ No item IDs found in file")
        return []
    
    print(f"\n📊 Fetching sales data for {len(item_ids)} items...")
    
    # Process items one by one to get sales data
    all_sales_data = []
    processed_count = 0
    
    for i, item_id in enumerate(item_ids):
        processed_count += 1
        
        # Get sales data for this single item
        item_data = single_get_detailed_item_data(item_id)

        #show progress
        print(f"📦 Processing item {processed_count}/{len(item_ids)} ({processed_count/len(item_ids)*100:.1f}%)")
        
        if item_data:
            all_sales_data.append(item_data)
        
    
    print(f"\n📊 Sales Data Collection Complete:")
    print(f"Total items processed: {len(item_ids)}")
    print(f"Items with sales data: {len(all_sales_data)}")
    
    # Sort by estimated sold quantity (highest first)
    print(f"\n🔄 Sorting items by estimated sold quantity...")
    
    # Filter items that have sales data and sort
    items_with_sales = [item for item in all_sales_data if item.get('numbersold') is not None]
    items_without_sales = [item for item in all_sales_data if item.get('numbersold') is None]
    
    # Sort by estimated sold quantity (descending)
    sorted_items = sorted(items_with_sales, key=lambda x: x.get('numbersold', 0), reverse=True)
    
    # Add items without sales data at the end
    final_sorted_list = sorted_items + items_without_sales
    
    print(f"✅ Sorted {len(sorted_items)} items with sales data")
    print(f"📊 {len(items_without_sales)} items without sales data")
    
    # Display top 10 items
    print(f"\n🏆 Top 10 Best Selling Items:")
    for i, item in enumerate(sorted_items[:10]):
        sold_qty = item.get('numbersold', 0)
        title = item.get('title', 'N/A')[:50]
        price = item.get('price', 'N/A')
        print(f"  {i+1:2d}. {sold_qty:3d} sold - {price} - {title}...")
    
    # Prepare export data
    export_data = {
        'source_file': input_filename,
        'seller_username': seller_username,
        'query': query,
        'total_items_processed': len(item_ids),
        'items_with_sales_data': len(sorted_items),
        'items_without_sales_data': len(items_without_sales),
        'export_date': datetime.now().isoformat(),
        'sorted_by': 'numbersold_desc',
        'items': final_sorted_list
    }
    
    # Export to file
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n Sales data exported to: {output_filename}")
        print(f"📁 File contains {len(final_sorted_list)} items sorted by estimated sold quantity")
        
        # Display summary statistics
        if sorted_items:
            total_sold = sum(item.get('numbersold', 0) for item in sorted_items)
            avg_sold = total_sold / len(sorted_items)
            max_sold = max(item.get('numbersold', 0) for item in sorted_items)
            
            print(f"\n Sales Summary:")
            print(f"  Total estimated units sold: {total_sold}")
            print(f"  Average sold per item: {avg_sold:.1f}")
            print(f"  Highest selling item: {max_sold} units")
        
        return final_sorted_list
        
    except Exception as e:
        print(f"❌ Error saving export file: {e}")
        return final_sorted_list


    """
    Get the top N selling items from a processed sales export file.
    
    Args:
        input_filename (str): Name of the file containing processed sales data (SalesExport.json)
        top_n (int): Number of top items to return
        output_filename (str): Name of the output file (optional)
    
    Returns:
        list: Top N selling items
    """
    if not output_filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"Top{top_n}Sales_{timestamp}.json"
    
    print(f"🏆 Getting top {top_n} selling items from {input_filename}...")
    
    # Load the processed sales data
    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        all_items = data.get('items', [])
        seller_username = data.get('seller_username', 'Unknown')
        
        print(f"✅ Loaded {len(all_items)} items from {seller_username}")
        
    except FileNotFoundError:
        print(f"❌ File not found: {input_filename}")
        print(f"💡 Make sure you've run processSalesExportFromFile() first to create {input_filename}")
        return []
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON file: {input_filename}")
        return []
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return []
    
    if not all_items:
        print("❌ No items found in file")
        return []
    
    # Get top N items with sales data (they're already sorted)
    items_with_sales = [item for item in all_items if item.get('numbersold') is not None]
    top_items = items_with_sales[:top_n]
    
    print(f"📊 Found {len(items_with_sales)} items with sales data")
    print(f"🏆 Selecting top {min(top_n, len(top_items))} items")
    
    # Prepare top items data
    top_items_data = {
        'source_file': input_filename,
        'seller_username': seller_username,
        'total_items_available': len(all_items),
        'items_with_sales_data': len(items_with_sales),
        'top_n': top_n,
        'export_date': datetime.now().isoformat(),
        'top_items': top_items
    }
    
    # Export top items
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(top_items_data, f, indent=2, ensure_ascii=False)
        
        print(f" Top {top_n} items exported to: {output_filename}")
        
        # Display top items summary
        if top_items:
            total_sold = sum(item.get('numbersold', 0) for item in top_items)
            print(f"\n Top {top_n} Summary:")
            print(f"  Total estimated units sold: {total_sold}")
            print(f"  Average sold per item: {total_sold/len(top_items):.1f}")
            
            # Show top 5 items
            print(f"\n🏆 Top 5 Items:")
            for i, item in enumerate(top_items[:5]):
                sold_qty = item.get('numbersold', 0)
                title = item.get('title', 'N/A')[:40]
                price = item.get('price', 'N/A')
                print(f"  {i+1}. {sold_qty:3d} sold - {price} - {title}...")
        
        return top_items
        
    except Exception as e:
        print(f"❌ Error saving top items file: {e}")
        return top_items

def getTopSellingItems(input_filename="SalesExport.json", top_n=50, pastDays = 9999):
    
   

def getByRatio(input_filename="SalesExport.json"):


def singleCopyListing(id):
    if (id[0] == 'h' or id[0] == 'e'):
        id = id.split('/itm/')[1].split('?')[0]

    listing = single_get_detailed_item_data(id, verbose = False)

    if listing:
        print("📦 Listing Details:")
        print(f"   Item ID: {listing.get('item_id', 'N/A')}")
        print(f"   Title: {listing.get('title', 'N/A')}")
        print(f"   Description: {listing.get('description', 'N/A')}")
        print(f"   Date: {listing.get('date', 'N/A')}")
        print(f"   Number Sold: {listing.get('numbersold', 'N/A')}")
        print(f"   Price: {listing.get('price', 'N/A')}")
        print(f"   Number of Pictures: {listing.get('numberOfPictures', 'N/A')}")
        print(f"   Thumbnail URL: {listing.get('thumbnailURL', 'N/A')}")
    else:
        print("❌ No listing data available")
    
    prompt = f"""
You are an expert eBay SEO copywriter. Rewrite the item's title and description.

Requirements
- Title: ≤80 characters, include high-intent keywords users search for. Do not add the phrases "3D printed" or "PETG" to the title unless they are already present in the original title. Preserve important specifics (brand/model/size/color) if present. Use normal capitalization, no ALL CAPS, no emojis, no quotes, no color specification in the title. continiously adding keywords relating to the product until you are most close to 80 characters.
- Description: keyword-rich but human-readable. Please add to the description by adding keywords relating to the product which are most commonly searched. Explicitly state the material is PETG. State that the product comes in black. Remove any mentions of who it is made by or the maker/manufacturer name. please format the description in modern, simple, and clean HTML and feel free to use clear list, no shipping info.


Output format (strict JSON):
{{
  "edited_title": "...",
  "edited_description": "..."
}}

Original title:
{listing.get('title', '')}

Original description:
{listing.get('description', '')}
"""
    
    # Call OpenRouter API to get optimized content
    llm_response = call_openrouter_llm(prompt)
    
    if llm_response:
        try:
            # Parse JSON response
            optimized_content = json.loads(llm_response)
            
            print("\n🎯 Optimized eBay Listing:")
            print("=" * 50)
            print(f"📝 Optimized Title ({len(optimized_content.get('edited_title', ''))} chars):")
            print(f"   {optimized_content.get('edited_title', 'N/A')}")
            print(f"\n📄 Optimized Description:")
            print(f"   {optimized_content.get('edited_description', 'N/A')}")
            print("=" * 50)
            
            return optimized_content
            
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing LLM response as JSON: {e}")
            print(f"Raw response: {llm_response}")
            return None
    else:
        print("❌ Failed to get response from OpenRouter")
        return None
            

def run_command(command, *args):
    """Command runner for eBay API functions"""
    command = command.lower()
    
    try:
        if command == "search":
            if not args: raise ValueError("Usage: search <query>")
            print(f"🔍 Searching for: {args[0]}")
            singleSearch(args[0])
            
        elif command == "seller":
            if not args: raise ValueError("Usage: seller <username> [query] [limit]")
            seller, query, limit = args[0], args[1] if len(args) > 1 else "", int(args[2]) if len(args) > 2 else 50
            print(f"🔍 Searching seller: {seller}")
            single_search_by_seller(seller, query, limit)
            
        elif command == "item":
            if not args: raise ValueError("Usage: item <item_id>")
            print(f"📦 Getting item data: {args[0]}")
            result = single_get_detailed_item_data(args[0])
            if result:
                print(f"✅ Title: {result.get('title', 'N/A')}")
                print(f"💰 Price: {result.get('price', 'N/A')}")
                print(f"📊 Sold: {result.get('numbersold', 'N/A')}")
                print(f"📅 Date: {result.get('date', 'N/A')}")
                
        elif command == "collect":
            if not args: raise ValueError("Usage: collect <seller_username> [query] [limit]")
            seller, query, limit = args[0], args[1] if len(args) > 1 else " ", int(args[2]) if len(args) > 2 else 200
            print(f"📦 Collecting from: {seller}")
            getItemIds(seller, query, limit)
            
        elif command == "process":
            input_file, output_file = args[0] if args else "IDExport.json", args[1] if len(args) > 1 else "SalesExport.json"
            print(f"📊 Processing: {input_file} -> {output_file}")
            processSalesExportFromFile(input_file, output_file)
            
        elif command == "top":
            input_file, top_n, output_file = args[0] if args else "SalesExport.json", int(args[1]) if len(args) > 1 else 50, args[2] if len(args) > 2 else None
            print(f"🏆 Top {top_n} from: {input_file}")
            getTopSellingItems(input_file, top_n, output_file)
            
        elif command == "copy":
            if not args: raise ValueError("Usage: copy <item_id_or_link>")
            print(f"�� Copying: {args[0]}")
            singleCopyListing(args[0])
            
        elif command == "refresh":
            refreshToken()
            
        else:
            print("❌ Available commands: search, seller, item, collect, process, top, copy, refresh [token]")
            
    except ValueError as e:
        print(f"❌ {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("❌ Usage: python ebay_search_test.py <command> [args...]")
        print("Commands: search, seller, item, collect, process, top, copy, refresh [token]")
        sys.exit(1)
    
    run_command(sys.argv[1], *sys.argv[2:])
