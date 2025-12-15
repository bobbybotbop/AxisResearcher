"""
eBay Browse API Test Script

This script uses the eBay Browse API to search for items.
The Browse API requires OAuth authentication (user token), unlike the Finding API.

Required environment variables:
- api_key: Your eBay App ID
- application_token: Your OAuth application token (obtained through OAuth flow)

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
import importlib.util

# Import single_functions module (handles unused folder - keeping dynamic import for now)
single_functions_spec = importlib.util.spec_from_file_location("single_functions", "unused/single_functions.py")
single_functions_module = importlib.util.module_from_spec(single_functions_spec)
single_functions_spec.loader.exec_module(single_functions_module)
singleSearch = single_functions_module.singleSearch
single_search_by_seller = single_functions_module.single_search_by_seller

from helper_functions import remove_html_tags, helper_get_valid_token, handle_http_error, refreshToken

# Import from copyScripts package
from copyScripts.upload_to_ebay import upload_complete_listing, create_inventory_location, create_test_listing
from copyScripts.create_text import create_text
from copyScripts.CopyListingMain import copy_listing_main
from copyScripts.create_image import generate_image_from_urls, decode_image_from_response, upload_image_to_ebay, ImageType
from copyScripts.combine_data import create_listing_with_preferences, get_item_aspects_for_category

# Keep alias for backward compatibility
create_inventory_and_offer_listing = create_listing_with_preferences


load_dotenv()
API_KEY = os.getenv('api_key')
CLIENT_ID = os.getenv('client_id')
CLIENT_SECRET = os.getenv('client_secret')
APPLICATION_TOKEN = os.getenv('application_token')
USER_TOKEN = os.getenv('user_token')
REFRESH_TOKEN = os.getenv('refresh_token')
OPENROUTER_API_KEY = os.getenv('openrouter_api_key')

ZIP_CODE = 14853


def call_openrouter_llm(prompt):
    """Call OpenRouter DeepSeek R1 0528 API to generate optimized eBay listing content."""
    if not OPENROUTER_API_KEY:
        print("❌ OpenRouter API key not found. Please set OPENROUTER_API_KEY in your .env file")
        return None
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    
    data = {
        "model": "deepseek/deepseek-r1-0528",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
    }
    
    try:
        print("🤖 Calling OpenRouter deepseek-r1-0528...")
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


def single_get_detailed_item_data(item_id, verbose=True):
    """
    Get complete detailed data for a specific item from eBay API
    
    Args:
        item_id (str): The eBay item ID (e.g., "v1|123456789|0")
        verbose (bool): If True, prints detailed information. Default: True
    
    Returns:
        dict: Complete item data from eBay API
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
            print(f"🔍 Fetching complete item data for: {item_id}")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            item = response.json()
            
            if verbose:
                print(f"✅ Complete Item Data Retrieved:")
                print(f"   Title: {item.get('title', 'N/A')}")
                print(f"   Price: ${item.get('price', {}).get('value', 'N/A')} {item.get('price', {}).get('currency', '')}")
                print(f"   Seller: {item.get('seller', {}).get('username', 'N/A')}")
                
                # Show estimated sales data if available
                estimated_availabilities = item.get('estimatedAvailabilities', [])
                if estimated_availabilities:
                    print(f"\n📊 Sales Data:")
                    for i, availability in enumerate(estimated_availabilities):
                        estimated_sold = availability.get('estimatedSoldQuantity')
                        estimated_available = availability.get('estimatedAvailableQuantity')
                        
                        if estimated_sold is not None:
                            print(f"    Estimated Sold: {estimated_sold} units")
                        else:
                            print(f"    Estimated Sold: Not available")
                        
                        if estimated_available is not None:
                            print(f"    Estimated Available: {estimated_available} units")
            
            # Return the complete item object
            return item
            
        else:
            handle_http_error(response, "single_get_detailed_item_data")
            return None
    except Exception as e:
        print(f"❌ Error fetching item data: {e}")
        return None

def getItemIds(seller_username, query=" ", limit_per_request=200):
    
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
    
    # Always save to file
    if all_item_ids:
        # Create Collected-Data folder if it doesn't exist
        collected_data_folder = "Collected-Data"
        if not os.path.exists(collected_data_folder):
            os.makedirs(collected_data_folder)
            print(f"📁 Created folder: {collected_data_folder}")
        
        # Create folder for seller if it doesn't exist
        safe_seller = seller_username.replace(" ", "_").replace("/", "_").replace("\\", "_")
        seller_folder = os.path.join(collected_data_folder, safe_seller)
        
        if not os.path.exists(seller_folder):
            os.makedirs(seller_folder)
            print(f"📁 Created folder: {seller_folder}")
        
        # Generate filename with seller username and date
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(seller_folder, f"{safe_seller}_{timestamp}.json")
        
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

def find_newest_seller_file(seller_username):
    """
    Find the newest file for a specific seller.
    
    Args:
        seller_username (str): The eBay username of the seller
    
    Returns:
        str: Path to the newest file, or None if no files found
    """
    import glob
    
    # Create safe seller name for folder matching
    safe_seller = seller_username.replace(" ", "_").replace("/", "_").replace("\\", "_")
    
    # Look for files in the seller's folder within Collected-Data
    pattern = f"Collected-Data/{safe_seller}/{safe_seller}_*.json"
    files = glob.glob(pattern)
    
    if not files:
        # Also check for files without the seller folder structure in Collected-Data
        pattern = f"Collected-Data/{safe_seller}_*.json"
        files = glob.glob(pattern)
    
    if not files:
        # Fallback: check old location (for backward compatibility)
        pattern = f"{safe_seller}/{safe_seller}_*.json"
        files = glob.glob(pattern)
    
    if not files:
        print(f"❌ No files found for seller: {seller_username}")
        print(f"💡 Make sure you've run 'collect' command first to gather item IDs")
        return None
    
    # Sort files by modification time (newest first)
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    newest_file = files[0]
    print(f"📁 Found newest file for {seller_username}: {newest_file}")
    
    return newest_file

def processSalesExportFromFile(seller_username=None, output_filename=None, limit=None):
    """
    Process sales data for a seller by finding their newest item ID file and generating sales export.
    
    Args:
        seller_username (str): The eBay username of the seller (required)
        output_filename (str): Name of the output file for sales data (optional, auto-generated if not provided)
        limit (int): Maximum number of item IDs to process (optional, processes all if not specified)
    
    Returns:
        list: Sorted list of items with sales data
    """
    if not seller_username:
        print("❌ Error: seller_username is required")
        print("💡 Usage: process <seller_username> [limit] [output_filename]")
        return []
    
    # Find the newest file for this seller
    input_filename = find_newest_seller_file(seller_username)
    if not input_filename:
        return []
    
    # Generate output filename and folder structure
    safe_seller = seller_username.replace(" ", "_").replace("/", "_").replace("\\", "_")
    
    # Create Collected-Data folder if it doesn't exist
    collected_data_folder = "Collected-Data"
    if not os.path.exists(collected_data_folder):
        os.makedirs(collected_data_folder)
        print(f"📁 Created folder: {collected_data_folder}")
    
    # Create seller folder if it doesn't exist
    seller_folder = os.path.join(collected_data_folder, safe_seller)
    if not os.path.exists(seller_folder):
        os.makedirs(seller_folder)
        print(f"📁 Created seller folder: {seller_folder}")
    
    # Create processed-sales-data subfolder
    processed_folder = os.path.join(seller_folder, "processed-sales-data")
    if not os.path.exists(processed_folder):
        os.makedirs(processed_folder)
        print(f"📁 Created processed-sales-data folder: {processed_folder}")
    
    # Generate filename based on input filename
    if not output_filename:
        # Extract the base filename from input_filename and add PROCESSED prefix
        input_basename = os.path.basename(input_filename)
        # Remove the .json extension and add PROCESSED prefix
        base_name = input_basename.replace('.json', '')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"PROCESSED_{base_name}_{timestamp}.json"
    
    # Ensure the output filename is in the processed-sales-data folder
    if not os.path.dirname(output_filename):
        output_filename = os.path.join(processed_folder, output_filename)
    elif not output_filename.startswith(processed_folder):
        output_filename = os.path.join(processed_folder, os.path.basename(output_filename))
    
    print(f"📁 Loading item IDs from: {input_filename}")
    
    # Load item IDs from file
    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        item_ids = data.get('item_ids', [])
        seller_username = data.get('seller_username', 'Unknown')
        query = data.get('query', '')
        
        # Apply limit if specified
        if limit is not None and limit > 0:
            original_count = len(item_ids)
            item_ids = item_ids[:limit]
            print(f"✅ Loaded {len(item_ids)} item IDs from {seller_username} (limited from {original_count})")
        else:
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
    def get_estimated_sold_quantity(item):
        """Extract estimated sold quantity from complete item data"""
        estimated_availabilities = item.get('estimatedAvailabilities', [])
        if estimated_availabilities:
            return estimated_availabilities[0].get('estimatedSoldQuantity')
        return None
    
    def get_formatted_price(item):
        """Extract formatted price from complete item data"""
        price_info = item.get('price', {})
        price_value = price_info.get('value', 'N/A')
        currency = price_info.get('currency', 'USD')
        return f"${price_value} {currency}" if price_value != 'N/A' else 'N/A'
    
    items_with_sales = [item for item in all_sales_data if get_estimated_sold_quantity(item) is not None]
    items_without_sales = [item for item in all_sales_data if get_estimated_sold_quantity(item) is None]
    
    # Sort by estimated sold quantity (descending)
    sorted_items = sorted(items_with_sales, key=lambda x: get_estimated_sold_quantity(x) or 0, reverse=True)
    
    # Add items without sales data at the end
    final_sorted_list = sorted_items + items_without_sales
    
    print(f"✅ Sorted {len(sorted_items)} items with sales data")
    print(f"📊 {len(items_without_sales)} items without sales data")
    
    # Display top 10 items
    print(f"\n🏆 Top 10 Best Selling Items:")
    for i, item in enumerate(sorted_items[:10]):
        sold_qty = get_estimated_sold_quantity(item) or 0
        title = item.get('title', 'N/A')[:50]
        price = get_formatted_price(item)
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
        'limit_applied': limit if limit else None,
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
            total_sold = sum(get_estimated_sold_quantity(item) or 0 for item in sorted_items)
            avg_sold = total_sold / len(sorted_items)
            max_sold = max(get_estimated_sold_quantity(item) or 0 for item in sorted_items)
            
            print(f"\n📊 Sales Summary:")
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
        
        # Create Collected-Data folder if it doesn't exist
        collected_data_folder = "Collected-Data"
        if not os.path.exists(collected_data_folder):
            os.makedirs(collected_data_folder)
            print(f"📁 Created folder: {collected_data_folder}")
        
        output_filename = os.path.join(collected_data_folder, f"Top{top_n}Sales_{timestamp}.json")
    
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
    
    # Helper function to extract estimated sold quantity from complete item data
    def get_estimated_sold_quantity_from_item(item):
        """Extract estimated sold quantity from complete item data"""
        estimated_availabilities = item.get('estimatedAvailabilities', [])
        if estimated_availabilities:
            return estimated_availabilities[0].get('estimatedSoldQuantity')
        return None
    
    # Get top N items with sales data (they're already sorted)
    items_with_sales = [item for item in all_items if get_estimated_sold_quantity_from_item(item) is not None]
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
            total_sold = sum(get_estimated_sold_quantity_from_item(item) or 0 for item in top_items)
            print(f"\n🏆 Top {top_n} Summary:")
            print(f"  Total estimated units sold: {total_sold}")
            print(f"  Average sold per item: {total_sold/len(top_items):.1f}")
            
            # Show top 5 items
            print(f"\n🏆 Top 5 Items:")
            for i, item in enumerate(top_items[:5]):
                sold_qty = get_estimated_sold_quantity_from_item(item) or 0
                title = item.get('title', 'N/A')[:40]
                
                # Extract price information
                price_info = item.get('price', {})
                price_value = price_info.get('value', 'N/A')
                currency = price_info.get('currency', 'USD')
                formatted_price = f"${price_value} {currency}" if price_value != 'N/A' else 'N/A'
                
                print(f"  {i+1}. {sold_qty:3d} sold - {formatted_price} - {title}...")
        
        return top_items
        
    except Exception as e:
        print(f"❌ Error saving top items file: {e}")
        return top_items

def getTopSellingItems(input_filename="SalesExport.json", top_n=50, pastDays = 9999):
    """
    Get the top N selling items from a processed sales export file.
    
    Args:
        input_filename (str): Name of the file containing processed sales data (SalesExport.json)
        top_n (int): Number of top items to return
        pastDays (int): Number of past days to filter (not implemented yet)
    
    Returns:
        list: Top N selling items
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create Collected-Data folder if it doesn't exist
    collected_data_folder = "Collected-Data"
    if not os.path.exists(collected_data_folder):
        os.makedirs(collected_data_folder)
        print(f"📁 Created folder: {collected_data_folder}")
    
    output_filename = os.path.join(collected_data_folder, f"Top{top_n}Sales_{timestamp}.json")
    
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
    
    # Helper function to extract estimated sold quantity from complete item data
    def get_estimated_sold_quantity_from_item(item):
        """Extract estimated sold quantity from complete item data"""
        estimated_availabilities = item.get('estimatedAvailabilities', [])
        if estimated_availabilities:
            return estimated_availabilities[0].get('estimatedSoldQuantity')
        return None
    
    # Get top N items with sales data (they're already sorted)
    items_with_sales = [item for item in all_items if get_estimated_sold_quantity_from_item(item) is not None]
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
            total_sold = sum(get_estimated_sold_quantity_from_item(item) or 0 for item in top_items)
            print(f"\n🏆 Top {top_n} Summary:")
            print(f"  Total estimated units sold: {total_sold}")
            print(f"  Average sold per item: {total_sold/len(top_items):.1f}")
            
            # Show top 5 items
            print(f"\n🏆 Top 5 Items:")
            for i, item in enumerate(top_items[:5]):
                sold_qty = get_estimated_sold_quantity_from_item(item) or 0
                title = item.get('title', 'N/A')[:40]
                
                # Extract price information
                price_info = item.get('price', {})
                price_value = price_info.get('value', 'N/A')
                currency = price_info.get('currency', 'USD')
                formatted_price = f"${price_value} {currency}" if price_value != 'N/A' else 'N/A'
                
                print(f"  {i+1}. {sold_qty:3d} sold - {formatted_price} - {title}...")
        
        return top_items
        
    except Exception as e:
        print(f"❌ Error saving top items file: {e}")
        return top_items


def getByRatio(input_filename="SalesExport.json"):
    """
    Get items sorted by ratio (placeholder function).
    
    Args:
        input_filename (str): Name of the file containing processed sales data
    
    Returns:
        list: Items sorted by ratio
    """
    print("⚠️ getByRatio function not yet implemented")
    return []


def add_item(item_data):
    """
    Create and publish a new listing on eBay using the Trading API AddItem endpoint.
    
    Args:
        item_data (dict): Dictionary containing all mandatory information for creating an item
    
    Returns:
        dict: Response containing item ID and fees if successful, or error information
    """
    import xml.etree.ElementTree as ET
    from datetime import datetime, timedelta
    
    # Get a valid token for Trading API
    # Use the same application_token as other functions in this codebase
    valid_token = helper_get_valid_token()
    if not valid_token:
        print("❌ Error: Could not get valid access token")
        return {"success": False, "error": "Could not get valid access token"}
    
    # Use production endpoint
    url = "https://api.ebay.com/ws/api.dll"
    site_id = "0"  # US Production
    print("🚀 Using eBay Production environment")
    
    # Validate required fields
    required_fields = [
        'Title', 'Description', 'CategoryID', 'StartPrice', 'ConditionID',
        'Country', 'Currency', 'DispatchTimeMax', 'ListingDuration', 'ListingType',
        'PaymentMethods', 'PayPalEmailAddress', 'PostalCode', 'Quantity'
    ]
    
    missing_fields = [field for field in required_fields if field not in item_data]
    if missing_fields:
        error_msg = f"Missing required fields: {', '.join(missing_fields)}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}
    
    # Set default values for optional fields if not provided
    defaults = {
        'ReturnsAcceptedOption': 'ReturnsAccepted',
        'RefundOption': 'MoneyBack',
        'ReturnsWithinOption': 'Days_30',
        'ShippingCostPaidByOption': 'Buyer',
        'ShippingType': 'Flat',
        'ShippingService': 'USPSPriority',
        'ShippingServiceCost': '5.99',
        'Location': 'United States'
    }
    
    for key, default_value in defaults.items():
        if key not in item_data:
            item_data[key] = default_value
    
    # Construct the XML payload
    xml_payload = f"""<?xml version="1.0" encoding="utf-8"?>
<AddItemRequest xmlns="urn:ebay:apis:eBLBaseComponents">
    <RequesterCredentials>
      <eBayAuthToken>{valid_token}</eBayAuthToken>
    </RequesterCredentials>
  <Item>
    <Title><![CDATA[{item_data['Title']}]]></Title>
    <Description><![CDATA[{item_data['Description']}]]></Description>
    <PrimaryCategory>
      <CategoryID>{item_data['CategoryID']}</CategoryID>
    </PrimaryCategory>
    <StartPrice>{item_data['StartPrice']}</StartPrice>
    <ConditionID>{item_data['ConditionID']}</ConditionID>
    <Country>{item_data['Country']}</Country>
    <Currency>{item_data['Currency']}</Currency>
    <DispatchTimeMax>{item_data['DispatchTimeMax']}</DispatchTimeMax>
    <ListingDuration>{item_data['ListingDuration']}</ListingDuration>
    <ListingType>{item_data['ListingType']}</ListingType>
    <PaymentMethods>{item_data['PaymentMethods']}</PaymentMethods>
    <PayPalEmailAddress>{item_data['PayPalEmailAddress']}</PayPalEmailAddress>
    <PostalCode>{item_data['PostalCode']}</PostalCode>
    <Quantity>{item_data['Quantity']}</Quantity>
    <Location>{item_data.get('Location', 'United States')}</Location>
    <ReturnPolicy>
      <ReturnsAcceptedOption>{item_data['ReturnsAcceptedOption']}</ReturnsAcceptedOption>
      <RefundOption>{item_data['RefundOption']}</RefundOption>
      <ReturnsWithinOption>{item_data['ReturnsWithinOption']}</ReturnsWithinOption>
      <ShippingCostPaidByOption>{item_data['ShippingCostPaidByOption']}</ShippingCostPaidByOption>
    </ReturnPolicy>
    <ShippingDetails>
      <ShippingType>{item_data['ShippingType']}</ShippingType>
      <ShippingServiceOptions>
        <ShippingService>{item_data['ShippingService']}</ShippingService>
        <ShippingServiceCost>{item_data['ShippingServiceCost']}</ShippingServiceCost>
      </ShippingServiceOptions>
    </ShippingDetails>
    <Site>US</Site>
  </Item>
</AddItemRequest>"""
    
    # Set the headers for eBay Trading API
    # Use the same credentials as other functions in this codebase
    headers = {
        "X-EBAY-API-SITEID": site_id,
        "X-EBAY-API-COMPATIBILITY-LEVEL": "967",
        "X-EBAY-API-CALL-NAME": "AddItem",
        "X-EBAY-API-DEV-NAME": CLIENT_ID,
        "X-EBAY-API-APP-NAME": API_KEY,
        "X-EBAY-API-CERT-NAME": CLIENT_SECRET,
        "Content-Type": "text/xml"
    }
    
    try:
        print(f"📦 Creating listing: {item_data['Title'][:50]}...")
        print(f"💰 Price: ${item_data['StartPrice']} {item_data['Currency']}")
        print(f"📂 Category: {item_data['CategoryID']}")
        
        response = requests.post(url, data=xml_payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Parse the response
            response_xml = ET.fromstring(response.content)
            ack = response_xml.find(".//{urn:ebay:apis:eBLBaseComponents}Ack")
            
            if ack is not None and ack.text == "Success":
                # Extract success information
                item_id = response_xml.find(".//{urn:ebay:apis:eBLBaseComponents}ItemID")
                start_date = response_xml.find(".//{urn:ebay:apis:eBLBaseComponents}StartDate")
                end_date = response_xml.find(".//{urn:ebay:apis:eBLBaseComponents}EndDate")
                
                result = {
                    "success": True,
                    "item_id": item_id.text if item_id is not None else None,
                    "start_date": start_date.text if start_date is not None else None,
                    "end_date": end_date.text if end_date is not None else None,
                    "ack": "Success"
                }
                
                # Extract fees information
                fees = response_xml.find(".//{urn:ebay:apis:eBLBaseComponents}Fees")
                if fees is not None:
                    result["fees"] = []
                    for fee in fees.findall(".//{urn:ebay:apis:eBLBaseComponents}Fee"):
                        fee_name = fee.find(".//{urn:ebay:apis:eBLBaseComponents}Name")
                        fee_amount = fee.find(".//{urn:ebay:apis:eBLBaseComponents}Fee")
                        if fee_name is not None and fee_amount is not None:
                            result["fees"].append({
                                "name": fee_name.text,
                                "amount": fee_amount.text
                            })
                
                print(f"✅ Item listed successfully!")
                print(f"🆔 Item ID: {result['item_id']}")
                print(f"📅 Start Date: {result['start_date']}")
                print(f"📅 End Date: {result['end_date']}")
                
                return result
            else:
                # Handle errors
                errors = response_xml.findall(".//{urn:ebay:apis:eBLBaseComponents}Errors")
                error_messages = []
                for error in errors:
                    error_code = error.find(".//{urn:ebay:apis:eBLBaseComponents}ErrorCode")
                    short_message = error.find(".//{urn:ebay:apis:eBLBaseComponents}ShortMessage")
                    long_message = error.find(".//{urn:ebay:apis:eBLBaseComponents}LongMessage")
                    
                    if error_code is not None and short_message is not None:
                        error_msg = f"Error {error_code.text}: {short_message.text}"
                        error_messages.append(error_msg)
                        print(f"❌ {error_msg}")
                
                return {
                    "success": False,
                    "error": "; ".join(error_messages),
                    "raw_response": response.text
                }
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "raw_response": response.text
            }
            
    except Exception as e:
        error_msg = f"Exception occurred: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}


def create_ebay_listing(sku, inventory_item_data, locale="en_US", use_user_token=True):
    """
    Create or replace an inventory item using the eBay Inventory API.
    
    Args:
        sku (str): Seller-defined SKU value for the inventory item (required)
        inventory_item_data (dict): Dictionary containing inventory item data including:
            - availability: dict with shipToLocationAvailability
            - condition: str (e.g., "NEW", "USED_EXCELLENT")
            - product: dict with title, description, aspects, imageUrls
            - locale: str (optional, defaults to parameter value)
            - packageWeightAndSize: dict (optional but recommended)
        locale (str): Locale code (e.g., "en_US"). Default: "en_US"
        use_user_token (bool): If True, use user_token instead of application_token. Default: False
    
    Returns:
        dict: Response containing statusCode, SKU, and any warnings/errors, or None on failure
    """
    # Get a valid token
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
    
    # Ensure locale is set in the data
    if 'locale' not in inventory_item_data:
        inventory_item_data['locale'] = locale
    
    # Endpoint for creating/replacing a single inventory item
    url = f"https://api.ebay.com/sell/inventory/v1/inventory_item/{sku}"
    
    # Convert locale format from en_US to en-US for Content-Language header
    content_language = locale.replace('_', '-') if '_' in locale else locale
    
    headers = {
        'Authorization': f'Bearer {valid_token}',
        'Content-Language': content_language,
        'Content-Type': 'application/json'
    }
    
    try:
        # Print headers with masked Authorization token for security
        for key, value in headers.items():
            
            print(f"   {key}: {value}")
        
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
            
            # Check for errors
            errors = result.get('errors', [])
            if errors:
                print(f"❌ Errors:")
                for error in errors:
                    print(f"   - {error.get('message', 'Unknown error')}")
            
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


def extract_item_data_for_listing(item_data, seller_info=None):
    """
    Extract and map data from processed sales data to create item_data for AddItem API.
    
    Args:
        item_data (dict): Item data from processed sales export
        seller_info (dict): Optional seller information (PayPal email, location, etc.)
    
    Returns:
        dict: Mapped item data ready for AddItem API
    """
    import random
    
    # Extract basic information
    title = item_data.get('title', 'Sample Item')
    description = item_data.get('shortDescription', 'No description available')
    
    # Get price information
    price_info = item_data.get('price', {})
    price_value = price_info.get('value', '9.99')
    currency = price_info.get('currency', 'USD')
    
    # Get category information
    category_path = item_data.get('categoryPath', '')
    category_id_path = item_data.get('categoryIdPath', '')
    
    # Extract the primary category ID (first one in the path)
    primary_category_id = category_id_path.split('|')[0] if category_id_path else '888'  # Default to Sporting Goods
    
    # Get condition information
    condition_id = item_data.get('conditionId', '1000')  # Default to New
    
    # Get location information
    item_location = item_data.get('itemLocation', {})
    location_city = item_location.get('city', 'Unknown City')
    location_state = item_location.get('stateOrProvince', 'Unknown State')
    location_country = item_location.get('country', 'US')
    location_postal = item_location.get('postalCode', '12345')
    
    # Create description with additional details
    enhanced_description = f"""
    <div>
        <h3>Product Description</h3>
        <p>{description}</p>
        
        <h3>Key Features</h3>
        <ul>
            <li>High-quality construction</li>
            <li>Made from durable PETG material</li>
            <li>Available in black color</li>
            <li>Perfect for everyday use</li>
        </ul>
        
        <h3>Shipping & Returns</h3>
        <p>Fast and reliable shipping. 30-day return policy.</p>
        
        <h3>Questions?</h3>
        <p>Feel free to contact us with any questions!</p>
    </div>
    """
    
    # Create mapped item data
    mapped_data = {
        'Title': title,
        'Description': enhanced_description,
        'CategoryID': primary_category_id,
        'StartPrice': price_value,
        'ConditionID': condition_id,
        'Country': location_country,
        'Currency': currency,
        'DispatchTimeMax': '3',  # 3 business days
        'ListingDuration': 'GTC',  # Good 'Til Cancelled
        'ListingType': 'FixedPriceItem',
        'PaymentMethods': 'PayPal',
        'PayPalEmailAddress': seller_info.get('paypal_email', 'test@example.com') if seller_info else 'test@example.com',
        'PostalCode': location_postal,
        'Quantity': '1',
        'Location': f"{location_city}, {location_state}, {location_country}",
        'ReturnsAcceptedOption': 'ReturnsAccepted',
        'RefundOption': 'MoneyBack',
        'ReturnsWithinOption': 'Days_30',
        'ShippingCostPaidByOption': 'Buyer',
        'ShippingType': 'Flat',
        'ShippingService': 'USPSPriority',
        'ShippingServiceCost': '5.99'
    }
    
    return mapped_data


def test_add_item_with_sales_data(filename=None, item_index=0):
    """
    Test the add_item function using data from processed sales export.
    
    Args:
        filename (str): Path to processed sales data file (optional)
        item_index (int): Index of item to test with (default: 0)
    
    Returns:
        dict: Result of the add_item test
    """
    import random
    
    # Default to the processed sales data file
    if not filename:
        filename = "Collected-Data/3dexcel/processed-sales-data/PROCESSED_3dexcel_20250928_161528_20250928_171132.json"
    
    print(f"🧪 Testing AddItem function with data from: {filename}")
    
    try:
        # Load the processed sales data
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        items = data.get('items', [])
        if not items:
            print("❌ No items found in the processed sales data")
            return {"success": False, "error": "No items found in processed sales data"}
        
        # Select an item (random if index is -1, otherwise use specified index)
        if item_index == -1:
            selected_item = random.choice(items)
            print(f"🎲 Randomly selected item from {len(items)} available items")
        else:
            if item_index >= len(items):
                item_index = 0
                print(f"⚠️ Item index {item_index} out of range, using first item")
            selected_item = items[item_index]
            print(f"📦 Using item at index {item_index} of {len(items)} available items")
        
        # Display selected item information
        print(f"\n📋 Selected Item Details:")
        print(f"   Title: {selected_item.get('title', 'N/A')}")
        print(f"   Price: ${selected_item.get('price', {}).get('value', 'N/A')} {selected_item.get('price', {}).get('currency', 'USD')}")
        print(f"   Category: {selected_item.get('categoryPath', 'N/A')}")
        print(f"   Condition: {selected_item.get('condition', 'N/A')}")
        
        # Create seller info (you would replace this with actual seller information)
        seller_info = {
            'paypal_email': 'test@example.com',  # Replace with actual PayPal email
            'location': 'United States'
        }
        
        # Extract and map the data
        print(f"\n🔄 Mapping item data for AddItem API...")
        item_data_for_listing = extract_item_data_for_listing(selected_item, seller_info)
        
        # Display mapped data
        print(f"\n📝 Mapped Item Data:")
        print(f"   Title: {item_data_for_listing['Title'][:50]}...")
        print(f"   Category ID: {item_data_for_listing['CategoryID']}")
        print(f"   Price: ${item_data_for_listing['StartPrice']} {item_data_for_listing['Currency']}")
        print(f"   Condition ID: {item_data_for_listing['ConditionID']}")
        print(f"   Location: {item_data_for_listing['Location']}")
        print(f"   PayPal Email: {item_data_for_listing['PayPalEmailAddress']}")
        
        # Test the add_item function (in production mode)
        print(f"\n🚀 Testing AddItem function in production mode...")
        result = add_item(item_data_for_listing)
        
        return result
        
    except FileNotFoundError:
        error_msg = f"File not found: {filename}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}
    except json.JSONDecodeError:
        error_msg = f"Invalid JSON file: {filename}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"Error testing AddItem: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}


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
                
                # Extract price information
                price_info = result.get('price', {})
                price_value = price_info.get('value', 'N/A')
                currency = price_info.get('currency', 'USD')
                formatted_price = f"${price_value} {currency}" if price_value != 'N/A' else 'N/A'
                print(f"💰 Price: {formatted_price}")
                
                # Extract estimated sold quantity
                estimated_availabilities = result.get('estimatedAvailabilities', [])
                estimated_sold = estimated_availabilities[0].get('estimatedSoldQuantity') if estimated_availabilities else None
                print(f"📊 Sold: {estimated_sold if estimated_sold is not None else 'N/A'}")
                
                print(f"📅 Date: {result.get('itemCreationDate', 'N/A')}")
                
        elif command == "collect":
            if not args: raise ValueError("Usage: collect <seller_username> [query] [limit]")
            seller, query, limit = args[0], args[1] if len(args) > 1 else " ", int(args[2]) if len(args) > 2 else 200
            print(f"📦 Collecting from: {seller}")
            getItemIds(seller, query, limit)
            
        elif command == "process":
            if not args: raise ValueError("Usage: process <seller_username> [limit] [output_filename]")
            seller_username = args[0]
            limit = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
            output_filename = args[2] if len(args) > 2 else (args[1] if len(args) > 1 and not args[1].isdigit() else None)
            print(f"📊 Processing newest file for seller: {seller_username}")
            if limit:
                print(f"🔢 Limiting to {limit} items")
            processSalesExportFromFile(seller_username, output_filename, limit)
            
        elif command == "top":
            input_file, top_n, output_file = args[0] if args else "SalesExport.json", int(args[1]) if len(args) > 1 else 50, args[2] if len(args) > 2 else None
            print(f"🏆 Top {top_n} from: {input_file}")
            getTopSellingItems(input_file, top_n, output_file)
            
        elif command == "copy":
            if not args: raise ValueError("Usage: copy <item_id_or_link>")
            print(f"�� Copying: {args[0]}")
            copy_listing_main(args[0])
            
        elif command == "refresh":
            refreshToken()
            
        elif command == "test-add":
            item_index = int(args[0]) if args else 0
            print(f"🧪 Testing AddItem function with item index: {item_index}")
            test_add_item_with_sales_data(item_index=item_index)
            
        elif command == "createinv":
            print(f"📍 Creating inventory location: PlasticLoveShopLocation")
            result = create_inventory_location()
            if result:
                print(f"\n✅ Location created successfully!")
            else:
                print(f"\n❌ Location creation failed. Check the error messages above.")
            
        elif command == "list":
            # All test data is hardcoded in create_test_listing() function in upload_to_ebay.py
            create_test_listing(locale="en-US", use_user_token=True)
            
        elif command == "combine":
            # Optional arguments: sku and output_filename
            sku = args[0] if args else None
            output_filename = args[1] if len(args) > 1 else None
            
            print(f"📦 Creating inventory and offer listing...")
            if sku:
                print(f"🆔 SKU: {sku}")
            if output_filename:
                print(f"📁 Output filename: {output_filename}")
            
            result = create_inventory_and_offer_listing(
                sku=sku,
                output_filename=output_filename
            )
            
            if result:
                print(f"\n✅ Listing data created successfully!")
                print(f"📁 File: {result}")
            else:
                print(f"\n❌ Failed to create listing data")
            
        elif command == "image":
            if len(args) < 2:
                raise ValueError("Usage: image <image_url> <image_type>")
            image_url = args[0]
            image_type_str = args[1].upper()
            
            # Validate and convert image type
            if image_type_str == "PROFESSIONAL":
                image_type = ImageType.PROFESSIONAL
            elif image_type_str == "REAL_WORLD" or image_type_str == "REALWORLD":
                image_type = ImageType.REAL_WORLD
            else:
                raise ValueError("Image type must be 'PROFESSIONAL' or 'REAL_WORLD'")
            
            print(f"🖼️ Generating image from URL: {image_url}")
            print(f"📝 Image type: {image_type.value}")
            
            # Call the image generation function (saves JSON response)
            result = generate_image_from_urls([image_url], image_type)
            
            if result:
                print(f"\n✅ API response saved successfully!")
                print(f"📁 JSON file: {result}")
                print(f"💡 Use 'decode {result}' to extract and save the image")
            else:
                print(f"\n❌ Failed to generate image")
        
        elif command == "decode":
            print(f"🔍 Decoding image from most recent API response...")
            
            # Call the decode function
            result = decode_image_from_response()
            
            if result:
                print(f"\n✅ Image decoded and saved successfully!")
                print(f"📁 Image file: {result}")
            else:
                print(f"\n❌ Failed to decode image from JSON file")
        
        elif command == "upload":
            # Optional picture name argument
            picture_name = args[0] if args else "Uploaded Image"
            print(f"📤 Uploading image to eBay Picture Services...")
            print(f"📝 Picture name: {picture_name}")
            
            # Call the upload function
            result = upload_image_to_ebay(picture_name=picture_name)
            
            if result:
                print(f"\n✅ Image uploaded successfully!")
                print(f"🔗 Image URL: {result}")
            else:
                print(f"\n❌ Failed to upload image to eBay")
        
        elif command == "aspects":
            if not args: raise ValueError("Usage: aspects <category_id> [category_tree_id]")
            category_id = args[0]
            category_tree_id = args[1] if len(args) > 1 else "0"
            print(f"📋 Getting aspects for category: {category_id}")
            if category_tree_id != "0":
                print(f"🌳 Category tree ID: {category_tree_id}")
            result = get_item_aspects_for_category(category_id, category_tree_id)
            if not result:
                print(f"\n❌ Failed to get aspects for category {category_id}")
            
        else:
            print("❌ Available commands: search, seller, item, collect, process, top, copy, refresh [token], test-add [item_index], list [sku], createinv, combine [sku] [output_filename], image <url> <type>, decode, upload [picture_name], aspects <category_id> [category_tree_id]")
            
    except ValueError as e:
        print(f"❌ {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("❌ Usage: python main_ebay_commands.py <command> [args...]")
        print("Commands: search, seller, item, collect, process, top, copy, refresh [token], test-add [item_index], list [sku], createinv, combine [sku] [output_filename], image <url> <type>, decode, upload [picture_name], aspects <category_id> [category_tree_id]")
        sys.exit(1)
    
    run_command(sys.argv[1], *sys.argv[2:])
