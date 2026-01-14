"""
Flask API for eBay Listing Photo Gallery

This Flask application provides a REST API endpoint to fetch photos
and listing details from eBay listings.
"""

import sys
import io

# Set UTF-8 encoding for stdout/stderr to handle Unicode characters
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from flask import Flask, jsonify, request
from flask_cors import CORS
from copyScripts.CopyListingMain import copy_listing_main, testing_function
from copyScripts.create_image import generate_image_from_urls, ImageType
from copyScripts.combine_data import get_next_sku, create_listing_with_preferences, update_listing_images, update_listing_title_description, update_listing_meta_data, load_listing_data
import os
import json
import os
import glob
from copyScripts.create_text import create_text
from copyScripts.upload_to_ebay import upload_complete_listing

app = Flask(__name__)
# Enable CORS for all routes to allow React frontend to make requests
CORS(app, origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"])

@app.route('/api/photos/<path:listing_id>', methods=['GET'])
def get_listing_photos(listing_id):
    """
    Fetch photos and listing details for a given eBay listing ID or URL.
    
    Args:
        listing_id: eBay item ID or full URL
        
    Returns:
        JSON response with photos array and listing details, or error message
    """
    try:
        result = copy_listing_main(listing_id)
        
        if result is None:
            return jsonify({
                "error": "Failed to fetch listing data. The listing may not exist or the ID is invalid.",
                "photos": [],
                "categories": {},
                "listing": None
            }), 404
        
        return jsonify({
            "photos": result.get("photos", []),
            "categories": result.get("categories", {}),
            "listing": result.get("listing", {}),
            "error": None
        }), 200
        
    except Exception as e:
        # Safely convert exception to string, handling encoding issues
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred while fetching listing data (encoding error)"
        
        return jsonify({
            "error": f"An error occurred while fetching listing data: {error_msg}",
            "photos": [],
            "categories": {},
            "listing": None
        }), 500

@app.route('/api/generate-images', methods=['POST'])
def generate_images():
    """
    Generate images based on confirmed categories.
    
    Accepts JSON body:
    {
        "photos": ["url1", "url2", ...],
        "categories": {"url1": "bad_image", "url2": "professional_image", ...}
    }
    
    Returns:
        JSON response with generated image URLs, or error message
    """
    try:
        print("[API] /api/generate-images endpoint called")
        data = request.get_json()
        print(f"[API] Received data: photos={len(data.get('photos', [])) if data else 0}, categories={len(data.get('categories', {})) if data else 0}")
        
        if not data:
            print("[API] Error: No data in request")
            return jsonify({
                "error": "Request body must be JSON",
                "generated_images": []
            }), 400
        
        photos = data.get("photos", [])
        categories = data.get("categories", {})
        
        print(f"[API] Processing {len(photos)} photos with {len(categories)} categories")
        
        if not photos or not isinstance(photos, list):
            print("[API] Error: Invalid photos array")
            return jsonify({
                "error": "photos must be a non-empty array",
                "generated_images": []
            }), 400
        
        if not categories or not isinstance(categories, dict):
            print("[API] Error: Invalid categories dict")
            return jsonify({
                "error": "categories must be a non-empty dictionary",
                "generated_images": []
            }), 400
        
        # Categories to skip
        skip_categories = ['real_world_image', 'edited_image']
        
        # Map categories to ImageType
        category_to_image_type = {
            'bad_image': ImageType.REAL_WORLD,
            'professional_image': ImageType.PROFESSIONAL
        }
        
        generated_images = []
        errors = []
        
        # Process each photo
        for idx, photo_url in enumerate(photos):
            category = categories.get(photo_url)
            print(f"[API] Processing photo {idx + 1}/{len(photos)}: category={category}")
            
            # Skip if category is None or in skip list
            if not category or category in skip_categories:
                print(f"[API] Skipping photo {idx + 1}: category={category} (None or in skip list)")
                continue
            
            # Get ImageType for this category
            image_type = category_to_image_type.get(category)
            
            if not image_type:
                error_msg = f"Unknown category '{category}' for photo {photo_url[:50]}..."
                print(f"[API] {error_msg}")
                errors.append(error_msg)
                continue
            
            try:
                print(f"[API] Generating image {idx + 1} with type {image_type.value}...")
                # Generate image using the appropriate prompt
                result = generate_image_from_urls([photo_url], image_type)
                
                if result and isinstance(result, list):
                    generated_images.extend(result)
                    print(f"[API] Successfully generated {len(result)} image(s) for photo {idx + 1}")
                elif result:
                    # In case result is not a list, wrap it
                    generated_images.append(result)
                    print(f"[API] Successfully generated 1 image for photo {idx + 1}")
                else:
                    error_msg = f"Failed to generate image for {photo_url[:50]}..."
                    print(f"[API] {error_msg}")
                    errors.append(error_msg)
            except Exception as e:
                error_msg = f"Error generating image for {photo_url[:50]}...: {str(e)}"
                print(f"[API] Exception: {error_msg}")
                import traceback
                traceback.print_exc()
                errors.append(error_msg)
        
        print(f"[API] Generation complete: {len(generated_images)} images generated, {len(errors)} errors")
        print(f"[API] Generated image URLs: {generated_images}")
        
        # Return results
        response_data = {
            "generated_images": generated_images,
            "error": None
        }
        
        if errors:
            response_data["warnings"] = errors
            print(f"[API] Warnings: {errors}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        # Safely convert exception to string, handling encoding issues
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred while generating images (encoding error)"
        
        return jsonify({
            "error": f"An error occurred while generating images: {error_msg}",
            "generated_images": []
        }), 500

@app.route('/api/regenerate-images', methods=['POST'])
def regenerate_images():
    """
    Regenerate images using a custom prompt.
    
    Accepts JSON body:
    {
        "image_urls": ["url1", "url2", ...],
        "prompt": "custom prompt text"
    }
    
    Returns:
        JSON response with regenerated image URLs, or error message
    """
    try:
        print("[API] /api/regenerate-images endpoint called")
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "Request body must be JSON",
                "generated_images": []
            }), 400
        
        image_urls = data.get("image_urls", [])
        prompt = data.get("prompt", "")
        
        if not image_urls or not isinstance(image_urls, list):
            return jsonify({
                "error": "image_urls must be a non-empty array",
                "generated_images": []
            }), 400
        
        if not prompt or not isinstance(prompt, str) or not prompt.strip():
            return jsonify({
                "error": "prompt must be a non-empty string",
                "generated_images": []
            }), 400
        
        print(f"[API] Regenerating {len(image_urls)} image(s) with custom prompt")
        
        generated_images = []
        errors = []
        
        # Regenerate each image with custom prompt
        # Use EXPERIMENTAL type since we're using custom prompt
        for idx, image_url in enumerate(image_urls):
            try:
                print(f"[API] Regenerating image {idx + 1}/{len(image_urls)}...")
                result = generate_image_from_urls([image_url], ImageType.EXPERIMENTAL, custom_prompt=prompt.strip())
                
                if result and isinstance(result, list):
                    generated_images.extend(result)
                    print(f"[API] Successfully regenerated {len(result)} image(s) for image {idx + 1}")
                elif result:
                    generated_images.append(result)
                    print(f"[API] Successfully regenerated 1 image for image {idx + 1}")
                else:
                    errors.append(f"Failed to regenerate image {idx + 1}")
            except Exception as e:
                error_msg = f"Error regenerating image {idx + 1}: {str(e)}"
                print(f"[API] Exception: {error_msg}")
                import traceback
                traceback.print_exc()
                errors.append(error_msg)
        
        print(f"[API] Regeneration complete: {len(generated_images)} images generated, {len(errors)} errors")
        
        response_data = {
            "generated_images": generated_images,
            "error": None
        }
        
        if errors:
            response_data["warnings"] = errors
        
        return jsonify(response_data), 200
        
    except Exception as e:
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred while regenerating images (encoding error)"
        
        return jsonify({
            "error": f"An error occurred while regenerating images: {error_msg}",
            "generated_images": []
        }), 500

@app.route('/api/create-listing', methods=['POST'])
def create_listing():
    """
    Create a new listing JSON file with generated images, generate optimized text, and update listing.
    
    Accepts JSON body:
    {
        "generated_images": ["url1", "url2", ...],
        "listing": {
            "title": "...",
            "description": "...",
            "price": "...",
            "categoryId": "...",
            ...
        }
    }
    
    Returns:
        JSON response with complete listing data, or error message
    """
    try:
        print("[API] /api/create-listing endpoint called")
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "Request body must be JSON",
                "listing_data": None
            }), 400
        
        generated_images = data.get("generated_images", [])
        listing = data.get("listing", {})
        
        if not generated_images or not isinstance(generated_images, list):
            return jsonify({
                "error": "generated_images must be a non-empty array",
                "listing_data": None
            }), 400
        
        if not listing:
            return jsonify({
                "error": "listing data is required",
                "listing_data": None
            }), 400
        
        print(f"[API] Creating listing with {len(generated_images)} image(s)")
        
        # Generate new SKU
        sku = get_next_sku()
        print(f"[API] Generated SKU: {sku}")
        
        # Create listing with default structure
        create_listing_with_preferences(sku=sku)
        print(f"[API] Created listing JSON file for SKU: {sku}")
        
        # Add images to listing
        update_listing_images(sku, generated_images)
        print(f"[API] Added {len(generated_images)} image(s) to listing")
        
        # Generate optimized text
        old_title = listing.get("title", "")
        old_description = listing.get("description", "")
        
        if old_title and old_description:
            print(f"[API] Generating optimized text...")
            optimized_content = create_text(old_title, old_description)
            
            if optimized_content:
                update_listing_title_description(sku, optimized_content)
                print(f"[API] Updated listing with optimized text")
            else:
                print(f"[API] Warning: Failed to generate optimized text, using original")
                # Use original text if optimization fails
                optimized_content = {
                    "edited_title": old_title,
                    "edited_description": old_description
                }
                update_listing_title_description(sku, optimized_content)
        else:
            print(f"[API] Warning: No title/description provided, skipping text generation")
        
        # Update metadata (price and category)
        price = listing.get("price", "0")
        category_id = listing.get("categoryId", "")
        
        if price and category_id:
            update_listing_meta_data(sku, str(price), str(category_id))
            print(f"[API] Updated listing metadata: price={price}, categoryId={category_id}")
        
        # Load and return the complete listing data
        listing_data = load_listing_data(sku=sku)
        
        if not listing_data:
            return jsonify({
                "error": "Failed to load created listing data",
                "listing_data": None
            }), 500
        
        print(f"[API] Successfully created listing: {sku}")
        
        return jsonify({
            "listing_data": listing_data,
            "error": None
        }), 200
        
    except Exception as e:
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred while creating listing (encoding error)"
        
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "error": f"An error occurred while creating listing: {error_msg}",
            "listing_data": None
        }), 500

@app.route('/api/listings', methods=['GET'])
def list_all_listings():
    """
    Get all generated listings from the Generated_Listings folder.
    
    Returns:
        JSON response with list of all listings (summary data), or error message
    """
    try:
        print("[API] /api/listings endpoint called")
        output_dir = "Generated_Listings"
        
        if not os.path.exists(output_dir):
            return jsonify({
                "listings": [],
                "error": None
            }), 200
        
        listings = []
        
        # Get all JSON files in the directory
        for filename in os.listdir(output_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(output_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        listing_data = json.load(f)
                    
                    # Extract summary information
                    sku = listing_data.get('sku', filename.replace('.json', ''))
                    title = listing_data.get('inventoryItem', {}).get('product', {}).get('title', 'No title')
                    price = listing_data.get('offer', {}).get('pricingSummary', {}).get('price', {}).get('value', 'N/A')
                    category_id = listing_data.get('offer', {}).get('categoryId', 'N/A')
                    created_date = listing_data.get('createdDateTime', '')
                    image_count = len(listing_data.get('inventoryItem', {}).get('product', {}).get('imageUrls', []))
                    
                    listings.append({
                        'sku': sku,
                        'title': title,
                        'price': price,
                        'categoryId': category_id,
                        'createdDateTime': created_date,
                        'imageCount': image_count,
                        'filename': filename,
                        'fileSku': filename.replace('.json', '')  # SKU derived from filename
                    })
                except Exception as e:
                    print(f"[API] Error reading {filename}: {e}")
                    continue
        
        # Sort by created date (newest first)
        listings.sort(key=lambda x: x.get('createdDateTime', ''), reverse=True)
        
        print(f"[API] Found {len(listings)} listing(s)")
        
        return jsonify({
            "listings": listings,
            "error": None
        }), 200
        
    except Exception as e:
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred while listing files (encoding error)"
        
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "error": f"An error occurred while listing files: {error_msg}",
            "listings": []
        }), 500

@app.route('/api/listings/<sku>', methods=['GET'])
def get_listing_detail(sku):
    """
    Get full details of a specific listing by SKU.
    
    Args:
        sku: The SKU of the listing to retrieve
    
    Returns:
        JSON response with complete listing data, or error message
    """
    try:
        print(f"[API] /api/listings/{sku} endpoint called")
        
        listing_data = load_listing_data(sku=sku)
        
        if not listing_data:
            return jsonify({
                "error": f"Listing not found for SKU: {sku}",
                "listing_data": None
            }), 404
        
        print(f"[API] Successfully loaded listing data for SKU: {sku}")
        
        return jsonify({
            "listing_data": listing_data,
            "error": None
        }), 200
        
    except Exception as e:
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred while fetching listing (encoding error)"
        
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "error": f"An error occurred while fetching listing: {error_msg}",
            "listing_data": None
        }), 500

@app.route('/api/upload-listing', methods=['POST'])
def upload_listing():
    """
    Upload a listing to eBay using upload_complete_listing.
    
    Accepts JSON body:
    {
        "sku": "AXIS_1"
    }
    
    Returns:
        JSON response with upload result including listing ID, or error message
    """
    try:
        print("[API] /api/upload-listing endpoint called")
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "Request body must be JSON",
                "upload_result": None
            }), 400
        
        sku = data.get("sku")
        filename = data.get("filename")  # Optional: use filename if provided
        
        if not sku or not isinstance(sku, str):
            return jsonify({
                "error": "sku must be a non-empty string",
                "upload_result": None
            }), 400
        
        print(f"[API] Uploading listing to eBay with SKU: {sku}")
        if filename:
            print(f"[API] Using filename: {filename}")
        
        # Load listing data from JSON file
        # Try filename first if provided, otherwise use SKU
        if filename:
            listing_data = load_listing_data(filename=filename)
        else:
            listing_data = load_listing_data(sku=sku)
        
        # If that fails, try using SKU as filename
        if not listing_data:
            print(f"[API] First attempt failed, trying SKU as filename: {sku}.json")
            listing_data = load_listing_data(filename=f"{sku}.json")
        
        if not listing_data:
            return jsonify({
                "error": f"Failed to load listing data for SKU: {sku}",
                "upload_result": None
            }), 404
        
        # Extract inventory and offer data
        inventory_item_data = listing_data.get("inventoryItem", {}).copy()
        offer_data = listing_data.get("offer", {}).copy()
        
        if not inventory_item_data or not offer_data:
            return jsonify({
                "error": "Listing data is missing inventoryItem or offer",
                "upload_result": None
            }), 400
        
        # Validate required fields
        product = inventory_item_data.get("product", {})
        if not product.get("title") or product.get("title") == "[need to change]":
            return jsonify({
                "error": "Listing title is missing or not set. Please update the title before uploading.",
                "upload_result": None
            }), 400
        
        if not product.get("imageUrls") or len(product.get("imageUrls", [])) == 0:
            return jsonify({
                "error": "Listing has no images. Please add images before uploading.",
                "upload_result": None
            }), 400
        
        # Use SKU from loaded data
        actual_sku = listing_data.get("sku", sku)
        
        print(f"[API] Calling upload_complete_listing for SKU: {actual_sku}")
        print(f"[API] Title: {product.get('title', 'N/A')}")
        print(f"[API] Image count: {len(product.get('imageUrls', []))}")
        print(f"[API] Price: {offer_data.get('pricingSummary', {}).get('price', {}).get('value', 'N/A')}")
        
        # Upload to eBay using upload_complete_listing function
        try:
            upload_result = upload_complete_listing(
                sku=actual_sku,
                inventory_item_data=inventory_item_data,
                offer_data=offer_data,
                locale="en-US",
                use_user_token=True
            )
        except Exception as upload_exception:
            error_msg = str(upload_exception)
            print(f"[API] Exception during upload_complete_listing: {error_msg}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "error": f"Exception during upload: {error_msg}",
                "upload_result": None
            }), 500
        
        if not upload_result:
            print(f"[API] upload_complete_listing returned None - upload failed")
            return jsonify({
                "error": "Failed to upload listing to eBay. Check server logs for details.",
                "upload_result": None
            }), 500
        
        print(f"[API] Successfully uploaded listing to eBay")
        print(f"[API] Upload result: {upload_result}")
        print(f"[API] Upload result type: {type(upload_result)}")
        print(f"[API] Upload result keys: {list(upload_result.keys()) if isinstance(upload_result, dict) else 'Not a dict'}")
        
        return jsonify({
            "upload_result": upload_result,
            "error": None
        }), 200
        
    except Exception as e:
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred while uploading listing (encoding error)"
        
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "error": f"An error occurred while uploading listing: {error_msg}",
            "upload_result": None
        }), 500

@app.route('/api/listings', methods=['GET'])
def get_all_listings():
    """
    Get all generated listings from the Generated_Listings folder.
    
    Returns:
        JSON response with list of all listings with summary data
    """
    try:
        print("[API] /api/listings endpoint called")
        output_dir = "Generated_Listings"
        
        if not os.path.exists(output_dir):
            return jsonify({
                "listings": [],
                "error": None
            }), 200
        
        # Get all JSON files in the directory
        pattern = os.path.join(output_dir, "*.json")
        json_files = glob.glob(pattern)
        
        listings = []
        
        for filepath in json_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    listing_data = json.load(f)
                
                # Extract summary information
                sku = listing_data.get("sku", "")
                title = listing_data.get("inventoryItem", {}).get("product", {}).get("title", "[No Title]")
                description = listing_data.get("inventoryItem", {}).get("product", {}).get("description", "")
                price = listing_data.get("offer", {}).get("pricingSummary", {}).get("price", {}).get("value", "0")
                currency = listing_data.get("offer", {}).get("pricingSummary", {}).get("price", {}).get("currency", "USD")
                category_id = listing_data.get("offer", {}).get("categoryId", "")
                image_urls = listing_data.get("inventoryItem", {}).get("product", {}).get("imageUrls", [])
                created_date = listing_data.get("createdDateTime", "")
                quantity = listing_data.get("offer", {}).get("quantity", 0)
                
                listings.append({
                    "sku": sku,
                    "title": title,
                    "description": description[:200] + "..." if len(description) > 200 else description,
                    "price": price,
                    "currency": currency,
                    "categoryId": category_id,
                    "imageCount": len(image_urls),
                    "imageUrls": image_urls[:3],  # First 3 images for preview
                    "createdDateTime": created_date,
                    "quantity": quantity
                })
            except Exception as e:
                print(f"[API] Error loading listing file {filepath}: {e}")
                continue
        
        # Sort by created date (newest first)
        listings.sort(key=lambda x: x.get("createdDateTime", ""), reverse=True)
        
        print(f"[API] Found {len(listings)} listing(s)")
        
        return jsonify({
            "listings": listings,
            "error": None
        }), 200
        
    except Exception as e:
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred while fetching listings (encoding error)"
        
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "listings": [],
            "error": f"An error occurred while fetching listings: {error_msg}"
        }), 500

@app.route('/api/testing', methods=['POST'])
def run_testing_function():
    """
    Run the testing_function from CopyListingMain.
    
    Accepts JSON body:
    {
        "id": "optional_id_parameter"
    }
    
    Returns:
        JSON response with result or error message
    """
    try:
        print("[API] /api/testing endpoint called")
        data = request.get_json() or {}
        
        id_param = data.get("id")
        print(f"[API] Testing function called with id: {id_param}")
        
        # Call the testing function with id parameter
        result = testing_function(id=id_param)
        
        print("[API] Testing function completed")
        
        return jsonify({
            "result": result if result is not None else "Testing function executed successfully",
            "error": None
        }), 200
        
    except Exception as e:
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred while running testing function (encoding error)"
        
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "error": f"An error occurred while running testing function: {error_msg}",
            "result": None
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
