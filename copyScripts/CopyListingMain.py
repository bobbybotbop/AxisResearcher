"""
Copy Listing Main Module

This module orchestrates the process of fetching eBay listing data
and generating optimized text content.
"""

from helper_functions import remove_html_tags
from copyScripts.create_text import create_text
from copyScripts.combine_data import create_listing_with_preferences, update_listing_title_description, update_listing_meta_data,update_listing_with_aspects
from copyScripts.create_image import generate_image_from_urls, ImageType, categorize_images



def copy_listing_main(id):
    """
    Copy a listing from eBay and generate optimized content using LLM.
    
    Args:
        id (str): eBay item ID or URL
    
    Returns:
        dict: Optimized listing content with edited_title and edited_description, or None on failure
    """
    # Import here to avoid circular import issues
    from main_ebay_commands import single_get_detailed_item_data
    
    # Handle URL parsing if needed
    if (id[0] == 'h' or id[0] == 'e'):
        id = id.split('/itm/')[1].split('?')[0]

    # Get listing data from eBay API
    listing = single_get_detailed_item_data(id, verbose=True)

    if listing:
        # print("📦 Listing Details:")
        # print(f"   Item ID: {listing.get('itemId', 'N/A')}")
        # print(f"   Title: {listing.get('title', 'N/A')}")
        
        # Extract description and remove HTML tags
        # description = listing.get('description', 'No description available')
        # clean_description = remove_html_tags(description)
        # print(f"   Description: {clean_description}")
        
        # print(f"   Date: {listing.get('itemCreationDate', 'N/A')}")
        
        # # Extract estimated sold quantity
        # estimated_availabilities = listing.get('estimatedAvailabilities', [])
        # estimated_sold = estimated_availabilities[0].get('estimatedSoldQuantity') if estimated_availabilities else None
        # print(f"   Number Sold: {estimated_sold if estimated_sold is not None else 'N/A'}")
        
        # # Extract price information
        # price_info = listing.get('price', {})
        # price_value = price_info.get('value', 'N/A')
        # currency = price_info.get('currency', 'USD')
        # formatted_price = f"${price_value} {currency}" if price_value != 'N/A' else 'N/A'
        # print(f"   Price: {formatted_price}")
        
        # # Extract number of pictures
        # images = listing.get('image', {})
        # image_urls = images.get('imageUrl', []) if isinstance(images.get('imageUrl'), list) else [images.get('imageUrl')] if images.get('imageUrl') else []
        # number_of_pictures = len([url for url in image_urls if url])
        # print(f"   Number of Pictures: {number_of_pictures}")
        
        # # Extract thumbnail URL
        # thumbnail_url = images.get('thumbnailUrl') or images.get('imageUrl') if isinstance(images.get('imageUrl'), str) else (image_urls[0] if image_urls else 'N/A')
        # print(f"   Thumbnail URL: {thumbnail_url}")
        
        # Extract title and description

        new_sku = create_listing_with_preferences();

        # old_title = listing.get('title', '')
        # old_description = remove_html_tags(listing.get('description', 'No description available'))

        # # Call create_text to generate optimized content
        # optimized_content = create_text(old_title, old_description)

        # if optimized_content:
        #     update_listing_title_description(new_sku, optimized_content)
        # else:
        #     print("ERROR: no optimized content")

        # # Update meta data
        # old_price = listing.get('price', {}).get('value', 'N/A')
        # old_categoryId = listing.get('categoryId', 'N/A')

        # update_listing_meta_data(new_sku, old_price, old_categoryId)
        # # Update aspects
        # old_aspects = listing.get('localizedAspects', [])
        # update_listing_with_aspects(new_sku, old_aspects)

        # Update Photos - extract all image URLs into a flat list
        old_photo_list = [
            url for url in 
            [listing.get("image", {}).get("imageUrl")] + 
            [img.get("imageUrl") for img in listing.get("additionalImages", []) if isinstance(img, dict)]
            if url
        ]
        print(f"Found {len(old_photo_list)} photo(s): {old_photo_list}")
        # old_photo_list = [listing.get("image",{}).get("imageUrl")].extend([])
        # print(generate_image_from_urls(old_photo_list, ImageType.EXPERIMENTAL))

        # Categorize images
        categories = {}
        if old_photo_list:
            print("Categorizing images...")
            categories = categorize_images(old_photo_list)
            if categories is None:
                categories = {}

        # Return photos and listing data for API consumption
        return {
            "photos": old_photo_list,
            "categories": categories,
            "listing": {
                "itemId": listing.get('itemId', 'N/A'),
                "title": listing.get('title', 'N/A'),
                "description": remove_html_tags(listing.get('description', 'No description available')),
                "price": listing.get('price', {}).get('value', 'N/A'),
                "currency": listing.get('price', {}).get('currency', 'USD'),
                "itemCreationDate": listing.get('itemCreationDate', 'N/A'),
                "categoryId": listing.get('categoryId', 'N/A'),
                "estimatedSoldQuantity": listing.get('estimatedAvailabilities', [{}])[0].get('estimatedSoldQuantity') if listing.get('estimatedAvailabilities') else None
            }
        }
    else:
        print("ERROR: No listing data available")
        return None


def testing_function(id=None):
    """
    Testing function for development and debugging.
    Add your test code here.
    
    Args:
        id (str, optional): ID parameter for testing
    
    Returns:
        Any: Result of testing function
    """
    from main_ebay_commands import single_get_detailed_item_data
    
    if not id:
        return {"error": "No ID provided"}
    
    # Handle URL parsing if needed
    if id and (id[0] == 'h' or id[0] == 'e'):
        id = id.split('/itm/')[1].split('?')[0]

    # Get listing data from eBay API
    listing = single_get_detailed_item_data(id, verbose=True)

    if listing:
        # Extract image URLs
        image_urls = [
            url for url in 
            [listing.get("image", {}).get("imageUrl")] + 
            [img.get("imageUrl") for img in listing.get("additionalImages", []) if isinstance(img, dict)]
            if url
        ]
        
        # Extract title and description
        title = listing.get('title', '')
        description = remove_html_tags(listing.get('description', 'No description available'))
        
        # Extract price and category
        price_value = listing.get('price', {}).get('value', '0')
        category_id = listing.get('categoryId', '')
        
        # Get quantity (if available, otherwise use default)
        estimated_availabilities = listing.get('estimatedAvailabilities', [])
        quantity = estimated_availabilities[0].get('estimatedSoldQuantity') if estimated_availabilities else 1
        
        # Create inventory item data structure
        from copyScripts.combine_data import (
            DEFAULT_QUANTITY, DEFAULT_WEIGHT, DEFAULT_DIMESIONS,
            MERCHANT_LOCATION_KEY, get_listing_policies
        )
        
        inventory_item_data = {
            "availability": {
                "shipToLocationAvailability": {
                    "quantity": DEFAULT_QUANTITY
                }
            },
            "condition": "NEW",  # Default to NEW, can be updated based on listing condition
            "packageWeightAndSize": {
                "weight": DEFAULT_WEIGHT,
                "dimensions": DEFAULT_DIMESIONS
            },
            "product": {
                "title": title,
                "description": description,
                "aspects": {},  # Can be populated from listing.get('localizedAspects', [])
                "imageUrls": image_urls
            }
        }
        
        # Create offer data structure
        offer_data = {
            "marketplaceId": "EBAY_US",
            "format": "FIXED_PRICE",
            "quantity": DEFAULT_QUANTITY,
            "pricingSummary": {
                "price": {
                    "value": str(price_value),
                    "currency": listing.get('price', {}).get('currency', 'USD')
                }
            },
            "listingDuration": "GTC",
            "categoryId": str(category_id),
            "merchantLocationKey": MERCHANT_LOCATION_KEY
        }
        
        # Add listing policies if available
        policies = get_listing_policies()
        if policies:
            offer_data["listingPolicies"] = policies
        
        # Create listing JSON file
        from copyScripts.combine_data import get_next_sku, create_listing_with_preferences
        
        sku = get_next_sku()
        create_listing_with_preferences(
            sku=sku,
            inventory_item_data=inventory_item_data,
            offer_data=offer_data
        )
        
        # Return formatted data
        result = {
            "sku": sku,
            "inventoryItem": inventory_item_data,
            "offer": offer_data,
            "message": f"Successfully formatted listing data and saved to Generated_Listings/{sku}.json"
        }
        
        print(f"✅ Formatted listing data for SKU: {sku}")
        print(f"   Title: {title}")
        print(f"   Price: ${price_value}")
        print(f"   Category: {category_id}")
        print(f"   Images: {len(image_urls)}")
        
        return result
    else:
        return {"error": "Failed to fetch listing data"}
