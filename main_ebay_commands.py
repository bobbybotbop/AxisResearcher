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
from single_functions import singleSearch, single_search_by_seller
from helper_functions import remove_html_tags, helper_get_valid_token, handle_http_error, refreshToken


load_dotenv()
API_KEY = os.getenv('api_key')
CLIENT_ID = os.getenv('client_id')
CLIENT_SECRET = os.getenv('client_secret')
USER_TOKEN = os.getenv('user_token')
REFRESH_TOKEN = os.getenv('refresh_token')
OPENROUTER_API_KEY = os.getenv('openrouter_api_key')

ZIP_CODE = 14853


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
        # Create folder for seller if it doesn't exist
        safe_seller = seller_username.replace(" ", "_").replace("/", "_").replace("\\", "_")
        seller_folder = safe_seller
        
        if not os.path.exists(seller_folder):
            os.makedirs(seller_folder)
            print(f"📁 Created folder: {seller_folder}")
        
        # Generate filename with seller username and date
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{seller_folder}/{safe_seller}_{timestamp}.json"
        
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
    
    # Look for files in the seller's folder
    pattern = f"{safe_seller}/{safe_seller}_*.json"
    files = glob.glob(pattern)
    
    if not files:
        # Also check for files without the seller folder structure
        pattern = f"{safe_seller}_*.json"
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
    
    # Create seller folder if it doesn't exist
    seller_folder = safe_seller
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


def singleCopyListing(id):
    if (id[0] == 'h' or id[0] == 'e'):
        id = id.split('/itm/')[1].split('?')[0]

    listing = single_get_detailed_item_data(id, verbose = False)

    if listing:
        print("📦 Listing Details:")
        print(f"   Item ID: {listing.get('itemId', 'N/A')}")
        print(f"   Title: {listing.get('title', 'N/A')}")
        
        # Extract description and remove HTML tags
        description = listing.get('description', 'No description available')
        clean_description = remove_html_tags(description)
        print(f"   Description: {clean_description}")
        
        print(f"   Date: {listing.get('itemCreationDate', 'N/A')}")
        
        # Extract estimated sold quantity
        estimated_availabilities = listing.get('estimatedAvailabilities', [])
        estimated_sold = estimated_availabilities[0].get('estimatedSoldQuantity') if estimated_availabilities else None
        print(f"   Number Sold: {estimated_sold if estimated_sold is not None else 'N/A'}")
        
        # Extract price information
        price_info = listing.get('price', {})
        price_value = price_info.get('value', 'N/A')
        currency = price_info.get('currency', 'USD')
        formatted_price = f"${price_value} {currency}" if price_value != 'N/A' else 'N/A'
        print(f"   Price: {formatted_price}")
        
        # Extract number of pictures
        images = listing.get('image', {})
        image_urls = images.get('imageUrl', []) if isinstance(images.get('imageUrl'), list) else [images.get('imageUrl')] if images.get('imageUrl') else []
        number_of_pictures = len([url for url in image_urls if url])
        print(f"   Number of Pictures: {number_of_pictures}")
        
        # Extract thumbnail URL
        thumbnail_url = images.get('thumbnailUrl') or images.get('imageUrl') if isinstance(images.get('imageUrl'), str) else (image_urls[0] if image_urls else 'N/A')
        print(f"   Thumbnail URL: {thumbnail_url}")
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
{listing.get('title', '') if listing else ''}

Original description:
{clean_description if listing else ''}
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
        print("❌ Usage: python main_ebay_commands.py <command> [args...]")
        print("Commands: search, seller, item, collect, process, top, copy, refresh [token]")
        sys.exit(1)
    
    run_command(sys.argv[1], *sys.argv[2:])
