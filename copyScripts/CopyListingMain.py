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

        # Create listing file prematurely (as desired) - this increments counter once
        new_sku = create_listing_with_preferences()

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

        # Return photos and listing data for API consumption, including the SKU
        return {
            "sku": new_sku,  # Return the SKU so frontend can track it
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
                "estimatedSoldQuantity": listing.get('estimatedAvailabilities', [{}])[0].get('estimatedSoldQuantity') if listing.get('estimatedAvailabilities') else None,
                "localizedAspects": listing.get('localizedAspects', [])  # Include aspects from original listing
            }
        }
    else:
        print("ERROR: No listing data available")
        return None


def testing_function(id=None):
    """
    Testing function for development and debugging.
    Tests update_listing_with_aspects() function with an eBay listing ID or URL.
    
    Args:
        id (str, optional): eBay listing ID or URL
    
    Returns:
        dict: Result of testing update_listing_with_aspects function
    """
    from main_ebay_commands import single_get_detailed_item_data
    from copyScripts.combine_data import (
        get_next_sku, create_listing_with_preferences, update_listing_with_aspects,
        load_listing_data, DEFAULT_QUANTITY, DEFAULT_WEIGHT, DEFAULT_DIMESIONS,
        MERCHANT_LOCATION_KEY, get_listing_policies
    )
    
    if not id:
        return {"error": "No eBay listing ID or URL provided"}
    
    # Handle URL parsing if needed
    item_id = id
    if id and (id[0] == 'h' or id[0] == 'e'):
        item_id = id.split('/itm/')[1].split('?')[0]

    print(f"🔍 Testing update_listing_with_aspects() with eBay listing ID: {item_id}")
    
    # Get listing data from eBay API
    listing = single_get_detailed_item_data(item_id, verbose=True)

    if not listing:
        return {"error": "Failed to fetch listing data from eBay"}
    
    # Extract data from eBay listing
    title = listing.get('title', '')
    description = remove_html_tags(listing.get('description', 'No description available'))
    price_value = listing.get('price', {}).get('value', '0')
    category_id = listing.get('categoryId', '')
    localized_aspects = listing.get('localizedAspects', [])
    
    image_urls = [
        url for url in 
        [listing.get("image", {}).get("imageUrl")] + 
        [img.get("imageUrl") for img in listing.get("additionalImages", []) if isinstance(img, dict)]
        if url
    ]
    
    print(f"📋 eBay Listing Info:")
    print(f"   Title: {title}")
    print(f"   Category ID: {category_id}")
    print(f"   Price: ${price_value}")
    print(f"   Found {len(localized_aspects)} localized aspects from eBay listing")
    
    if localized_aspects:
        print(f"   Localized aspects:")
        for aspect in localized_aspects:
            aspect_name = aspect.get('name', 'N/A')
            aspect_value = aspect.get('value', 'N/A')
            print(f"     - {aspect_name}: {aspect_value}")
    
    # Create a test listing file
    sku = get_next_sku()
    print(f"\n📝 Creating test listing file with SKU: {sku}")
    
    inventory_item_data = {
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
            "title": title,
            "description": description,
            "aspects": {},
            "imageUrls": image_urls
        }
    }
    
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
    
    policies = get_listing_policies()
    if policies:
        offer_data["listingPolicies"] = policies
    
    create_listing_with_preferences(
        sku=sku,
        inventory_item_data=inventory_item_data,
        offer_data=offer_data
    )
    
    print(f"✅ Created listing file: {sku}.json")
    
    # Load listing before updating aspects
    listing_before = load_listing_data(sku=sku)
    aspects_before = listing_before.get('inventoryItem', {}).get('product', {}).get('aspects', {}) if listing_before else {}
    
    print(f"\n🔧 Before update_listing_with_aspects():")
    print(f"   Aspects: {aspects_before}")
    
    # Test update_listing_with_aspects()
    print(f"\n🔄 Calling update_listing_with_aspects(sku='{sku}', localizedAspects={len(localized_aspects)} aspects)...")
    success = update_listing_with_aspects(sku, localized_aspects)
    
    if not success:
        return {
            "error": "update_listing_with_aspects() returned False",
            "sku": sku,
            "localized_aspects_count": len(localized_aspects),
            "category_id": category_id
        }
    
    # Load listing after updating aspects
    listing_after = load_listing_data(sku=sku)
    aspects_after = listing_after.get('inventoryItem', {}).get('product', {}).get('aspects', {}) if listing_after else {}
    
    print(f"\n✅ After update_listing_with_aspects():")
    print(f"   Aspects: {aspects_after}")
    
    # Return detailed result
    result = {
        "success": True,
        "sku": sku,
        "ebay_listing_id": item_id,
        "category_id": category_id,
        "localized_aspects_from_ebay": localized_aspects,
        "localized_aspects_count": len(localized_aspects),
        "aspects_before": aspects_before,
        "aspects_after": aspects_after,
        "aspects_added": {
            key: value for key, value in aspects_after.items() 
            if key not in aspects_before or aspects_before[key] != value
        },
        "message": f"Successfully tested update_listing_with_aspects() for SKU {sku}"
    }
    
    return result
