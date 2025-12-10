"""
Create Text Module

This module contains functions for copying and optimizing eBay listings.
"""

import json
from helper_functions import remove_html_tags


def singleCopyListing(id):
    """
    Copy a listing from eBay and generate optimized content using LLM.
    
    Args:
        id (str): eBay item ID or URL
    
    Returns:
        dict: Optimized listing content with edited_title and edited_description, or None on failure
    """
    # Import here to avoid circular import issues
    from main_ebay_commands import single_get_detailed_item_data, call_openrouter_llm
    
    if (id[0] == 'h' or id[0] == 'e'):
        id = id.split('/itm/')[1].split('?')[0]

    listing = single_get_detailed_item_data(id, verbose = True)

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
        
        # Load prompt template from file
        prompt_template_path = "llm_prompt_template.txt"
        try:
            with open(prompt_template_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        except FileNotFoundError:
            print(f"❌ Prompt template file not found: {prompt_template_path}")
            return None
        except Exception as e:
            print(f"❌ Error loading prompt template: {e}")
            return None
        
        # Format the prompt with listing data
        prompt = prompt_template.format(
            original_title=listing.get('title', ''),
            original_description=clean_description
        )
        
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
    else:
        print("❌ No listing data available")
        return None
