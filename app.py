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

from flask import Flask, jsonify, request, Response, stream_with_context
from flask_cors import CORS
from copyScripts.CopyListingMain import copy_listing_main, testing_function
from copyScripts.create_image import generate_image_from_urls, ImageType, categorize_images
from copyScripts.combine_data import get_next_sku, create_listing_with_preferences, update_listing_images, update_listing_title_description, update_listing_meta_data, load_listing_data, update_listing_with_aspects
from helper_functions import remove_html_tags
import os
import json
import os
import glob
import time
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from copyScripts.create_text import create_text
from copyScripts.imageEditing import remove_background, compile_images
from copyScripts.upload_to_ebay import upload_complete_listing

app = Flask(__name__)
# Enable CORS for all routes to allow React frontend to make requests
CORS(app, origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"])

# In-memory storage for image generation task progress
# Structure: {task_id: {"status": "running|completed|failed", "total": N, "completed": M, "results": [], "errors": []}}
image_generation_tasks = {}
image_generation_lock = threading.Lock()

# --- Streaming progress helpers (NDJSON) ---
def progress_event(step, status):
    """Send a progress event as an NDJSON line."""
    return json.dumps({"type": "progress", "step": step, "status": status}) + "\n"

def result_event(data):
    """Send a final result event as an NDJSON line."""
    return json.dumps({"type": "result", "data": data}) + "\n"

def error_event(error_msg):
    """Send an error event as an NDJSON line."""
    return json.dumps({"type": "error", "error": error_msg}) + "\n"

def streaming_response(generator):
    """Wrap a generator in a streaming Flask Response with proper headers."""
    return Response(
        stream_with_context(generator),
        mimetype='application/x-ndjson',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

@app.route('/api/photos/<path:listing_id>', methods=['GET'])
def get_listing_photos(listing_id):
    """
    Fetch photos and listing details for a given eBay listing ID or URL.
    Streams real-time progress events as NDJSON so the frontend can show accurate status.
    """
    def generate():
        try:
            from main_ebay_commands import single_get_detailed_item_data

            # Parse ID from URL if needed
            item_id = listing_id
            if item_id and (item_id[0] == 'h' or item_id[0] == 'e'):
                item_id = item_id.split('/itm/')[1].split('?')[0]

            # Step 1: Fetch listing from eBay
            yield progress_event('Fetching listing from eBay', 'in_progress')
            listing = single_get_detailed_item_data(item_id, verbose=True)

            if not listing:
                yield error_event("Failed to fetch listing data. The listing may not exist or the ID is invalid.")
                return

            yield progress_event('Fetching listing from eBay', 'completed')

            # Step 2: Create initial JSON file
            yield progress_event('Creating initial JSON file', 'in_progress')
            new_sku = create_listing_with_preferences()
            yield progress_event('Creating initial JSON file', 'completed')

            # Extract photo URLs
            old_photo_list = [
                url for url in
                [listing.get("image", {}).get("imageUrl")] +
                [img.get("imageUrl") for img in listing.get("additionalImages", []) if isinstance(img, dict)]
                if url
            ]
            print(f"Found {len(old_photo_list)} photo(s): {old_photo_list}")

            # Step 3: Categorize images
            yield progress_event('Categorizing images', 'in_progress')
            categories = {}
            if old_photo_list:
                print("Categorizing images...")
                categories = categorize_images(old_photo_list)
                if categories is None:
                    categories = {}
            yield progress_event('Categorizing images', 'completed')

            # Send final result
            result = {
                "sku": new_sku,
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
                    "localizedAspects": listing.get('localizedAspects', [])
                },
                "error": None
            }
            yield result_event(result)

        except Exception as e:
            try:
                error_msg = str(e)
            except UnicodeEncodeError:
                error_msg = "An error occurred while fetching listing data (encoding error)"
            yield error_event(f"An error occurred while fetching listing data: {error_msg}")

    return streaming_response(generate())

@app.route('/api/generate-images-status/<task_id>', methods=['GET'])
def get_generation_status(task_id):
    """
    Get status of image generation task.
    
    Returns:
        JSON response with task status, progress, and results if completed
    """
    try:
        with image_generation_lock:
            if task_id not in image_generation_tasks:
                return jsonify({
                    "error": f"Task {task_id} not found",
                    "status": None
                }), 404
            
            task = image_generation_tasks[task_id]
            
            response_data = {
                "status": task["status"],
                "total": task["total"],
                "completed": task["completed"],
                "errors": task["errors"]
            }
            
            # Include results if completed
            if task["status"] == "completed":
                response_data["generated_images"] = task["results"]
            elif task["status"] == "failed":
                response_data["generated_images"] = task["results"]  # Return partial results if any
            
            return jsonify(response_data), 200
            
    except Exception as e:
        return jsonify({
            "error": f"An error occurred while checking status: {str(e)}",
            "status": None
        }), 500

def generate_image_with_delay(photo_url, image_type, index, delay_ms=500, task_id=None, prompt_modifier=None):
    """
    Generate image with rate limiting delay. Used for parallel execution.
    
    Args:
        photo_url: URL of photo to generate from
        image_type: ImageType enum value
        index: Index of this image (for ordering and delay calculation)
        delay_ms: Delay in milliseconds before starting generation
        task_id: Task ID for progress tracking
        prompt_modifier: Optional additional text to append to each image's prompt
    
    Returns:
        tuple: (index, photo_url, result, error)
    """
    try:
        # Stagger API calls to avoid rate limits
        time.sleep(index * delay_ms / 1000)
        
        # Update progress: starting
        if task_id:
            with image_generation_lock:
                if task_id in image_generation_tasks:
                    image_generation_tasks[task_id]["status"] = "running"
        
        print(f"[API] Starting generation for image {index + 1} (photo: {photo_url[:50]}...)")
        
        # Generate image
        result = generate_image_from_urls([photo_url], image_type, prompt_modifier=prompt_modifier)
        
        # Update progress: completed
        if task_id:
            with image_generation_lock:
                if task_id in image_generation_tasks:
                    if result:
                        image_generation_tasks[task_id]["completed"] += 1
                        if isinstance(result, list):
                            image_generation_tasks[task_id]["results"].extend(result)
                        else:
                            image_generation_tasks[task_id]["results"].append(result)
                    else:
                        image_generation_tasks[task_id]["errors"].append(f"Failed to generate image for {photo_url[:50]}...")
        
        return (index, photo_url, result, None)
    except Exception as e:
        error_msg = f"Error generating image for {photo_url[:50]}...: {str(e)}"
        print(f"[API] Exception: {error_msg}")
        import traceback
        traceback.print_exc()
        
        # Update progress: error
        if task_id:
            with image_generation_lock:
                if task_id in image_generation_tasks:
                    image_generation_tasks[task_id]["errors"].append(error_msg)
                    image_generation_tasks[task_id]["completed"] += 1
        
        return (index, photo_url, None, error_msg)

@app.route('/api/generate-images', methods=['POST'])
def generate_images():
    """
    Generate images based on confirmed categories using parallel async processing.
    
    Accepts JSON body:
    {
        "photos": ["url1", "url2", ...],
        "categories": {"url1": "bad_image", "url2": "professional_image", ...}
    }
    
    Returns:
        JSON response with task_id for progress tracking, or error message
    """
    try:
        print("[API] /api/generate-images endpoint called")
        data = request.get_json()
        print(f"[API] Received data: photos={len(data.get('photos', [])) if data else 0}, categories={len(data.get('categories', {})) if data else 0}")
        
        if not data:
            print("[API] Error: No data in request")
            return jsonify({
                "error": "Request body must be JSON",
                "task_id": None
            }), 400
        
        photos = data.get("photos", [])
        categories = data.get("categories", {})
        prompt_modifier = data.get("prompt_modifier", "")
        
        print(f"[API] Processing {len(photos)} photos with {len(categories)} categories")
        if prompt_modifier:
            print(f"[API] Prompt modifier: {prompt_modifier}")
        
        if not photos or not isinstance(photos, list):
            print("[API] Error: Invalid photos array")
            return jsonify({
                "error": "photos must be a non-empty array",
                "task_id": None
            }), 400
        
        if not categories or not isinstance(categories, dict):
            print("[API] Error: Invalid categories dict")
            return jsonify({
                "error": "categories must be a non-empty dictionary",
                "task_id": None
            }), 400
        
        # Categories to skip
        skip_categories = ['real_world_image', 'edited_image']
        
        # Map categories to ImageType
        category_to_image_type = {
            'bad_image': ImageType.REAL_WORLD,
            'professional_image': ImageType.PROFESSIONAL
        }
        
        # Prepare tasks for parallel execution
        tasks_to_generate = []
        for idx, photo_url in enumerate(photos):
            category = categories.get(photo_url)
            
            # Skip if category is None or in skip list
            if not category or category in skip_categories:
                print(f"[API] Skipping photo {idx + 1}: category={category} (None or in skip list)")
                continue
            
            # Get ImageType for this category
            image_type = category_to_image_type.get(category)
            
            if not image_type:
                print(f"[API] Unknown category '{category}' for photo {photo_url[:50]}...")
                continue
            
            tasks_to_generate.append((idx, photo_url, image_type))
        
        if not tasks_to_generate:
            return jsonify({
                "error": "No photos to generate (all skipped or invalid categories)",
                "task_id": None
            }), 400
        
        # Create task ID for progress tracking
        task_id = str(uuid.uuid4())
        
        # Initialize task progress
        with image_generation_lock:
            image_generation_tasks[task_id] = {
                "status": "running",
                "total": len(tasks_to_generate),
                "completed": 0,
                "results": [],
                "errors": []
            }
        
        print(f"[API] Created task {task_id} for {len(tasks_to_generate)} image(s)")
        
        # Start parallel generation in background thread
        def run_generation():
            try:
                with ThreadPoolExecutor(max_workers=5) as executor:
                    # Submit all tasks
                    futures = {}
                    for idx, photo_url, image_type in tasks_to_generate:
                        future = executor.submit(
                            generate_image_with_delay,
                            photo_url, image_type, idx, delay_ms=500, task_id=task_id,
                            prompt_modifier=prompt_modifier if prompt_modifier else None
                        )
                        futures[future] = (idx, photo_url)
                    
                    # Wait for all to complete
                    for future in as_completed(futures):
                        idx, photo_url = futures[future]
                        try:
                            result = future.result()
                            # Result already processed in generate_image_with_delay
                        except Exception as e:
                            print(f"[API] Future exception for image {idx + 1}: {e}")
                
                # Mark task as completed
                with image_generation_lock:
                    if task_id in image_generation_tasks:
                        image_generation_tasks[task_id]["status"] = "completed"
                
                print(f"[API] Task {task_id} completed: {len(image_generation_tasks[task_id]['results'])} images generated")
            except Exception as e:
                print(f"[API] Error in background generation thread: {e}")
                import traceback
                traceback.print_exc()
                with image_generation_lock:
                    if task_id in image_generation_tasks:
                        image_generation_tasks[task_id]["status"] = "failed"
                        image_generation_tasks[task_id]["errors"].append(str(e))
        
        # Start background thread
        thread = threading.Thread(target=run_generation, daemon=True)
        thread.start()
        
        # Return task ID immediately
        return jsonify({
            "task_id": task_id,
            "total_images": len(tasks_to_generate),
            "error": None
        }), 200
        
    except Exception as e:
        # Safely convert exception to string, handling encoding issues
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred while generating images (encoding error)"
        
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "error": f"An error occurred while generating images: {error_msg}",
            "task_id": None
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
    Update an existing listing JSON file with generated images, generate optimized text, and update listing.
    Streams real-time progress events as NDJSON so the frontend can show accurate status.
    """
    # Parse request body before streaming (can't access request inside generator after response starts)
    data = request.get_json()

    def generate():
        try:
            print("[API] /api/create-listing endpoint called")

            if not data:
                yield error_event("Request body must be JSON")
                return

            generated_images = data.get("generated_images", [])
            listing = data.get("listing", {})
            sku = data.get("sku")

            if not generated_images or not isinstance(generated_images, list):
                yield error_event("generated_images must be a non-empty array")
                return
            if not listing:
                yield error_event("listing data is required")
                return
            if not sku:
                yield error_event("sku is required in request body")
                return

            print(f"[API] Updating listing with {len(generated_images)} image(s)")
            print(f"[API] Using SKU: {sku}")

            # Step 1: Updating images
            yield progress_event('Updating images', 'in_progress')

            from copyScripts.combine_data import listing_file_exists
            if not listing_file_exists(sku):
                print(f"[API] File doesn't exist for SKU {sku}, creating it...")
                create_listing_with_preferences(sku=sku)
                print(f"[API] Created listing JSON file for SKU: {sku}")
            else:
                print(f"[API] File exists for SKU {sku}, updating existing file")

            update_listing_images(sku, generated_images)
            print(f"[API] Added {len(generated_images)} image(s) to listing")
            yield progress_event('Updating images', 'completed')

            # Step 2: Generating optimized text
            yield progress_event('Generating optimized text', 'in_progress')

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
                    optimized_content = {
                        "edited_title": old_title,
                        "edited_description": old_description
                    }
                    update_listing_title_description(sku, optimized_content)
            else:
                print(f"[API] Warning: No title/description provided, skipping text generation")

            yield progress_event('Generating optimized text', 'completed')

            # Step 3: Updating metadata
            yield progress_event('Updating metadata', 'in_progress')

            price = listing.get("price", "0")
            category_id = listing.get("categoryId", "")

            if price and category_id:
                update_listing_meta_data(sku, str(price), str(category_id))
                print(f"[API] Updated listing metadata: price={price}, categoryId={category_id}")

            yield progress_event('Updating metadata', 'completed')

            # Step 4: Updating aspects
            yield progress_event('Updating aspects', 'in_progress')

            localized_aspects = listing.get("localizedAspects")
            if localized_aspects is None:
                localized_aspects = []
            update_listing_with_aspects(sku, localized_aspects)
            print(f"[API] Updated listing with aspects")

            yield progress_event('Updating aspects', 'completed')

            # Load and return the complete listing data
            listing_data = load_listing_data(sku=sku)

            if not listing_data:
                yield error_event("Failed to load created listing data")
                return

            print(f"[API] Successfully created listing: {sku}")

            yield result_event({
                "listing_data": listing_data,
                "error": None
            })

        except Exception as e:
            try:
                error_msg = str(e)
            except UnicodeEncodeError:
                error_msg = "An error occurred while creating listing (encoding error)"

            import traceback
            traceback.print_exc()

            yield error_event(f"An error occurred while creating listing: {error_msg}")

    return streaming_response(generate())

@app.route('/api/listings', methods=['GET'])
def list_all_listings():
    """
    Get all generated listings from the Generated_Listings folder.
    
    Returns:
        JSON response with list of all listings (summary data), or error message
    """
    try:
        print("[API] /api/listings endpoint called")
        # Use absolute path to ensure we're looking in the right directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(base_dir, "Generated_Listings")
        
        if not os.path.exists(output_dir):
            print(f"[API] Generated_Listings directory does not exist at: {output_dir}")
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
                    description = listing_data.get('inventoryItem', {}).get('product', {}).get('description', '')
                    price = listing_data.get('offer', {}).get('pricingSummary', {}).get('price', {}).get('value', 'N/A')
                    currency = listing_data.get('offer', {}).get('pricingSummary', {}).get('price', {}).get('currency', 'USD')
                    category_id = listing_data.get('offer', {}).get('categoryId', 'N/A')
                    created_date = listing_data.get('createdDateTime', '')
                    image_urls = listing_data.get('inventoryItem', {}).get('product', {}).get('imageUrls', [])
                    image_count = len(image_urls)
                    quantity = listing_data.get('offer', {}).get('quantity', 0)
                    
                    listings.append({
                        'sku': sku,
                        'title': title,
                        'description': description[:200] + "..." if len(description) > 200 else description,
                        'price': price,
                        'currency': currency,
                        'categoryId': category_id,
                        'createdDateTime': created_date,
                        'imageCount': image_count,
                        'imageUrls': image_urls[:3],  # First 3 images for preview
                        'quantity': quantity,
                        'filename': filename,
                        'fileSku': filename.replace('.json', '')  # SKU derived from filename
                    })
                except Exception as e:
                    print(f"[API] Error reading {filename}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        # Sort by created date (newest first)
        listings.sort(key=lambda x: x.get('createdDateTime', ''), reverse=True)
        
        print(f"[API] Found {len(listings)} listing(s) in {output_dir}")
        
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
    Streams real-time progress events as NDJSON so the frontend can show accurate status.
    """
    # Parse request body before streaming
    data = request.get_json()

    def generate():
        try:
            print("[API] /api/upload-listing endpoint called")

            if not data:
                yield error_event("Request body must be JSON")
                return

            sku = data.get("sku")
            filename = data.get("filename")

            if not sku or not isinstance(sku, str):
                yield error_event("sku must be a non-empty string")
                return

            print(f"[API] Uploading listing to eBay with SKU: {sku}")
            if filename:
                print(f"[API] Using filename: {filename}")

            # Step 1: Preparing listing data
            yield progress_event('Preparing listing data', 'in_progress')

            if filename:
                listing_data = load_listing_data(filename=filename)
            else:
                listing_data = load_listing_data(sku=sku)

            if not listing_data:
                print(f"[API] First attempt failed, trying SKU as filename: {sku}.json")
                listing_data = load_listing_data(filename=f"{sku}.json")

            if not listing_data:
                yield error_event(f"Failed to load listing data for SKU: {sku}")
                return

            inventory_item_data = listing_data.get("inventoryItem", {}).copy()
            offer_data = listing_data.get("offer", {}).copy()

            if not inventory_item_data or not offer_data:
                yield error_event("Listing data is missing inventoryItem or offer")
                return

            product = inventory_item_data.get("product", {})
            if not product.get("title") or product.get("title") == "[need to change]":
                yield error_event("Listing title is missing or not set. Please update the title before uploading.")
                return

            if not product.get("imageUrls") or len(product.get("imageUrls", [])) == 0:
                yield error_event("Listing has no images. Please add images before uploading.")
                return

            actual_sku = listing_data.get("sku", sku)

            print(f"[API] Calling upload_complete_listing for SKU: {actual_sku}")
            print(f"[API] Title: {product.get('title', 'N/A')}")
            print(f"[API] Image count: {len(product.get('imageUrls', []))}")
            print(f"[API] Price: {offer_data.get('pricingSummary', {}).get('price', {}).get('value', 'N/A')}")

            yield progress_event('Preparing listing data', 'completed')

            # Step 2: Uploading to eBay
            yield progress_event('Uploading to eBay', 'in_progress')

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
                yield error_event(f"Exception during upload: {error_msg}")
                return

            if not upload_result:
                print(f"[API] upload_complete_listing returned None - upload failed")
                yield error_event("Failed to upload listing to eBay. Check server logs for details.")
                return

            print(f"[API] Successfully uploaded listing to eBay")
            print(f"[API] Upload result: {upload_result}")

            yield progress_event('Uploading to eBay', 'completed')

            yield result_event({
                "upload_result": upload_result,
                "error": None
            })

        except Exception as e:
            try:
                error_msg = str(e)
            except UnicodeEncodeError:
                error_msg = "An error occurred while uploading listing (encoding error)"

            import traceback
            traceback.print_exc()

            yield error_event(f"An error occurred while uploading listing: {error_msg}")

    return streaming_response(generate())


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

@app.route('/api/remove-background', methods=['POST'])
def api_remove_background():
    """
    Remove the background from an uploaded image using rembg.
    
    Accepts a multipart/form-data request with an 'image' file field.
    
    Returns:
        PNG image with background removed (transparent).
    """
    try:
        file = request.files.get('image')
        if not file:
            return jsonify({"error": "No image file provided"}), 400

        print(f"[API] /api/remove-background called with file: {file.filename}")
        image_bytes = file.read()
        result_bytes = remove_background(image_bytes)
        print("[API] Background removal completed successfully")

        return Response(result_bytes, mimetype='image/png')

    except Exception as e:
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred during background removal (encoding error)"

        import traceback
        traceback.print_exc()

        return jsonify({
            "error": f"An error occurred during background removal: {error_msg}"
        }), 500


@app.route('/api/compile-canvas', methods=['POST'])
def api_compile_canvas():
    """
    Compile multiple images onto a canvas with transforms.
    
    Accepts JSON body:
    {
        "layers": [
            {
                "image_base64": "base64-encoded image data",
                "left": 0,
                "top": 0,
                "scaleX": 1,
                "scaleY": 1,
                "angle": 0
            }
        ],
        "canvasWidth": 1080,
        "canvasHeight": 1080,
        "bgColor": "#FFFFFF"
    }
    
    Returns:
        PNG image of the composed canvas.
    """
    try:
        data = request.get_json()
        if not data or 'layers' not in data:
            return jsonify({"error": "No layers provided"}), 400

        print(f"[API] /api/compile-canvas called with {len(data['layers'])} layers")

        layers = data['layers']
        canvas_width = data.get('canvasWidth', 1080)
        canvas_height = data.get('canvasHeight', 1080)
        bg_color = data.get('bgColor', '#FFFFFF')

        result_bytes = compile_images(
            layers=layers,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            bg_color=bg_color
        )

        print("[API] Canvas compilation completed successfully")
        return Response(result_bytes, mimetype='image/png')

    except Exception as e:
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred during canvas compilation (encoding error)"

        import traceback
        traceback.print_exc()

        return jsonify({
            "error": f"An error occurred during canvas compilation: {error_msg}"
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
