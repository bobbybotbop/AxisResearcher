"""
Flask API for eBay Listing Photo Gallery

This Flask application provides a REST API endpoint to fetch photos
and listing details from eBay listings.
"""

import sys
import io

class _SafeStream:
    """Wraps a stream so any OSError (e.g. Windows invalid handle) is silently swallowed."""
    def __init__(self, stream):
        self._stream = stream
    def write(self, s):
        try:
            return self._stream.write(s)
        except OSError:
            return 0
    def flush(self):
        try:
            self._stream.flush()
        except OSError:
            pass
    def __getattr__(self, name):
        return getattr(self._stream, name)

if sys.platform == 'win32':
    try:
        _utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        _utf8_stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        sys.stdout = _SafeStream(_utf8_stdout)
        sys.stderr = _SafeStream(_utf8_stderr)
    except AttributeError:
        sys.stdout = _SafeStream(sys.stdout)
        sys.stderr = _SafeStream(sys.stderr)

from flask import Flask, jsonify, request, Response, stream_with_context
from flask_cors import CORS
from werkzeug.serving import WSGIRequestHandler
from backend.copyScripts.CopyListingMain import copy_listing_main, testing_function
from backend.serp import search_by_image, extract_top_links, filter_links_by_enabled_sites, search_by_text, order_by_site_priority, drop_blacklisted
from backend.downloaders.thingiverse import extract_thing_id, stream_zip as tv_stream_zip, probe as probe_thingiverse, scrape_images as tv_scrape_images, probe_images as probe_images_thingiverse
from backend.downloaders.printables import extract_model_id as printables_model_id, build_zip as printables_build_zip, probe as probe_printables, scrape_images as printables_scrape_images, probe_images as probe_images_printables
from backend.downloaders.makerworld import extract_model_info as mw_extract_model_info, download_3mf as mw_download_3mf, probe as probe_makerworld, open_session as mw_open_session, session_status as mw_session_status, close_session as mw_close_session, scrape_images as mw_scrape_images, probe_images as probe_images_makerworld
from backend.downloaders.cults3d import extract_slug as cults3d_extract_slug, stream_zip as cults3d_stream_zip, probe as probe_cults3d, PaidModelError as Cults3DPaidModelError, load_cookies_from_browser as cults3d_load_cookies_from_browser, scrape_images as cults3d_scrape_images, probe_images as probe_images_cults3d
from backend.downloaders.thangs import extract_model_id as thangs_extract_model_id, build_zip as thangs_build_zip, probe as probe_thangs, PaidModelError as ThangsPaidModelError, scrape_images as thangs_scrape_images, probe_images as probe_images_thangs
from backend.constants.files_3d import DOWNLOAD_MODE_FULL_ZIP, DOWNLOAD_MODE_SINGLE_FILE, DOWNLOAD_MODES
from backend.downloaders.zip_utils import extract_best_3d_file
from backend.image_compare import find_matching_pairs, DEFAULT_THRESHOLD as COMPARE_IMAGES_THRESHOLD
from backend.copyScripts.create_image import (
    generate_image_from_urls,
    ImageType,
    categorize_images,
    _openrouter_response_dict_to_image_bytes_and_mime,
    upload_image_bytes_to_ebay,
)
from backend.copyScripts.combine_data import get_next_sku, create_listing_with_preferences, update_listing_images, update_listing_title_description, update_listing_meta_data, load_listing_data, update_listing_with_aspects, compute_aspects_for_category, save_ebay_listing_id, update_listing_models, get_auto_restock_settings, save_auto_restock_settings, update_local_listing_quantity, extract_metadata_for_llm, get_minimum_images_setting, save_minimum_images_setting, get_manual_import_last_refreshed, save_manual_import_last_refreshed, write_manual_listing_json, get_promoted_listing_settings, save_promoted_listing_settings, get_promoted_listing_campaign_ids, save_promoted_listing_campaign_ids, set_listing_ebay_status, get_operation_cooldown_setting, save_operation_cooldown_setting, migrate_hide_not_found_listings, get_render_settings, save_render_settings, get_render_profiles, save_render_profile, delete_render_profile, get_active_render_profile, set_active_render_profile, validate_rig
from backend.helper_functions import remove_html_tags
from backend.copy_seller import (
    get_title_simplification_config,
    list_pipeline_runs,
    load_pipeline_run,
    run_copy_seller,
    save_title_simplification_config,
)
import os
import json
import sqlite3
import time
from datetime import datetime, timezone
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from backend.copyScripts.create_text import create_text, create_text_stream
from backend.ebay_cli import call_text_llm, get_seller_list, revise_inventory_status_batch, get_item_available_quantity
from backend.copyScripts.imageEditing import remove_background, compile_images, downscale_image_bytes, warm_rembg
from backend.copyScripts.upload_to_ebay import upload_complete_listing
from backend.promoted_listings import promote_listing, PromotionError
from backend.logger import log_event
from backend import db as _db
from backend.constants.models import DEFAULT_TEXT_MODEL, DEFAULT_IMAGE_MODEL, DEFAULT_CLASSIFIER_MODEL, DEFAULT_TITLE_SEARCH_MODEL
from backend.constants.data_browser import DATA_BROWSER_TABLES, DATA_BROWSER_MAX_PAGE_SIZE
from backend.constants.listing import (
    ANGLE_VARIANTS, PROMPT_TYPES, TITLE_MIN_LEN, TITLE_MAX_LEN,
    TITLE_TARGET_LEN, TITLE_MAX_ATTEMPTS, SKIP_CATEGORIES,
    CATEGORY_TO_IMAGE_TYPE, EBAY_STATUS_NOT_FOUND,
)
from backend.constants.ebay import EBAY_MARKETPLACE_ID, EBAY_BROWSE_API_BASE, EBAY_INVENTORY_API_BASE
from backend.constants.paths import GENERATED_IMAGES_DIR, PROMPTS_DIR, SAVED_3D_FILES_DIR as _SAVED_3D_FILES_DIR_NAME
from backend.constants.render import (
    DEFAULT_RENDER_AMBIENT, DEFAULT_RENDER_AZIMUTH, DEFAULT_RENDER_COLOR,
    DEFAULT_RENDER_ELEVATION, DEFAULT_RENDER_EXPOSURE, DEFAULT_RENDER_FILL_ENERGY,
    DEFAULT_RENDER_FINISH, DEFAULT_RENDER_FOV, DEFAULT_RENDER_KEY_ENERGY,
    DEFAULT_RENDER_LAYER_DEPTH, DEFAULT_RENDER_LAYER_HEIGHT_MM,
    DEFAULT_RENDER_RESOLUTION, DEFAULT_RENDER_RIM_ENERGY, DEFAULT_RENDER_ROUGHNESS,
    DEFAULT_RENDER_SHADOW, DEFAULT_RENDER_SHADOW_SOFTNESS,
    RENDER_AMBIENT_MAX, RENDER_ENERGY_MAX, RENDER_EXPOSURE_MAX, RENDER_EXPOSURE_MIN,
    RENDER_FINISHES, RENDER_FOV_RANGE,
    RENDER_LAYER_DEPTH_MAX, RENDER_LAYER_DEPTH_MIN,
    RENDER_LAYER_HEIGHT_MM_MAX, RENDER_LAYER_HEIGHT_MM_MIN,
    RENDER_OUTPUT_PREFIX, RENDER_RESOLUTIONS,
    RENDER_SHADOW_SOFTNESS_MAX, RENDER_SHADOW_SOFTNESS_MIN,
    DEFAULT_RENDER_SHOT_MODE, RENDER_SHOT_MODES,
    SUPPORTED_RENDER_EXTENSIONS,
)
from backend.render import iter_render_progress, RenderError
from backend.render.normalize import normalize_to_render_mesh
from backend.render.camera import compute_blender_camera
from backend.render.validate import validate_fov, validate_resolution, validate_roughness
import re
import shutil
import tempfile
import mimetypes
import requests
from dotenv import load_dotenv

app = Flask(__name__)
# Enable CORS for all routes to allow React frontend to make requests
CORS(app, origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"], expose_headers=["Content-Disposition"])

# In-memory storage for image generation task progress
# Structure: {task_id: {"status": "running|completed|failed", "total": N, "completed": M, "results": [], "errors": []}}
image_generation_tasks = {}
image_generation_lock = threading.Lock()


def _load_listing_file(sku):
    """Read a listing row from axis.db; None if missing/unreadable."""
    _db.ensure_db()
    try:
        return _db.load_listing(sku)
    except Exception:
        return None


def _is_manual_sku(sku):
    """True when the listing file marks this SKU as imported from eBay (not tool-created)."""
    d = _load_listing_file(sku)
    return bool(d and d.get('isManualListing'))


def _manual_item_id(sku):
    """eBay item ID for an imported (manual) listing, from its ebayListingId field."""
    d = _load_listing_file(sku)
    if d and d.get('isManualListing'):
        return str(d.get('ebayListingId') or '').strip()
    return ''


def _verify_failed_skus(
    failed_manual_skus: list,
    failed_axis_skus: list,
) -> set[str]:
    """
    For each failed SKU, check eBay to determine if it truly no longer exists.
    Returns a set of SKUs confirmed to be gone from eBay.

    - MANUAL SKUs: compared against GetSellerList (single call, all active item IDs).
    - AXIS SKUs: checked individually via GET /sell/inventory/v1/inventory_item/{sku}.

    Failures in the eBay check are silently skipped (logged) so a transient
    network issue never incorrectly deactivates a listing.
    """
    confirmed_not_found = set()

    # --- MANUAL SKUs: fetch all active item IDs once, check membership ---
    if failed_manual_skus:
        try:
            active_listings = get_seller_list()
            if active_listings:  # Guard: skip if no active listings (prevents false-positive mass deactivation)
                active_item_ids = {str(item['item_id']) for item in active_listings}
                for sku in failed_manual_skus:
                    item_id = _manual_item_id(sku)
                    if item_id and item_id not in active_item_ids:
                        confirmed_not_found.add(sku)
        except Exception as e:
            print(f"[verify_failed_skus] GetSellerList failed, skipping MANUAL check: {e}")

    # --- AXIS SKUs: check inventory_item endpoint per SKU ---
    user_token = os.getenv('user_token', '').strip()
    if failed_axis_skus and user_token:
        headers = {
            'Authorization': f'Bearer {user_token}',
            'Content-Type': 'application/json',
        }
        for sku in failed_axis_skus:
            try:
                r = requests.get(
                    f'{EBAY_INVENTORY_API_BASE}/inventory_item/{sku}',
                    headers=headers,
                    timeout=10,
                )
                if r.status_code == 404:
                    confirmed_not_found.add(sku)
            except Exception as e:
                print(f"[verify_failed_skus] inventory_item check failed for {sku}: {e}")

    return confirmed_not_found


@app.route('/api/prompts/<prompt_type>', methods=['GET'])
def list_prompts(prompt_type):
    if prompt_type not in PROMPT_TYPES:
        return jsonify({"error": f"Invalid prompt type: {prompt_type}"}), 400
    _db.ensure_db()
    return jsonify({"prompts": _db.list_prompts(prompt_type)}), 200


@app.route('/api/prompts/<prompt_type>', methods=['POST'])
def create_prompt(prompt_type):
    if prompt_type not in PROMPT_TYPES:
        return jsonify({"error": f"Invalid prompt type: {prompt_type}"}), 400
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    name = data.get("name", "").strip()
    content = data.get("content", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    if not content:
        return jsonify({"error": "content is required"}), 400
    if not name.endswith(".txt"):
        name = name + ".txt"
    if any(c in name for c in ("/", "\\", "..")):
        return jsonify({"error": "Invalid filename"}), 400
    _db.ensure_db()
    prompt_name = f"{prompt_type}/{name}"
    if _db.prompt_exists(prompt_name):
        return jsonify({"error": f"Prompt '{name}' already exists"}), 400
    _db.save_prompt(prompt_name, content)
    return jsonify({"name": name}), 201


# --- Streaming progress helpers (NDJSON) ---
def progress_event(step, status, **extra):
    """Send a progress event as an NDJSON line. Extra fields are merged in."""
    return json.dumps({"type": "progress", "step": step, "status": status, **extra}) + "\n"

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

@app.route('/api/research/copy-seller', methods=['POST'])
def research_copy_seller():
    """
    Run the Copy Seller research pipeline for an eBay seller.
    Streams progress events and the final raw (unranked) Product Candidates as NDJSON.
    Body: { seller, top_n?, k?, min_sold? }
    """
    data = request.get_json()

    def generate():
        if not data:
            yield error_event("Request body must be JSON")
            return
        seller = (data.get("seller") or "").strip()
        if not seller:
            yield error_event("seller is required")
            return
        try:
            top_n = int(data.get("top_n", 25))
            k = int(data.get("k", 20))
            min_sold = int(data.get("min_sold", 1))
        except (TypeError, ValueError):
            yield error_event("top_n, k, and min_sold must be integers")
            return
        weights = data.get("weights")
        if weights is not None and not isinstance(weights, dict):
            yield error_event("weights must be an object")
            return

        print(f"[API] /api/research/copy-seller: seller={seller} top_n={top_n} k={k} min_sold={min_sold}")
        for event in run_copy_seller(seller, top_n=top_n, k=k, min_sold=min_sold, weights=weights):
            event_type = event.get("type")
            if event_type == "progress":
                extra = {k: v for k, v in event.items() if k not in ("type", "step", "status")}
                yield progress_event(event.get("step", ""), event.get("status", ""), **extra)
            elif event_type == "result":
                yield result_event(event.get("data"))
            elif event_type == "error":
                yield error_event(event.get("error", "Unknown error"))
            else:
                yield json.dumps(event) + "\n"

    return streaming_response(generate())

@app.route('/api/research/copy-seller/runs', methods=['GET'])
def list_copy_seller_runs():
    """
    List past Copy Seller Pipeline Runs as summaries (newest first).
    Follows the /api/listings read-many-JSON pattern.
    """
    try:
        print("[API] /api/research/copy-seller/runs endpoint called")
        return jsonify({"runs": list_pipeline_runs(), "error": None}), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "runs": []}), 500

@app.route('/api/research/copy-seller/runs/<run_id>', methods=['GET'])
def get_copy_seller_run(run_id):
    """Fetch one full Pipeline Run (input + weights + candidates) by run_id."""
    try:
        print(f"[API] /api/research/copy-seller/runs/{run_id} endpoint called")
        run = load_pipeline_run(run_id)
        if run is None:
            return jsonify({"error": f"Run not found: {run_id}", "run": None}), 404
        return jsonify({"run": run, "error": None}), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "run": None}), 500

@app.route('/api/research/title-simplification', methods=['GET', 'POST'])
def api_title_simplification():
    """
    Read or update the Copy Seller title-simplification config (ticket 07).

    GET:        returns {"stopwords": [...], "max_words": int} — the editable
                knobs behind the deterministic trim.
    POST:       JSON body with any subset of those keys; persists and returns
                the saved state.
    """
    if request.method == 'GET':
        try:
            return jsonify(get_title_simplification_config()), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    body = request.get_json(silent=True) or {}
    try:
        config = save_title_simplification_config(
            stopwords=body.get('stopwords'),
            max_words=body.get('max_words'),
        )
        return jsonify(config), 200
    except (TypeError, ValueError) as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-text', methods=['POST'])
def generate_text():
    """
    Stream AI-optimized title and description tokens as NDJSON.
    Body: { title, description, text_model? }
    Events:
      { "type": "token",   "field": "title"|"description", "delta": "..." }
      { "type": "result",  "data": { "edited_title": "...", "edited_description": "..." } }
      { "type": "nudging", "message": "Adjusting title length..." }
      { "type": "error",   "error": "..." }
    """
    data = request.get_json()

    def generate():
        if not data:
            yield error_event("Request body must be JSON")
            return

        title = data.get("title", "")
        description = data.get("description", "")
        text_model = data.get("text_model") or DEFAULT_TEXT_MODEL
        title_prompt = data.get("title_prompt") or None
        description_prompt = data.get("description_prompt") or None

        if not title:
            yield error_event("title is required")
            return

        try:
            final_result = None
            for event in create_text_stream(
                title, description, model=text_model,
                title_prompt=title_prompt,
                description_prompt=description_prompt,
            ):
                if event.get("type") == "result":
                    final_result = event.get("data", {})
                yield json.dumps(event) + "\n"

            # After streaming completes, nudge title length into [75, 80] if needed
            if final_result and final_result.get("edited_title"):
                pending_title = final_result["edited_title"]
                title_len = len(pending_title)
                if not (TITLE_MIN_LEN <= title_len <= TITLE_MAX_LEN):
                    yield json.dumps({"type": "nudging", "message": "Adjusting title length..."}) + "\n"
                    nudged_title, _ = _nudge_title_length(pending_title, text_model)
                    if nudged_title:
                        # Stream the nudged title char-by-char so the frontend can animate it
                        for char in nudged_title:
                            yield json.dumps({"type": "token", "field": "title", "delta": char}) + "\n"
                        nudged_result = dict(final_result)
                        nudged_result["edited_title"] = nudged_title
                        yield json.dumps({"type": "result", "data": nudged_result}) + "\n"
        except Exception as e:
            yield error_event(f"Text generation failed: {e}")

    return streaming_response(generate())

@app.route('/api/photos/<path:listing_id>', methods=['GET'])
def get_listing_photos(listing_id):
    """
    Fetch photos and listing details for a given eBay listing ID or URL.
    Streams real-time progress events as NDJSON so the frontend can show accurate status.
    """
    def generate():
        try:
            from backend.ebay_cli import single_get_detailed_item_data

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
            try:
                new_sku = create_listing_with_preferences()
                log_event("draft_created", "success", sku=new_sku, sourceListingId=item_id)
            except Exception as create_err:
                log_event("draft_created", "error", sourceListingId=item_id, error=str(create_err))
                raise
            yield progress_event('Creating initial JSON file', 'completed')

            # Extract photo URLs — use aggregated variant images if available
            if listing.get('_all_images'):
                old_photo_list = listing['_all_images']
            else:
                old_photo_list = [
                    url for url in
                    [listing.get("image", {}).get("imageUrl")] +
                    [img.get("imageUrl") for img in listing.get("additionalImages", []) if isinstance(img, dict)]
                    if url
                ]
            print(f"Found {len(old_photo_list)} photo(s): {old_photo_list}")

            classify = request.args.get("classify", "true").lower() != "false"

            # Step 3: Categorize images (skipped when classify=false)
            categories = {}
            if classify:
                classifier_model = request.args.get("classifier_model") or DEFAULT_CLASSIFIER_MODEL
                yield progress_event('Categorizing images', 'in_progress')
                if old_photo_list:
                    print("Categorizing images...")
                    categories = categorize_images(old_photo_list, model=classifier_model)
                    if categories is None:
                        categories = {}
                yield progress_event('Categorizing images', 'completed')
            else:
                print("Skipping image categorization (classify=false)")

            # Pre-fetch aspects for the listing's category so create-listing can skip the Taxonomy API
            category_id = listing.get('categoryId', 'N/A')
            localized_aspects = listing.get('localizedAspects', [])
            pre_fetched_aspects = None
            if category_id and category_id != 'N/A':
                try:
                    pre_fetched_aspects = compute_aspects_for_category(category_id, localized_aspects)
                except Exception as _e:
                    print(f"[API] Warning: aspect pre-fetch failed ({_e}), will retry in create-listing")

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
                    "categoryId": category_id,
                    "estimatedSoldQuantity": listing.get('estimatedAvailabilities', [{}])[0].get('estimatedSoldQuantity') if listing.get('estimatedAvailabilities') else None,
                    "localizedAspects": localized_aspects,
                    "preFetchedAspects": pre_fetched_aspects,
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

def generate_image_with_delay(
    photo_url,
    image_type,
    index,
    delay_ms=500,
    task_id=None,
    prompt_modifier=None,
    extra_instructions=None,
    image_model=None,
    image_resolution=None,
    prompt_filename=None,
):
    """
    Generate image with rate limiting delay. Used for parallel execution.

    Args:
        photo_url: URL of photo to generate from
        image_type: ImageType enum value
        index: Index of this image (for ordering and delay calculation)
        delay_ms: Delay in milliseconds before starting generation
        task_id: Task ID for progress tracking
        prompt_modifier: For ANGLE_VARIANT: the angle string. For other types: appended to prompt.
        extra_instructions: User-supplied text always appended, independent of prompt_modifier.

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
        result = generate_image_from_urls(
            [photo_url],
            image_type,
            prompt_modifier=prompt_modifier,
            extra_instructions=extra_instructions,
            model=image_model or DEFAULT_IMAGE_MODEL,
            image_resolution=image_resolution,
            prompt_filename=prompt_filename,
        )
        
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
        image_model = data.get("image_model") or DEFAULT_IMAGE_MODEL
        image_resolution = data.get("image_resolution") or "1024x1024"
        image_prompt_real_world = data.get("image_prompt_real_world") or None
        image_prompt_professional = data.get("image_prompt_professional") or None
        image_prompt_angle_variant = data.get("image_prompt_angle_variant") or None
        classify_enabled = data.get("classify_enabled", True)

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
        
        skip_categories = SKIP_CATEGORIES
        category_to_image_type = CATEGORY_TO_IMAGE_TYPE
        
        image_prompt_map = {
            ImageType.REAL_WORLD: image_prompt_real_world,
            ImageType.PROFESSIONAL: image_prompt_professional,
            ImageType.ANGLE_VARIANT: image_prompt_angle_variant,
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

        # Inject angle-variant tasks when classifier is off and count is below minimum
        if not classify_enabled:
            try:
                minimum = get_minimum_images_setting()["minimum_images_per_listing"]
            except Exception:
                minimum = 10

            current_count = len(tasks_to_generate)
            deficit = minimum - current_count

            if deficit > 0 and tasks_to_generate:
                source_photos = [photo_url for _, photo_url, _ in tasks_to_generate]
                n_sources = len(source_photos)
                angle_index = 0
                variant_index = len(photos)  # offset index beyond original photos

                for i in range(deficit):
                    source_url = source_photos[i % n_sources]
                    angle = ANGLE_VARIANTS[angle_index % len(ANGLE_VARIANTS)]
                    angle_index += 1
                    tasks_to_generate.append((variant_index, source_url, ImageType.ANGLE_VARIANT, angle))
                    variant_index += 1

                print(f"[API] Added {deficit} angle-variant task(s) to reach minimum {minimum}")

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
                    for task in tasks_to_generate:
                        idx, photo_url, image_type = task[0], task[1], task[2]
                        angle = task[3] if len(task) > 3 else None
                        future = executor.submit(
                            generate_image_with_delay,
                            photo_url, image_type, idx, delay_ms=500, task_id=task_id,
                            prompt_modifier=angle if angle else (prompt_modifier or None),
                            extra_instructions=prompt_modifier if angle else None,
                            image_model=image_model,
                            image_resolution=image_resolution,
                            prompt_filename=image_prompt_map.get(image_type),
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
                
                # Mark task completed or failed based on whether any images succeeded
                with image_generation_lock:
                    if task_id in image_generation_tasks:
                        t = image_generation_tasks[task_id]
                        if t["results"]:
                            t["status"] = "completed"
                        else:
                            t["status"] = "failed"

                with image_generation_lock:
                    t = image_generation_tasks.get(task_id, {})
                print(f"[API] Task {task_id} finished: {len(t.get('results', []))} images generated, {len(t.get('errors', []))} errors")
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
        image_model = data.get("image_model") or DEFAULT_IMAGE_MODEL
        image_resolution = data.get("image_resolution") or "1024x1024"
        image_prompt_experimental = data.get("image_prompt_experimental") or None
        
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
                result = generate_image_from_urls(
                    [image_url],
                    ImageType.EXPERIMENTAL,
                    custom_prompt=prompt.strip(),
                    model=image_model,
                    image_resolution=image_resolution,
                    prompt_filename=image_prompt_experimental,
                )
                
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
            text_model = data.get("text_model") or DEFAULT_TEXT_MODEL
            title_prompt = data.get("title_prompt") or None
            description_prompt = data.get("description_prompt") or None
            pre_generated_text = data.get("pre_generated_text")  # {"edited_title": ..., "edited_description": ...}
            image_model = data.get("image_model") or DEFAULT_IMAGE_MODEL
            classifier_model_body = data.get("classifier_model")
            models_payload = {"text_model": text_model, "image_model": image_model}
            if classifier_model_body:
                models_payload["classifier_model"] = classifier_model_body

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

            from backend.copyScripts.combine_data import listing_file_exists
            if not listing_file_exists(sku):
                print(f"[API] File doesn't exist for SKU {sku}, creating it...")
                create_listing_with_preferences(sku=sku, models=models_payload)
                print(f"[API] Created listing JSON file for SKU: {sku}")
            else:
                print(f"[API] File exists for SKU {sku}, updating existing file")
                update_listing_models(sku, models_payload)

            update_listing_images(sku, generated_images)
            print(f"[API] Added {len(generated_images)} image(s) to listing")
            yield progress_event('Updating images', 'completed')

            # Step 2: Generating optimized text (skip LLM if text was pre-generated client-side)
            yield progress_event('Generating optimized text', 'in_progress')

            old_title = listing.get("title", "")
            old_description = listing.get("description", "")

            pending_title = None
            pending_description = None

            if pre_generated_text and pre_generated_text.get("edited_title"):
                # Text was already generated via /api/generate-text; just persist it
                pending_title = pre_generated_text["edited_title"]
                pending_description = pre_generated_text.get("edited_description", "")
                print(f"[API] Used pre-generated text (skipped LLM)")
            elif old_title and old_description:
                print(f"[API] Generating optimized text...")
                optimized_content = create_text(
                    old_title, old_description, model=text_model,
                    title_prompt=title_prompt,
                    description_prompt=description_prompt,
                )
                if optimized_content:
                    pending_title = optimized_content.get("edited_title", old_title)
                    pending_description = optimized_content.get("edited_description", old_description)
                else:
                    print(f"[API] Warning: Failed to generate optimized text, using original")
                    pending_title = old_title
                    pending_description = old_description
            else:
                print(f"[API] Warning: No title/description provided, skipping text generation")

            if pending_title:
                if not pre_generated_text:
                    # Only nudge if text was NOT pre-generated (nudge already ran in /api/generate-text)
                    title_len = len(pending_title)
                    if not (TITLE_MIN_LEN <= title_len <= TITLE_MAX_LEN):
                        print(
                            f"[API] Title length {title_len} outside [{TITLE_MIN_LEN},{TITLE_MAX_LEN}], "
                            f"auto-nudging..."
                        )
                        nudged_title, nudge_log = _nudge_title_length(pending_title, text_model)
                        if nudged_title:
                            pending_title = nudged_title
                            print(
                                f"[API] Nudge result: {len(nudged_title)} chars, "
                                f"{len(nudge_log)} attempt(s), title='{nudged_title}'"
                            )
                    # If description is empty (e.g. streaming failed), fall back to what's on disk
                    desc_to_save = pending_description
                    if not desc_to_save:
                        existing = load_listing_data(sku=sku)
                        desc_to_save = (
                            existing.get("inventoryItem", {}).get("product", {}).get("description", "")
                            if existing else ""
                        )
                else:
                    desc_to_save = pending_description
                update_listing_title_description(sku, {
                    "edited_title": pending_title,
                    "edited_description": desc_to_save,
                })

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

            localized_aspects = listing.get("localizedAspects") or []
            pre_fetched_aspects = listing.get("preFetchedAspects")  # pre-computed during /api/photos
            update_listing_with_aspects(sku, localized_aspects, pre_fetched_aspects=pre_fetched_aspects)
            print(f"[API] Updated listing with aspects")

            yield progress_event('Updating aspects', 'completed')

            # Load and return the complete listing data
            listing_data = load_listing_data(sku=sku)

            if not listing_data:
                log_event("draft_completed", "error", sku=sku, error="Failed to load created listing data")
                yield error_event("Failed to load created listing data")
                return

            print(f"[API] Successfully created listing: {sku}")

            _title = (listing_data.get("inventoryItem") or {}).get("product", {}).get("title", "")
            log_event(
                "draft_completed", "success",
                sku=sku,
                title=_title,
                textModel=(models_payload or {}).get("text_model"),
                imageModel=(models_payload or {}).get("image_model"),
            )

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

            log_event("draft_completed", "error", sku=sku, error=error_msg)
            yield error_event(f"An error occurred while creating listing: {error_msg}")

    return streaming_response(generate())


@app.route('/api/update-listing-images', methods=['POST'])
def update_listing_images_endpoint():
    """
    Update only the image URLs in a listing JSON file.
    Creates the file if it does not exist. Does not run AI title/description.
    
    Accepts JSON body:
    {
        "sku": "AXIS_XX",
        "image_urls": ["url1", "url2", ...]
    }
    
    Returns:
        JSON with listing_data from disk, or error message
    """
    try:
        print("[API] /api/update-listing-images endpoint called")
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body must be JSON", "listing_data": None}), 400
        
        sku = data.get("sku")
        image_urls = data.get("image_urls", [])
        
        if not sku or not isinstance(sku, str):
            return jsonify({"error": "sku must be a non-empty string", "listing_data": None}), 400
        
        if not image_urls or not isinstance(image_urls, list):
            return jsonify({"error": "image_urls must be a non-empty array", "listing_data": None}), 400
        
        from backend.copyScripts.combine_data import listing_file_exists
        if not listing_file_exists(sku):
            return jsonify({"error": f"Listing file not found for SKU {sku}. Cannot update images.", "listing_data": None}), 404

        success = update_listing_images(sku, image_urls)
        if not success:
            return jsonify({"error": "Failed to update listing images", "listing_data": None}), 500
        
        listing_data = load_listing_data(sku=sku)
        return jsonify({"listing_data": listing_data, "error": None}), 200
        
    except Exception as e:
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred while updating listing images (encoding error)"
        import traceback
        traceback.print_exc()
        return jsonify({"error": error_msg, "listing_data": None}), 500


def _sanitize_title(text):
    """Strip whitespace, surrounding quotes, and any trailing punctuation an LLM may add."""
    if not text:
        return ""
    cleaned = text.strip()
    # Remove paired surrounding quotes
    while cleaned and cleaned[0] in ('"', "'") and cleaned[-1] in ('"', "'"):
        cleaned = cleaned[1:-1].strip()
    # If model returned multiple lines, take the first non-empty line
    for line in cleaned.splitlines():
        line = line.strip()
        if line:
            cleaned = line
            break
    return cleaned.strip()


def _load_prompt(filename):
    _db.ensure_db()
    content = _db.get_prompt(filename)
    if content is None:
        # Seed-on-missing fallback: installs that migrated before this prompt
        # was added won't have it in the DB — load it from prompts/ on disk
        # and seed the DB so later reads hit the database.
        disk_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), PROMPTS_DIR, filename)
        if not os.path.isfile(disk_path):
            raise FileNotFoundError(f"prompt not found: {filename}")
        with open(disk_path, "r", encoding="utf-8") as f:
            content = f.read()
        try:
            _db.save_prompt(filename, content)
        except Exception as e:
            print(f"[API] could not seed prompt {filename} into DB: {e}")
    return content


def _nudge_title_length(current_title, text_model):
    """
    Recursively nudge a title's character count into [TITLE_MIN_LEN, TITLE_MAX_LEN].

    Uses two directional prompts (decrease/increase) and retries up to
    TITLE_MAX_ATTEMPTS times. Logs every attempt for testing.

    Returns (best_title, attempts_log) where best_title is the candidate
    closest to TITLE_TARGET_LEN that we produced (in-range if possible).
    """
    try:
        decrease_template = _load_prompt("trimTitlePrompt.txt")
    except FileNotFoundError:
        decrease_template = None
    try:
        increase_template = _load_prompt("increaseTitlePrompt.txt")
    except FileNotFoundError:
        increase_template = None

    attempts_log = []
    candidates = [current_title]
    working_title = current_title

    for attempt in range(1, TITLE_MAX_ATTEMPTS + 1):
        in_len = len(working_title)
        in_words = len(working_title.split())

        if TITLE_MIN_LEN <= in_len <= TITLE_MAX_LEN:
            print(
                f"[TITLE_NUDGE] attempt={attempt - 1} status=in_range "
                f"length={in_len} title='{working_title}'"
            )
            break

        if in_len > TITLE_MAX_LEN:
            direction = "decrease"
            template = decrease_template
            chars_delta = in_len - TITLE_TARGET_LEN  # positive: chars to remove
            target_words = max(1, round(TITLE_TARGET_LEN / 6))
            words_to_remove = max(1, round(chars_delta / 6))
            if not template:
                print("[TITLE_NUDGE] decrease prompt template missing; aborting loop")
                break
            prompt = template.format(
                current_title=working_title,
                current_length=in_len,
                current_words=in_words,
                chars_over=chars_delta,
                target_words=target_words,
                words_to_remove=words_to_remove,
            )
        else:  # in_len < TITLE_MIN_LEN
            direction = "increase"
            template = increase_template
            chars_delta = TITLE_TARGET_LEN - in_len  # positive: chars to add
            target_words = max(1, round(TITLE_TARGET_LEN / 6))
            words_to_add = max(1, round(chars_delta / 6))
            if not template:
                print("[TITLE_NUDGE] increase prompt template missing; aborting loop")
                break
            prompt = template.format(
                current_title=working_title,
                current_length=in_len,
                current_words=in_words,
                chars_under=chars_delta,
                target_words=target_words,
                words_to_add=words_to_add,
            )

        print(
            f"[TITLE_NUDGE] attempt={attempt} direction={direction} "
            f"in_length={in_len} chars_delta={chars_delta} "
            f"in_title='{working_title}'"
        )

        raw_response = call_text_llm(prompt, model=text_model)
        new_title = _sanitize_title(raw_response)

        if not new_title:
            print(
                f"[TITLE_NUDGE] attempt={attempt} direction={direction} "
                f"result=empty_response keeping_previous"
            )
            attempts_log.append({
                "attempt": attempt,
                "direction": direction,
                "in_length": in_len,
                "out_length": 0,
                "delta": 0,
                "in_range": False,
                "title": "",
            })
            continue

        out_len = len(new_title)
        delta = out_len - in_len
        in_range = TITLE_MIN_LEN <= out_len <= TITLE_MAX_LEN

        print(
            f"[TITLE_NUDGE] attempt={attempt} direction={direction} "
            f"in_length={in_len} out_length={out_len} delta={delta:+d} "
            f"in_range={in_range} out_title='{new_title}'"
        )

        attempts_log.append({
            "attempt": attempt,
            "direction": direction,
            "in_length": in_len,
            "out_length": out_len,
            "delta": delta,
            "in_range": in_range,
            "title": new_title,
        })

        candidates.append(new_title)
        working_title = new_title

        if in_range:
            break

    # Pick the best candidate: prefer in-range, otherwise prefer ≤80 (longest), else shortest overall
    in_range_candidates = [
        c for c in candidates if TITLE_MIN_LEN <= len(c) <= TITLE_MAX_LEN
    ]
    if in_range_candidates:
        # Prefer the LAST in-range candidate (most recent, refined version)
        best = in_range_candidates[-1]
    else:
        under_candidates = [c for c in candidates if len(c) <= TITLE_MAX_LEN]
        if under_candidates:
            # Longest title ≤ 80 (closest to target without going over)
            best = max(under_candidates, key=len)
        else:
            # Everything is over 80 — pick the shortest (least bad)
            best = min(candidates, key=len)

    print(
        f"[TITLE_NUDGE] final length={len(best)} "
        f"in_range={TITLE_MIN_LEN <= len(best) <= TITLE_MAX_LEN} "
        f"attempts={len(attempts_log)} title='{best}'"
    )

    return best, attempts_log


@app.route('/api/trim-title', methods=['POST'])
def trim_title():
    """
    Use AI to nudge a listing title into the 70-80 character range.

    If the title is too long (>80) it is shortened.
    If the title is too short (<70) it is expanded.
    Already-in-range titles are returned unchanged.

    Up to 3 LLM attempts are made; each attempt is logged for testing.
    Also updates the listing JSON file if sku is provided.

    Accepts JSON body:
    {
        "title": "current title text",
        "sku": "AXIS_XX" (optional - if provided, updates the listing file),
        "text_model": "model id" (optional)
    }

    Returns:
        JSON with trimmed_title (and attempts metadata for debugging)
    """
    try:
        print("[API] /api/trim-title endpoint called")
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        current_title = data.get("title", "")
        sku = data.get("sku")

        if not current_title:
            return jsonify({"error": "title is required"}), 400

        current_length = len(current_title)
        print(
            f"[API] /api/trim-title input length={current_length} "
            f"title='{current_title}'"
        )

        if TITLE_MIN_LEN <= current_length <= TITLE_MAX_LEN:
            print(f"[API] Title already in range ({current_length} chars), no nudge needed")
            return jsonify({
                "trimmed_title": current_title,
                "attempts": [],
                "original_length": current_length,
                "final_length": current_length,
            }), 200

        text_model = data.get("text_model") or DEFAULT_TEXT_MODEL
        final_title, attempts_log = _nudge_title_length(current_title, text_model)

        if not final_title:
            return jsonify({"error": "Failed to get response from AI"}), 502

        print(
            f"[API] Final title: '{final_title}' ({len(final_title)} chars) "
            f"after {len(attempts_log)} attempt(s)"
        )

        # Update listing file if sku provided
        if sku:
            try:
                listing_data = load_listing_data(sku=sku)
                if listing_data:
                    update_listing_title_description(sku, {
                        "edited_title": final_title,
                        "edited_description": listing_data.get("inventoryItem", {}).get("product", {}).get("description", "")
                    })
                    print(f"[API] Updated listing {sku} with nudged title")
            except Exception as e:
                print(f"[API] Warning: Could not update listing file: {e}")

        return jsonify({
            "trimmed_title": final_title,
            "attempts": attempts_log,
            "original_length": current_length,
            "final_length": len(final_title),
        }), 200

    except Exception as e:
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred while trimming title (encoding error)"

        import traceback
        traceback.print_exc()

        return jsonify({
            "error": f"An error occurred while trimming title: {error_msg}"
        }), 500


@app.route('/api/update-title', methods=['POST'])
def update_title():
    """
    Update just the title of an existing listing.
    
    Accepts JSON body:
    {
        "sku": "AXIS_XX",
        "title": "new title text"
    }
    """
    try:
        print("[API] /api/update-title endpoint called")
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        sku = data.get("sku")
        new_title = data.get("title", "")

        if not sku:
            return jsonify({"error": "sku is required"}), 400
        if not new_title:
            return jsonify({"error": "title is required"}), 400

        listing_data = load_listing_data(sku=sku)
        if not listing_data:
            return jsonify({"error": f"Listing not found for SKU: {sku}"}), 404

        current_desc = listing_data.get("inventoryItem", {}).get("product", {}).get("description", "")
        update_listing_title_description(sku, {
            "edited_title": new_title,
            "edited_description": current_desc
        })

        print(f"[API] Updated title for {sku}: '{new_title}' ({len(new_title)} chars)")

        # Reload to return updated data
        updated_data = load_listing_data(sku=sku)
        return jsonify({"listing_data": updated_data}), 200

    except Exception as e:
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred while updating title (encoding error)"

        import traceback
        traceback.print_exc()

        return jsonify({
            "error": f"An error occurred while updating title: {error_msg}"
        }), 500


@app.route('/api/regenerate-title', methods=['POST'])
def regenerate_title():
    """
    Regenerate the listing title using the LLM.

    Accepts JSON body:
    {
        "sku": "AXIS_XX",
        "current_title": "current editable title",
        "user_prompt": "make it shorter and highlight the brand",
        "model": "deepseek/deepseek-v4-flash"
    }
    """
    try:
        print("[API] /api/regenerate-title endpoint called")
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        sku = data.get("sku")
        current_title = data.get("current_title", "")
        user_prompt = data.get("user_prompt", "")
        model = data.get("model", DEFAULT_TEXT_MODEL)

        if not sku:
            return jsonify({"error": "sku is required"}), 400
        if not current_title:
            return jsonify({"error": "current_title is required"}), 400
        if not user_prompt:
            return jsonify({"error": "user_prompt is required"}), 400

        listing_data = load_listing_data(sku=sku)
        if not listing_data:
            return jsonify({"error": f"Listing not found for SKU: {sku}"}), 404

        prompt = (
            f"Here is an eBay listing title:\n\n{current_title}\n\n"
            f"Please edit the title according to this instruction: {user_prompt}\n\n"
            "Return only the new title text, no quotes, no explanation."
        )
        result = call_text_llm(prompt, model=model)
        if not result:
            return jsonify({"error": "LLM returned no response"}), 500

        new_title = result.strip().strip('"').strip("'")
        print(f"[API] Regenerated title for {sku}: '{new_title}' ({len(new_title)} chars)")

        current_desc = listing_data.get("inventoryItem", {}).get("product", {}).get("description", "")
        update_listing_title_description(sku, {
            "edited_title": new_title,
            "edited_description": current_desc
        })

        updated_data = load_listing_data(sku=sku)
        return jsonify({"title": new_title, "listing_data": updated_data}), 200

    except Exception as e:
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred while regenerating title (encoding error)"
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An error occurred while regenerating title: {error_msg}"}), 500


@app.route('/api/regenerate-description', methods=['POST'])
def regenerate_description():
    """
    Regenerate the listing description using the LLM.

    Accepts JSON body:
    {
        "sku": "AXIS_XX",
        "current_description": "<p>...</p>",
        "user_prompt": "add bullet points for features",
        "model": "deepseek/deepseek-v4-flash"
    }
    """
    try:
        print("[API] /api/regenerate-description endpoint called")
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        sku = data.get("sku")
        current_description = data.get("current_description", "")
        user_prompt = data.get("user_prompt", "")
        model = data.get("model", DEFAULT_TEXT_MODEL)

        if not sku:
            return jsonify({"error": "sku is required"}), 400
        if not current_description:
            return jsonify({"error": "current_description is required"}), 400
        if not user_prompt:
            return jsonify({"error": "user_prompt is required"}), 400

        listing_data = load_listing_data(sku=sku)
        if not listing_data:
            return jsonify({"error": f"Listing not found for SKU: {sku}"}), 404

        prompt = (
            f"Here is an eBay listing description (HTML):\n\n{current_description}\n\n"
            f"Please edit the description according to this instruction: {user_prompt}\n\n"
            "Return only the new description HTML, no explanation, no markdown fences."
        )
        result = call_text_llm(prompt, model=model)
        if not result:
            return jsonify({"error": "LLM returned no response"}), 500

        new_description = result.strip()
        print(f"[API] Regenerated description for {sku}: {len(new_description)} chars")

        current_title = listing_data.get("inventoryItem", {}).get("product", {}).get("title", "")
        update_listing_title_description(sku, {
            "edited_title": current_title,
            "edited_description": new_description
        })

        updated_data = load_listing_data(sku=sku)
        return jsonify({"description": new_description, "listing_data": updated_data}), 200

    except Exception as e:
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred while regenerating description (encoding error)"
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An error occurred while regenerating description: {error_msg}"}), 500


@app.route('/api/regenerate-metadata', methods=['POST'])
def regenerate_metadata():
    """
    Regenerate listing metadata (aspects, condition, price, category) using LLM.

    Accepts JSON body:
    {
        "sku": "AXIS_XX",
        "user_prompt": "it is black and made in the US",
        "model": "deepseek/deepseek-v4-flash"
    }
    """
    try:
        print("[API] /api/regenerate-metadata endpoint called")
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        sku = data.get("sku")
        user_prompt = data.get("user_prompt", "")
        model = data.get("model", DEFAULT_TEXT_MODEL)

        if not sku:
            return jsonify({"error": "sku is required"}), 400
        if not user_prompt:
            return jsonify({"error": "user_prompt is required"}), 400

        listing_data = load_listing_data(sku=sku)
        if not listing_data:
            return jsonify({"error": f"Listing not found for SKU: {sku}"}), 404

        metadata = extract_metadata_for_llm(listing_data)
        metadata_json = json.dumps(metadata, indent=2)

        prompt = (
            f"{metadata_json}\n\n"
            f"Please edit the JSON according to this instruction and keep it in JSON format.\n\n"
            f"{user_prompt}"
        )
        result = call_text_llm(prompt, model=model)
        if not result:
            return jsonify({"error": "LLM returned no response"}), 500

        # Strip markdown fences if present
        clean = result.strip()
        if clean.startswith("```"):
            parts = clean.split("```")
            clean = parts[1] if len(parts) > 1 else clean
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()

        try:
            updated_metadata = json.loads(clean)
        except json.JSONDecodeError as e:
            return jsonify({"error": f"LLM returned malformed JSON: {str(e)}. Raw: {result[:300]}"}), 400

        # Merge updated fields back into the listing
        inventory = listing_data.get("inventoryItem", {})
        product = inventory.get("product", {})
        offer = listing_data.get("offer", {})

        if "condition" in updated_metadata:
            inventory["condition"] = updated_metadata["condition"]
        if "aspects" in updated_metadata:
            product["aspects"] = updated_metadata["aspects"]
        if "price" in updated_metadata:
            offer.setdefault("pricingSummary", {})["price"] = updated_metadata["price"]
        if "categoryId" in updated_metadata:
            offer["categoryId"] = updated_metadata["categoryId"]

        inventory["product"] = product
        listing_data["inventoryItem"] = inventory
        listing_data["offer"] = offer

        _db.ensure_db()
        _db.save_listing(listing_data)

        print(f"[API] Regenerated metadata for {sku}")
        return jsonify({"metadata": updated_metadata, "listing_data": listing_data}), 200

    except Exception as e:
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred while regenerating metadata (encoding error)"
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An error occurred while regenerating metadata: {error_msg}"}), 500


@app.route('/api/update-description', methods=['POST'])
def update_description():
    """
    Update just the description of an existing listing (HTML allowed).

    Accepts JSON body:
    {
        "sku": "AXIS_XX",
        "description": "<p>...</p>"
    }
    """
    try:
        print("[API] /api/update-description endpoint called")
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        sku = data.get("sku")
        new_description = data.get("description", "")
        if new_description is None:
            new_description = ""

        if not sku:
            return jsonify({"error": "sku is required"}), 400

        listing_data = load_listing_data(sku=sku)
        if not listing_data:
            return jsonify({"error": f"Listing not found for SKU: {sku}"}), 404

        current_title = listing_data.get("inventoryItem", {}).get("product", {}).get("title", "")
        update_listing_title_description(sku, {
            "edited_title": current_title,
            "edited_description": new_description
        })

        print(f"[API] Updated description for {sku} ({len(new_description)} chars)")

        updated_data = load_listing_data(sku=sku)
        return jsonify({"listing_data": updated_data}), 200

    except Exception as e:
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred while updating description (encoding error)"

        import traceback
        traceback.print_exc()

        return jsonify({
            "error": f"An error occurred while updating description: {error_msg}"
        }), 500


@app.route('/api/listings', methods=['GET'])
def list_all_listings():
    """
    Get all generated listings from the listings table in axis.db.
    
    Returns:
        JSON response with list of all listings (summary data), or error message
    """
    try:
        print("[API] /api/listings endpoint called")
        _db.ensure_db()

        listings = []

        for listing_data in _db.list_listings():
            try:
                # Soft-deleted listings never appear in the API response
                if listing_data.get('hidden'):
                    continue

                # Extract summary information
                sku = listing_data.get('sku', '')
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
                    'description': description,
                    'price': price,
                    'currency': currency,
                    'categoryId': category_id,
                    'createdDateTime': created_date,
                    'imageCount': image_count,
                    'imageUrls': image_urls,
                    'quantity': quantity,
                    'filename': f"{sku}.json",
                    'fileSku': sku,
                    'ebayListingId': str(listing_data.get('ebayListingId') or '').strip(),
                    'models': listing_data.get('models') or None,
                    'isManualListing': bool(listing_data.get('isManualListing', False)),
                    'sellerSku': str(listing_data.get('sellerSku') or '').strip() or None,
                    'isVariationListing': bool(listing_data.get('isVariationListing', False)),
                    'ebay_status': listing_data.get('ebay_status', 'active'),
                })
            except Exception as e:
                print(f"[API] Error reading listing {listing_data.get('sku')}: {e}")
                import traceback
                traceback.print_exc()
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

@app.route('/api/import-listings', methods=['POST'])
def api_import_listings():
    """
    Sync active eBay listings created outside this tool into the listings table of axis.db.
    Uses ModTimeFrom from the preferences table for incremental fetches after the first run.
    """
    last_refreshed = get_manual_import_last_refreshed()
    try:
        items = get_seller_list(mod_time_from=last_refreshed)
    except Exception as e:
        log_event("import", "error", error=str(e))
        return jsonify({'error': str(e)}), 500

    # Index local listings by eBay item ID, split by listing kind
    _db.ensure_db()
    axis_item_ids = set()
    manual_item_ids = set()
    for d in _db.list_listings():
        try:
            eid = str(d.get('ebayListingId') or '').strip()
            if not eid:
                continue
            if d.get('isManualListing'):
                manual_item_ids.add(eid)
            else:
                axis_item_ids.add(eid)
        except Exception:
            continue

    imported = updated = skipped = 0
    imported_skus = []
    updated_skus = []
    for item in items:
        if item['item_id'] in axis_item_ids:
            skipped += 1
            continue
        is_new = item['item_id'] not in manual_item_ids
        written = write_manual_listing_json(item)
        if written:
            sku = str(item.get('seller_sku') or '').strip() or item['item_id']
            if is_new:
                imported += 1
                imported_skus.append(sku)
            else:
                updated += 1
                updated_skus.append(sku)
        else:
            skipped += 1

    save_manual_import_last_refreshed(
        datetime.now(timezone.utc).isoformat()
    )
    if imported or updated:
        log_event(
            "import", "success",
            count=imported + updated,
            imported_count=imported,
            updated_count=updated,
            imported_skus=imported_skus,
            updated_skus=updated_skus,
        )
    return jsonify({'imported': imported, 'updated': updated, 'skipped': skipped})

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
                log_event("upload", "error", sku=actual_sku, error=error_msg)
                yield error_event(f"Exception during upload: {error_msg}")
                return

            if not upload_result:
                print(f"[API] upload_complete_listing returned None - upload failed")
                log_event("upload", "error", sku=actual_sku, error="upload_complete_listing returned None")
                yield error_event("Failed to upload listing to eBay. Check server logs for details.")
                return

            print(f"[API] Successfully uploaded listing to eBay")
            print(f"[API] Upload result: {upload_result}")

            lid = upload_result.get("listingId")
            if lid:
                save_ebay_listing_id(sku=sku, filename=filename, ebay_listing_id=lid)
            else:
                print("[API] Warning: publish succeeded but listingId missing; ebayListingId not saved to JSON")

            _upload_title = (inventory_item_data.get("product") or {}).get("title", "")
            log_event("upload", "success", sku=actual_sku, title=_upload_title, ebayListingId=lid or "")

            yield progress_event('Uploading to eBay', 'completed')

            # Promoted listing enrollment (non-fatal)
            promote_settings = get_promoted_listing_settings()
            if promote_settings.get("auto_promote_enabled"):
                yield progress_event('Enrolling in Promoted Listings', 'in_progress')
                try:
                    ids = get_promoted_listing_campaign_ids()
                    user_token = os.getenv("user_token", "")
                    new_campaign_id, new_ad_group_id = promote_listing(
                        sku=actual_sku,
                        user_token=user_token,
                        campaign_id=ids["campaign_id"],
                        ad_group_id=ids["ad_group_id"],
                        ad_rate=promote_settings["promoted_listing_ad_rate"],
                    )
                    if new_campaign_id != ids["campaign_id"] or new_ad_group_id != ids["ad_group_id"]:
                        save_promoted_listing_campaign_ids(new_campaign_id, new_ad_group_id)
                    yield progress_event('Enrolling in Promoted Listings', 'completed')
                except PromotionError as pe:
                    print(f"[API] Promoted listing enrollment failed: {pe}")
                    yield progress_event(f'Promoted listing enrollment failed: {pe}', 'warning')
                except Exception as pe:
                    print(f"[API] Unexpected error during promotion: {pe}")
                    yield progress_event(f'Promoted listing enrollment failed (unexpected): {pe}', 'warning')

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


@app.route('/api/upload-test-listing', methods=['POST'])
def upload_test_listing():
    """
    Upload a synthetic test listing to eBay using real credentials.
    Uses hardcoded test data (product details, pricing) but injects real
    listing policies and merchant location from .env / listingPreferences.json.
    Intended for debugging the upload pipeline from the Test Workflow tab.
    Streams NDJSON progress events identical to /api/upload-listing.
    """
    def generate():
        try:
            print("[TEST-UPLOAD] /api/upload-test-listing called")

            # --- Build test inventory item data ---
            test_inventory_item = {
                "availability": {
                    "shipToLocationAvailability": {"quantity": 1}
                },
                "condition": "NEW",
                "packageWeightAndSize": {
                    "weight": {"value": "0.5", "unit": "POUND"},
                    "dimensions": {"length": "8", "width": "6", "height": "2", "unit": "INCH"},
                },
                "product": {
                    "title": "Vintage Ceramic Decorative Bowl Home Decor Accent Piece",
                    "description": "<p>Beautiful ceramic decorative bowl suitable for home and office use. Great accent piece for any room.</p>",
                    "aspects": {
                        "Brand": ["Unbranded"],
                        "Type": ["Test"],
                    },
                    "imageUrls": [
                        "https://picsum.photos/seed/axistest/400/400",
                    ],
                },
            }

            # --- Build test offer data ---
            from backend.copyScripts.combine_data import MERCHANT_LOCATION_KEY, get_listing_policies
            test_offer = {
                "marketplaceId": EBAY_MARKETPLACE_ID,
                "format": "FIXED_PRICE",
                "quantity": 1,
                "pricingSummary": {
                    "price": {"value": "999.99", "currency": "USD"}
                },
                "listingDuration": "GTC",
                "categoryId": "181415",
                "merchantLocationKey": MERCHANT_LOCATION_KEY,
            }

            # Inject real listing policies from .env
            policies = get_listing_policies()
            print(f"[TEST-UPLOAD] Listing policies from .env: {policies}")
            if not policies:
                yield error_event(
                    "No listing policies found in .env. "
                    "Set fulfillment_policy_id, payment_policy_id, return_policy_id."
                )
                return
            test_offer["listingPolicies"] = policies

            import time as _time
            test_sku = f"AXIS_TEST_{int(_time.time())}"

            print(f"[TEST-UPLOAD] SKU: {test_sku}")
            print(f"[TEST-UPLOAD] Title: {test_inventory_item['product']['title']}")
            print(f"[TEST-UPLOAD] Price: {test_offer['pricingSummary']['price']['value']}")
            print(f"[TEST-UPLOAD] merchantLocationKey: {MERCHANT_LOCATION_KEY}")
            print(f"[TEST-UPLOAD] Policies: {policies}")
            print(f"[TEST-UPLOAD] Full inventory item: {json.dumps(test_inventory_item, indent=2)}")
            print(f"[TEST-UPLOAD] Full offer data: {json.dumps(test_offer, indent=2)}")

            yield progress_event('Preparing listing data', 'completed')
            yield progress_event('Uploading to eBay', 'in_progress')

            try:
                upload_result = upload_complete_listing(
                    sku=test_sku,
                    inventory_item_data=test_inventory_item,
                    offer_data=test_offer,
                    locale="en-US",
                    use_user_token=True,
                )
            except Exception as upload_exc:
                error_msg = str(upload_exc)
                print(f"[TEST-UPLOAD] Exception during upload_complete_listing: {error_msg}")
                import traceback
                traceback.print_exc()
                yield error_event(f"Upload exception: {error_msg}")
                return

            if not upload_result:
                print("[TEST-UPLOAD] upload_complete_listing returned None")
                yield error_event("Upload returned no result. Check server logs.")
                return

            print(f"[TEST-UPLOAD] Upload succeeded. Result: {upload_result}")
            yield progress_event('Uploading to eBay', 'completed')

            # Non-fatal promoted listings enrollment (same as real upload)
            from backend.copyScripts.combine_data import (
                get_promoted_listing_settings,
                get_promoted_listing_campaign_ids,
                save_promoted_listing_campaign_ids,
            )
            promote_settings = get_promoted_listing_settings()
            if promote_settings.get("auto_promote_enabled"):
                yield progress_event('Enrolling in Promoted Listings', 'in_progress')
                try:
                    ids = get_promoted_listing_campaign_ids()
                    user_token = os.getenv("user_token", "")
                    new_campaign_id, new_ad_group_id = promote_listing(
                        sku=test_sku,
                        user_token=user_token,
                        campaign_id=ids["campaign_id"],
                        ad_group_id=ids["ad_group_id"],
                        ad_rate=promote_settings["promoted_listing_ad_rate"],
                    )
                    if new_campaign_id != ids["campaign_id"] or new_ad_group_id != ids["ad_group_id"]:
                        save_promoted_listing_campaign_ids(new_campaign_id, new_ad_group_id)
                    yield progress_event('Enrolling in Promoted Listings', 'completed')
                except PromotionError as pe:
                    print(f"[TEST-UPLOAD] Promoted listing enrollment failed: {pe}")
                    yield progress_event(f'Promoted listing enrollment failed: {pe}', 'warning')
                except Exception as pe:
                    print(f"[TEST-UPLOAD] Unexpected error during promotion: {pe}")
                    yield progress_event(f'Promoted listing enrollment failed (unexpected): {pe}', 'warning')

            yield result_event({"upload_result": upload_result, "error": None})

        except Exception as e:
            try:
                error_msg = str(e)
            except UnicodeEncodeError:
                error_msg = "An error occurred (encoding error)"
            import traceback
            traceback.print_exc()
            yield error_event(f"Unexpected error in test upload: {error_msg}")

    return streaming_response(generate())


def _test_application_token():
    """Test application token by making a simple Browse API search call."""
    token = os.getenv('application_token')
    if not token or not token.strip():
        return {'ok': False, 'message': 'application_token is not set in .env'}
    url = f'{EBAY_BROWSE_API_BASE}/item_summary/search'
    headers = {
        'Authorization': f'Bearer {token.strip()}',
        'X-EBAY-C-MARKETPLACE-ID': EBAY_MARKETPLACE_ID,
        'Content-Type': 'application/json'
    }
    params = {'q': 'test', 'limit': 1}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        if r.status_code == 200:
            return {'ok': True, 'message': 'Application token is valid'}
        return {'ok': False, 'message': f'eBay API returned {r.status_code}: {r.text[:200]}'}
    except requests.RequestException as e:
        return {'ok': False, 'message': str(e)}


def _test_user_token():
    """Test user token by making a simple Inventory API call."""
    token = os.getenv('user_token')
    if not token or not token.strip():
        return {'ok': False, 'message': 'user_token is not set in .env'}
    url = 'https://api.ebay.com/sell/inventory/v1/inventory_item'
    headers = {
        'Authorization': f'Bearer {token.strip()}',
        'Content-Type': 'application/json'
    }
    params = {'limit': 1}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        if r.status_code == 200:
            return {'ok': True, 'message': 'User token is valid'}
        return {'ok': False, 'message': f'eBay API returned {r.status_code}: {r.text[:200]}'}
    except requests.RequestException as e:
        return {'ok': False, 'message': str(e)}


@app.route('/api/test-application-token', methods=['POST'])
def api_test_application_token():
    """Test the application token via a simple Browse API call."""
    try:
        result = _test_application_token()
        return jsonify({'result': result, 'error': None}), 200
    except Exception as e:
        return jsonify({'result': None, 'error': str(e)}), 500


@app.route('/api/test-user-token', methods=['POST'])
def api_test_user_token():
    """Test the user token via a simple Inventory API call."""
    try:
        result = _test_user_token()
        return jsonify({'result': result, 'error': None}), 200
    except Exception as e:
        return jsonify({'result': None, 'error': str(e)}), 500


@app.route('/api/listings/quantities', methods=['POST'])
def api_listings_quantities():
    """Fetch live eBay offer-level quantity for a list of SKUs.

    Reads from the Offer API (GET /offer?sku=...) which reflects what
    buyers actually see on the listing, including sold-quantity adjustments.
    Falls back to the inventory-item level if no offer exists.
    """
    body = request.get_json(silent=True) or {}
    skus = body.get('skus', [])
    if not skus:
        return jsonify({}), 200

    token = os.getenv('user_token', '').strip()
    if not token:
        return jsonify({sku: None for sku in skus}), 200

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }

    result = {}
    for sku in skus:
        if _is_manual_sku(sku):
            # Imported listings live outside the Sell Inventory API; fetch the
            # live available quantity from eBay via GetItem, falling back to
            # the local snapshot if eBay is unreachable.
            item_id = _manual_item_id(sku)
            qty = get_item_available_quantity(item_id) if item_id else None
            if qty is None:
                d = _load_listing_file(sku)
                try:
                    qty = int(d.get('offer', {}).get('quantity', 0))
                except Exception:
                    qty = None
            result[sku] = qty
            continue
        try:
            # Try offer endpoint first (reflects live listing quantity)
            url = f'https://api.ebay.com/sell/inventory/v1/offer?sku={sku}'
            r = requests.get(url, headers=headers, timeout=10)
            qty = None
            if r.status_code == 200:
                resp_data = r.json()
                offers = resp_data.get('offers', [])
                if offers:
                    offer = offers[0]
                    qty = offer.get('availableQuantity')
                    if qty is None:
                        qty = offer.get('quantity')
                    if qty is None:
                        print(f"[quantities] SKU {sku}: offer keys = {list(offer.keys())}")

            # Fall back to inventory item quantity if offer didn't provide one
            if qty is None:
                inv_url = f'https://api.ebay.com/sell/inventory/v1/inventory_item/{sku}'
                r2 = requests.get(inv_url, headers=headers, timeout=10)
                if r2.status_code == 200:
                    qty = (
                        r2.json()
                        .get('availability', {})
                        .get('shipToLocationAvailability', {})
                        .get('quantity')
                    )

            result[sku] = qty
        except Exception as e:
            print(f"[quantities] SKU {sku}: exception {e}")
            result[sku] = None

    return jsonify(result), 200


@app.route('/api/settings/auto-restock', methods=['GET'])
def api_get_auto_restock_settings():
    """Read the persisted auto-restock enabled flag and target quantity."""
    try:
        return jsonify(get_auto_restock_settings()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/auto-restock', methods=['POST'])
def api_save_auto_restock_settings():
    """Persist the auto-restock enabled flag and/or target quantity."""
    body = request.get_json(silent=True) or {}
    enabled = body.get('enabled')
    quantity = body.get('quantity')
    try:
        if quantity is not None:
            quantity = int(quantity)
            if quantity < 0:
                return jsonify({'error': 'quantity must be a non-negative integer'}), 400
        settings = save_auto_restock_settings(enabled=enabled, quantity=quantity)
        return jsonify(settings), 200
    except (TypeError, ValueError):
        return jsonify({'error': 'quantity must be a non-negative integer'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/minimum-images', methods=['GET'])
def api_get_minimum_images_setting():
    """Read the persisted minimum images per listing value."""
    try:
        return jsonify(get_minimum_images_setting()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/minimum-images', methods=['POST'])
def api_save_minimum_images_setting():
    """Persist the minimum images per listing value."""
    body = request.get_json(silent=True) or {}
    minimum = body.get('minimum_images_per_listing')
    try:
        if minimum is None:
            return jsonify({'error': 'minimum_images_per_listing is required'}), 400
        minimum = int(minimum)
        if minimum < 1:
            return jsonify({'error': 'minimum_images_per_listing must be a positive integer'}), 400
        result = save_minimum_images_setting(minimum)
        return jsonify(result), 200
    except (TypeError, ValueError):
        return jsonify({'error': 'minimum_images_per_listing must be a positive integer'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/import-sync', methods=['GET'])
def api_get_import_sync_status():
    """Return the last-sync timestamp for the manual eBay import."""
    try:
        last_refreshed = get_manual_import_last_refreshed()
        return jsonify({"last_refreshed": last_refreshed})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/settings/operation-cooldown', methods=['GET'])
def api_get_operation_cooldown_setting():
    """Read the persisted auto-operation cooldown (hours)."""
    try:
        return jsonify(get_operation_cooldown_setting()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/operation-cooldown', methods=['POST'])
def api_save_operation_cooldown_setting():
    """Persist the auto-operation cooldown (hours)."""
    body = request.get_json(silent=True) or {}
    hours = body.get('operation_cooldown_hours')
    try:
        if hours is None:
            return jsonify({'error': 'operation_cooldown_hours is required'}), 400
        hours = int(hours)
        if hours < 1:
            return jsonify({'error': 'operation_cooldown_hours must be a positive integer'}), 400
        result = save_operation_cooldown_setting(hours)
        return jsonify(result), 200
    except (TypeError, ValueError):
        return jsonify({'error': 'operation_cooldown_hours must be a positive integer'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/promoted-listings', methods=['GET'])
def api_get_promoted_listing_settings():
    """Read promoted listing enabled flag and ad rate."""
    try:
        return jsonify(get_promoted_listing_settings()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/promoted-listings', methods=['POST'])
def api_save_promoted_listing_settings():
    """Persist promoted listing enabled flag and/or ad rate."""
    body = request.get_json(silent=True) or {}
    enabled = body.get('auto_promote_enabled')
    ad_rate = body.get('promoted_listing_ad_rate')
    try:
        if ad_rate is not None:
            ad_rate = float(ad_rate)
            if ad_rate < 1 or ad_rate > 100:
                return jsonify({'error': 'promoted_listing_ad_rate must be between 1 and 100'}), 400
        result = save_promoted_listing_settings(enabled=enabled, ad_rate=ad_rate)
        return jsonify(result), 200
    except (TypeError, ValueError):
        return jsonify({'error': 'promoted_listing_ad_rate must be a number'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/listings/bulk-delete', methods=['POST'])
def api_bulk_delete_listings():
    """
    Delete one or more local listing rows from the listings table in axis.db.

    Request body: { "skus": ["axis_84", "axis_85"] }
    Response: { "deleted": [...], "not_found": [...] }
    """
    data = request.get_json() or {}
    skus = data.get('skus', [])
    if not isinstance(skus, list):
        return jsonify({'error': 'skus must be a list'}), 400

    _db.ensure_db()

    deleted = []
    not_found = []
    errors = []
    for sku in skus:
        if not isinstance(sku, str) or not sku:
            not_found.append(sku)
            continue
        try:
            if _db.delete_listing(sku):
                deleted.append(sku)
            else:
                not_found.append(sku)
        except Exception as e:
            print(f"[API] bulk-delete error removing {sku}: {e}")
            errors.append({'sku': sku, 'error': str(e)})

    print(f"[API] bulk-delete: deleted={deleted}, not_found={not_found}, errors={errors}")
    if errors:
        return jsonify({'deleted': deleted, 'not_found': not_found, 'errors': errors}), 200
    return jsonify({'deleted': deleted, 'not_found': not_found}), 200


@app.route('/api/listings/restock', methods=['POST'])
def api_restock_listings():
    """
    Set the live eBay quantity for a batch of SKUs using the Sell Inventory
    API's bulkUpdatePriceQuantity call (up to 25 SKUs per eBay request).

    Updates both the inventory-item level (shipToLocationAvailability) and
    the offer level (offers[].availableQuantity) so that decreases are
    reflected on the live listing, not just the inventory record.
    """
    body = request.get_json(silent=True) or {}
    skus = [str(s).strip() for s in body.get('skus', []) if str(s).strip()]
    quantity = body.get('quantity')
    source = body.get('source', 'manual')

    try:
        quantity = int(quantity)
        if quantity < 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({'error': 'quantity must be a non-negative integer'}), 400

    if not skus:
        return jsonify({'updated': [], 'failed': [], 'quantity': quantity}), 200

    # Split into manual/imported (Trading API) and automated (Sell Inventory API) groups
    manual_sku_set = {s for s in skus if _is_manual_sku(s)}
    manual_skus = [s for s in skus if s in manual_sku_set]
    automated_skus = [s for s in skus if s not in manual_sku_set]

    updated = []
    failed = []
    failed_errors = {}  # sku -> list of eBay error message strings

    # --- Manual SKUs: route through ReviseInventoryStatus (Trading API) ---
    if manual_skus:
        sku_by_item_id = {}
        manual_api_items = []
        for sku in manual_skus:
            item_id = _manual_item_id(sku)
            if item_id:
                sku_by_item_id[item_id] = sku
                manual_api_items.append({'item_id': item_id, 'quantity': quantity})
            else:
                failed.append(sku)
                failed_errors[sku] = ['No eBay item ID on file for this imported listing']
        try:
            manual_results = revise_inventory_status_batch(manual_api_items)
            for result_item in manual_results:
                sku = sku_by_item_id.get(str(result_item['item_id']))
                if not sku:
                    continue
                if result_item['ok']:
                    updated.append(sku)
                    update_local_listing_quantity(sku=sku, quantity=quantity)
                else:
                    failed.append(sku)
                    if result_item.get('errors'):
                        failed_errors[sku] = result_item['errors']
        except Exception as e:
            for sku in sku_by_item_id.values():
                if sku not in failed:
                    failed.append(sku)
                    failed_errors[sku] = [str(e)]

    # --- Automated SKUs: route through Sell Inventory API ---
    if automated_skus:
        token = os.getenv('user_token', '').strip()
        if not token:
            failed.extend(automated_skus)
        else:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            }

            # Fetch offer IDs for each SKU so we can update offer-level quantity too
            sku_offer_ids = {}
            for sku in automated_skus:
                try:
                    r = requests.get(
                        f'https://api.ebay.com/sell/inventory/v1/offer?sku={sku}',
                        headers=headers,
                        timeout=10,
                    )
                    if r.status_code == 200:
                        offers = r.json().get('offers', [])
                        if offers:
                            sku_offer_ids[sku] = offers[0].get('offerId')
                except Exception:
                    pass

            batch_size = 25
            for i in range(0, len(automated_skus), batch_size):
                batch = automated_skus[i:i + batch_size]
                requests_list = []
                for sku in batch:
                    entry = {
                        'sku': sku,
                        'shipToLocationAvailability': {'quantity': quantity},
                    }
                    offer_id = sku_offer_ids.get(sku)
                    if offer_id:
                        entry['offers'] = [
                            {'offerId': offer_id, 'availableQuantity': quantity}
                        ]
                    requests_list.append(entry)

                payload = {'requests': requests_list}
                try:
                    r = requests.post(
                        'https://api.ebay.com/sell/inventory/v1/bulk_update_price_quantity',
                        headers=headers,
                        json=payload,
                        timeout=30,
                    )
                    if r.status_code not in (200, 207):
                        failed.extend(batch)
                        for sku in batch:
                            failed_errors[sku] = [f'HTTP {r.status_code}: {r.text[:200]}']
                        continue
                    data = r.json() or {}
                    responses = data.get('responses', [])
                    resp_by_sku = {resp.get('sku'): resp for resp in responses}
                    for sku in batch:
                        resp = resp_by_sku.get(sku)
                        if resp and resp.get('statusCode') == 200:
                            updated.append(sku)
                        else:
                            failed.append(sku)
                            errors = resp.get('errors', []) if resp else []
                            if errors:
                                failed_errors[sku] = [
                                    e.get('message') or e.get('longMessage') or str(e)
                                    for e in errors
                                ]
                            elif r.status_code not in (200, 207):
                                failed_errors[sku] = [f'HTTP {r.status_code}']
                except Exception as e:
                    failed.extend(batch)
                    for sku in batch:
                        failed_errors[sku] = [str(e)]

            for sku in updated:
                if sku not in manual_sku_set:
                    update_local_listing_quantity(sku=sku, quantity=quantity)

    # --- Verify failed SKUs against eBay to separate "not found" from real errors ---
    not_found_skus = []
    if failed:
        failed_manual = [s for s in failed if s in manual_sku_set]
        failed_axis = [s for s in failed if s not in manual_sku_set]
        try:
            confirmed_not_found = _verify_failed_skus(failed_manual, failed_axis)
        except Exception as e:
            print(f"[restock] _verify_failed_skus raised unexpectedly: {e}")
            confirmed_not_found = set()

        for sku in list(confirmed_not_found):
            set_listing_ebay_status(sku, EBAY_STATUS_NOT_FOUND)
            not_found_skus.append(sku)
            failed.remove(sku)
            failed_errors.pop(sku, None)

    if failed:
        for sku in failed:
            errors = failed_errors.get(sku) or ['(no error details)']
            print(f"[restock] FAILED {sku}: {'; '.join(errors)}")

    if not_found_skus:
        for sku in not_found_skus:
            print(f"[restock] NOT FOUND on eBay (deactivated): {sku}")

    if updated or failed or not_found_skus:
        restock_status = "success" if updated else "error"
        restock_kwargs = {"source": source, "quantity": quantity}
        if updated:
            restock_kwargs["skus"] = updated
            # Build parallel ebay_ids array (same length as skus)
            ebay_ids = []
            for restocked_sku in updated:
                ebay_id = ""
                d = _load_listing_file(restocked_sku)
                if d:
                    ebay_id = str(d.get('ebayListingId') or '')
                else:
                    print(f"[restock] could not read ebayListingId for {restocked_sku}")
                ebay_ids.append(ebay_id)
            restock_kwargs["ebay_ids"] = ebay_ids
        all_failed = failed + not_found_skus
        if all_failed:
            restock_kwargs["failed_skus"] = all_failed
        if failed_errors:
            restock_kwargs["failed_errors"] = failed_errors
        if not updated:
            restock_kwargs["error"] = f"{len(all_failed)} SKU(s) failed to restock"
        if not_found_skus:
            restock_kwargs["not_found_skus"] = not_found_skus
        log_event("restock", restock_status, **restock_kwargs)

    return jsonify({
        'updated': updated,
        'failed': failed,
        'not_found': not_found_skus,
        'failed_errors': failed_errors,
        'quantity': quantity,
    }), 200


def _index_seller_list_items(ebay_items, log_prefix):
    """Build lookup maps from get_seller_list() items, keyed by item_id and seller_sku."""
    active_by_item_id = {str(item['item_id']): item for item in ebay_items}
    active_by_seller_sku = {}
    for item in ebay_items:
        seller_sku = item.get('seller_sku')
        if seller_sku:
            if seller_sku in active_by_seller_sku:
                print(f"[{log_prefix}] Duplicate seller_sku '{seller_sku}' in eBay results; SKU fallback unreliable")
            active_by_seller_sku[seller_sku] = item
    return active_by_item_id, active_by_seller_sku


def _merge_seller_item_into_axis_listing(local_data, matched_item, matched_via, ebay_listing_id):
    """
    Merge the fields GetSellerList provides into an AXIS listing dict (in place).
    Also heals a missing ebayListingId (SKU match) and a stale not_found status.
    Returns True if anything changed.
    """
    data_changed = False

    inv = local_data.setdefault('inventoryItem', {})
    product = inv.setdefault('product', {})
    avail = inv.setdefault('availability', {})
    ship_avail = avail.setdefault('shipToLocationAvailability', {})
    offer = local_data.setdefault('offer', {})
    pricing = offer.setdefault('pricingSummary', {})
    price_obj = pricing.setdefault('price', {})

    new_title = matched_item['title']
    new_description = matched_item['description']
    new_image_urls = matched_item['image_urls']
    new_condition = matched_item['condition']
    new_quantity = matched_item['quantity']
    new_price = matched_item['price']

    if product.get('title') != new_title:
        product['title'] = new_title
        data_changed = True
    if product.get('description') != new_description:
        product['description'] = new_description
        data_changed = True
    if product.get('imageUrls') != new_image_urls:
        product['imageUrls'] = new_image_urls
        data_changed = True
    if inv.get('condition') != new_condition:
        inv['condition'] = new_condition
        data_changed = True
    if ship_avail.get('quantity') != new_quantity:
        ship_avail['quantity'] = new_quantity
        data_changed = True
    if price_obj.get('value') != new_price:
        price_obj['value'] = new_price
        data_changed = True
    if offer.get('quantity') != new_quantity:
        offer['quantity'] = new_quantity
        data_changed = True
    new_category_id = matched_item.get('category_id', '')
    if new_category_id and not offer.get('categoryId'):
        offer['categoryId'] = new_category_id
        data_changed = True

    # Heal missing ebayListingId when matched via seller_sku
    if matched_via == 'seller_sku' and not ebay_listing_id:
        local_data['ebayListingId'] = matched_item['item_id']
        data_changed = True

    if local_data.get('ebay_status') == EBAY_STATUS_NOT_FOUND:
        local_data['ebay_status'] = 'active'
        data_changed = True

    return data_changed


@app.route('/api/listings/sync-active', methods=['POST'])
def api_sync_active_listings():
    """
    Use GetSellerList as the single source of truth for active listings.

    Skips drafts (no ebayListingId and no SKU match in the active set).
    Merges eBay data into active listings and heals stale not_found status.
    Marks listings as inactive when no longer found on eBay.

    Returns { "active": N, "newly_inactive": M, "updated": K, "not_found": [...] }
    """
    _db.ensure_db()

    # Step 1: Fetch all active eBay listings via GetSellerList (single call)
    try:
        ebay_items = get_seller_list()
    except Exception as e:
        return jsonify({'error': f'GetSellerList failed: {e}'}), 500

    if not ebay_items:
        # Safety guard: an empty result likely means an auth or network issue,
        # not that the seller has zero listings. Abort to avoid mass deactivation.
        print("[sync-active] GetSellerList returned no items; aborting to prevent false deactivation")
        return jsonify({'error': 'GetSellerList returned no active listings; aborting sync to prevent false deactivation'}), 500

    active_by_item_id, active_by_seller_sku = _index_seller_list_items(ebay_items, 'sync-active')

    # Step 2: Scan all local listing rows
    active_count = 0
    newly_inactive = 0
    updated_count = 0
    not_found_skus = []
    updated_skus = []

    for local_data in _db.list_listings():
        sku = local_data.get('sku', '')
        ebay_listing_id = str(local_data.get('ebayListingId') or '').strip()
        ebay_status = local_data.get('ebay_status', '')

        # Determine if this listing matches any active eBay listing
        matched_item = None
        matched_via = None
        if ebay_listing_id and ebay_listing_id in active_by_item_id:
            matched_item = active_by_item_id[ebay_listing_id]
            matched_via = 'item_id'
        elif sku in active_by_seller_sku:
            matched_item = active_by_seller_sku[sku]
            matched_via = 'seller_sku'

        # No ebayListingId and no SKU match: draft or already-inactive, skip
        if not ebay_listing_id and matched_item is None:
            continue

        if matched_item is not None:
            # Listing is confirmed active on eBay
            is_manual = bool(local_data.get('isManualListing'))
            was_not_found = ebay_status == EBAY_STATUS_NOT_FOUND

            if is_manual:
                file_changed = write_manual_listing_json(matched_item)
                if was_not_found:
                    set_listing_ebay_status(sku, 'active')
                active_count += 1
                if file_changed or was_not_found:
                    updated_count += 1
                    updated_skus.append(sku)
            else:
                # AXIS_ listing: merge only the fields GetSellerList provides
                data_changed = _merge_seller_item_into_axis_listing(
                    local_data, matched_item, matched_via, ebay_listing_id)

                if data_changed:
                    try:
                        _db.save_listing(local_data)
                    except Exception as e:
                        print(f"[sync-active] Failed to write {sku}: {e}")

                active_count += 1
                if data_changed:
                    updated_count += 1
                    updated_skus.append(sku)

        else:
            # Has ebayListingId but not found in active maps: mark as inactive
            local_data['ebayListingId'] = ''
            local_data['ebay_status'] = EBAY_STATUS_NOT_FOUND
            try:
                _db.save_listing(local_data)
            except Exception as e:
                print(f"[sync-active] Failed to write {sku}: {e}")
            not_found_skus.append(sku)
            newly_inactive += 1
            print(f"[sync-active] Marked newly inactive: {sku}")

    # Step 3: Log the sync event
    log_fields = {
        'active': active_count,
        'newly_inactive': newly_inactive,
        'updated': updated_count,
    }
    if not_found_skus:
        log_fields['newly_inactive_skus'] = not_found_skus
    if updated_skus:
        log_fields['updated_skus'] = updated_skus
    log_event("sync_active", "success", **log_fields)

    # Step 4: Return response
    return jsonify({
        'active': active_count,
        'newly_inactive': newly_inactive,
        'updated': updated_count,
        'not_found': not_found_skus,
    }), 200


@app.route('/api/listings/sync-startup', methods=['POST'])
def api_sync_startup_listings():
    """
    Startup variant of sync-active (called at most once per 24h by the frontend).

    Uses GetSellerList as the source of truth, with two behavioral differences
    from /api/listings/sync-active:
      - A local file with a non-empty ebayListingId that is NOT in the seller
        list (ended outside Axis Researcher) is soft-deleted (hidden: true)
        instead of being marked not_found. ebayListingId is kept so the file
        can be re-matched if the listing comes back.
      - A matched file that is currently hidden is un-hidden (it apparently
        came back to life on eBay), in addition to the usual status healing.

    Returns { "removed": N, "healed": M, "aborted": bool, "reason"?: str }.
    Designed to never break app startup: failures return an error payload.
    """
    _db.ensure_db()

    try:
        ebay_items = get_seller_list()
    except Exception as e:
        print(f"[sync-startup] GetSellerList failed: {e}")
        return jsonify({
            'removed': 0,
            'healed': 0,
            'aborted': True,
            'reason': f'GetSellerList failed: {e}',
            'error': f'GetSellerList failed: {e}',
        }), 502

    if not ebay_items:
        # Safety guard: an empty result likely means an auth or network issue,
        # not that the seller has zero listings. Abort to avoid mass soft-deletion.
        reason = 'GetSellerList returned no active listings; aborting sync to prevent false soft-deletion'
        print(f"[sync-startup] {reason}")
        return jsonify({'removed': 0, 'healed': 0, 'aborted': True, 'reason': reason}), 200

    active_by_item_id, active_by_seller_sku = _index_seller_list_items(ebay_items, 'sync-startup')

    removed = 0
    healed = 0
    removed_skus = []
    healed_skus = []
    removed_titles = {}

    for local_data in _db.list_listings():
        sku = local_data.get('sku', '')
        ebay_listing_id = str(local_data.get('ebayListingId') or '').strip()
        was_hidden = bool(local_data.get('hidden'))
        was_not_found = local_data.get('ebay_status') == EBAY_STATUS_NOT_FOUND

        matched_item = None
        matched_via = None
        if ebay_listing_id and ebay_listing_id in active_by_item_id:
            matched_item = active_by_item_id[ebay_listing_id]
            matched_via = 'item_id'
        elif sku in active_by_seller_sku:
            matched_item = active_by_seller_sku[sku]
            matched_via = 'seller_sku'

        # No ebayListingId and no SKU match: draft, skip
        if not ebay_listing_id and matched_item is None:
            continue

        if matched_item is not None:
            if local_data.get('isManualListing'):
                write_manual_listing_json(matched_item)
                if was_not_found:
                    set_listing_ebay_status(sku, 'active')
                if was_hidden:
                    # write_manual_listing_json preserves the hidden flag,
                    # so explicitly clear it.
                    try:
                        file_data = _db.load_listing(sku)
                        if file_data and file_data.pop('hidden', None) is not None:
                            _db.save_listing(file_data)
                    except Exception as e:
                        print(f"[sync-startup] Failed to unhide {sku}: {e}")
            else:
                data_changed = _merge_seller_item_into_axis_listing(
                    local_data, matched_item, matched_via, ebay_listing_id)
                if was_hidden:
                    local_data.pop('hidden', None)
                    data_changed = True
                if data_changed:
                    try:
                        _db.save_listing(local_data)
                    except Exception as e:
                        print(f"[sync-startup] Failed to write {sku}: {e}")
            if was_not_found or was_hidden:
                healed += 1
                healed_skus.append(sku)
                print(f"[sync-startup] Healed: {sku}")
        else:
            # Has ebayListingId but not found on eBay: ended outside the
            # app -> soft-delete. Keep ebayListingId so a future relist can
            # re-match and heal this row.
            if not was_hidden:
                # Snapshot the title before hiding: once soft-deleted the
                # listing leaves /api/listings, so lazy title resolution
                # would fail for exactly these rows.
                title = (local_data.get('inventoryItem', {})
                         .get('product', {})
                         .get('title'))
                local_data['hidden'] = True
                try:
                    _db.save_listing(local_data)
                except Exception as e:
                    print(f"[sync-startup] Failed to write {sku}: {e}")
                    continue
                removed += 1
                removed_skus.append(sku)
                if title:
                    removed_titles[sku] = title
                print(f"[sync-startup] Soft-deleted externally ended listing: {sku}")

    log_kwargs = {'removed': removed, 'healed': healed}
    if removed_skus:
        log_kwargs['removed_skus'] = removed_skus
    if healed_skus:
        log_kwargs['healed_skus'] = healed_skus
    if removed_titles:
        log_kwargs['removed_titles'] = removed_titles
    log_event("sync_startup", "success", **log_kwargs)

    return jsonify({'removed': removed, 'healed': healed, 'aborted': False}), 200


@app.route('/api/logs', methods=['GET'])
def api_get_logs():
    _db.ensure_db()
    return jsonify({'logs': _db.get_logs()})


@app.route('/api/data-browser/<table>', methods=['GET'])
def api_data_browser(table):
    if table not in DATA_BROWSER_TABLES:
        return jsonify({"error": f"Unknown table: {table}"}), 400
    _db.ensure_db()
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 25, type=int)
    page = max(1, page)
    page_size = max(1, min(page_size, DATA_BROWSER_MAX_PAGE_SIZE))
    offset = (page - 1) * page_size

    conn = sqlite3.connect(_db.DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        total_rows = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
        columns = [row[1] for row in conn.execute(f"PRAGMA table_info([{table}])").fetchall()]
        rows = [
            dict(row)
            for row in conn.execute(
                f"SELECT * FROM [{table}] LIMIT ? OFFSET ?", (page_size, offset)
            ).fetchall()
        ]
    finally:
        conn.close()

    total_pages = max(1, -(-total_rows // page_size))  # ceiling division
    return jsonify({
        "table": table,
        "columns": columns,
        "rows": rows,
        "page": page,
        "page_size": page_size,
        "total_rows": total_rows,
        "total_pages": total_pages,
    })


# Primary key column for each browsable table, used to target row updates.
DATA_BROWSER_PK = {
    "listings": "sku",
    "preferences": "key",
    "logs": "id",
    "prompts": "name",
}


@app.route('/api/data-browser/<table>/update', methods=['PUT'])
def api_data_browser_update(table):
    if table not in DATA_BROWSER_TABLES:
        return jsonify({"error": f"Unknown table: {table}"}), 400
    body = request.get_json(silent=True) or {}
    pk_value = body.get("pk")
    column = body.get("column")
    value = body.get("value")
    if pk_value is None or not column:
        return jsonify({"error": "Missing 'pk' or 'column'"}), 400

    _db.ensure_db()
    conn = sqlite3.connect(_db.DB_FILE, timeout=30)
    try:
        pk_col = DATA_BROWSER_PK[table]
        valid_cols = {row[1] for row in conn.execute(f"PRAGMA table_info([{table}])").fetchall()}
        if column not in valid_cols:
            return jsonify({"error": f"Unknown column: {column}"}), 400
        if column == pk_col:
            return jsonify({"error": "Cannot edit primary key"}), 400

        cur = conn.execute(
            f"UPDATE [{table}] SET [{column}] = ? WHERE [{pk_col}] = ?",
            (value, pk_value),
        )
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Row not found"}), 404
    finally:
        conn.close()

    return jsonify({"ok": True, "table": table, "column": column, "pk": pk_value})


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

@app.route('/api/serp-lens', methods=['POST'])
def serp_lens_search():
    """
    Reverse-image-search an eBay listing photo via SerpAPI Google reverse image,
    filtered to 3D-print file hosting sites.

    Expects JSON: {"image_url": "https://...", "enabled_sites": ["printables.com", ...] (optional),
                   "site_priorities": ["printables.com", ...] (optional; domains in priority order)}
    Returns JSON: {"results": [{"title", "link", "source", "thumbnail", "priority_rank"}, ...]}
    """
    try:
        data = request.get_json()
        if not data or not data.get("image_url"):
            return jsonify({"error": "image_url is required"}), 400

        image_url = data["image_url"]
        enabled_sites = data.get("enabled_sites")  # list[str] | None; None means all sites
        if enabled_sites is not None and not isinstance(enabled_sites, list):
            return jsonify({"error": "enabled_sites must be a list of strings"}), 400
        site_priorities = data.get("site_priorities")  # list[str] | None; domains in priority order
        if site_priorities is not None and not isinstance(site_priorities, list):
            return jsonify({"error": "site_priorities must be a list of strings"}), 400
        print(f"[API] SerpAPI reverse image search for: {image_url}")

        raw = search_by_image(image_url)
        links = extract_top_links(raw, limit=10)
        links = drop_blacklisted(links)
        links = filter_links_by_enabled_sites(links, enabled_sites)
        links = order_by_site_priority(links, site_priorities)

        print(f"[API] SerpAPI returned {len(links)} results")
        return jsonify({"results": links}), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except requests.exceptions.RequestException as e:
        print(f"[API] SerpAPI HTTP error: {e}")
        return jsonify({"error": "SerpAPI request failed"}), 502
    except Exception as e:
        print(f"[API] SerpAPI lens error: {e}")
        return jsonify({"error": f"SerpAPI search failed: {str(e)}"}), 500


@app.route('/api/optimize-title/prompt', methods=['GET'])
def get_optimize_title_prompt():
    """Return the default title-optimization prompt template (with {title} placeholder)."""
    try:
        return jsonify({"prompt": _load_prompt("title/optimizeTitleForSearch.txt")}), 200
    except FileNotFoundError:
        return jsonify({"error": "Default title optimization prompt not found"}), 500


@app.route('/api/optimize-title', methods=['POST'])
def optimize_title():
    """
    Optimize an eBay listing title into a search query for 3D file sites
    (strip sales terms: quantity, color, condition, shipping, marketing filler).

    Expects JSON: {
        "title": "original eBay listing title",
        "prompt": "custom prompt template with {title} placeholder" (optional;
            defaults to prompts/title/optimizeTitleForSearch.txt),
        "text_model": "model id" (optional; defaults to Claude Haiku)
    }
    Returns JSON: {"optimized_title": "..."}
    """
    try:
        data = request.get_json()
        if not data or not data.get("title", "").strip():
            return jsonify({"error": "title is required"}), 400

        title = data["title"].strip()
        template = data.get("prompt")
        if not template or not template.strip():
            template = _load_prompt("title/optimizeTitleForSearch.txt")
        prompt = template.replace("{title}", title)

        text_model = data.get("text_model") or DEFAULT_TITLE_SEARCH_MODEL
        print(f"[API] /api/optimize-title model={text_model} title='{title}'")

        raw = call_text_llm(prompt, model=text_model)
        optimized = _sanitize_title(raw)
        if not optimized:
            return jsonify({"error": "Failed to get response from AI"}), 502

        print(f"[API] /api/optimize-title result: '{optimized}'")
        return jsonify({"optimized_title": optimized}), 200

    except FileNotFoundError:
        return jsonify({"error": "Default title optimization prompt not found"}), 500
    except Exception as e:
        print(f"[API] /api/optimize-title error: {e}")
        return jsonify({"error": f"Title optimization failed: {str(e)}"}), 500


@app.route('/api/serp-text-search', methods=['POST'])
def serp_text_search():
    """
    Google text search via SerpAPI (full google engine), classified against
    whitelisted/blacklisted 3D-print file hosting sites, filtered by enabled
    sites, ordered by site priority. Whitelisted links that don't point to a
    specific product page (e.g. tag/search pages) are classified blacklisted.

    Expects JSON: {
        "query": "benchy 3d file",
        "enabled_sites": ["printables.com", ...] (optional; omitted means all sites),
        "site_priorities": ["thingiverse.com", ...] (optional; domains in priority order)
    }
    Returns JSON: {"results": [{"title", "link", "snippet", "site_type", "priority_rank"}, ...]}
    """
    try:
        data = request.get_json()
        if not data or not data.get("query"):
            return jsonify({"error": "query is required"}), 400

        query = data["query"]
        enabled_sites = data.get("enabled_sites")  # list[str] | None; None means all sites
        if enabled_sites is not None and not isinstance(enabled_sites, list):
            return jsonify({"error": "enabled_sites must be a list of strings"}), 400
        site_priorities = data.get("site_priorities")  # list[str] | None; domains in priority order
        if site_priorities is not None and not isinstance(site_priorities, list):
            return jsonify({"error": "site_priorities must be a list of strings"}), 400
        print(f"[API] SerpAPI text search for: {query}")

        results = search_by_text(query)
        results = drop_blacklisted(results)
        results = filter_links_by_enabled_sites(results, enabled_sites)
        results = order_by_site_priority(results, site_priorities)

        print(f"[API] SerpAPI text search returned {len(results)} results")
        return jsonify({"results": results}), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except requests.exceptions.RequestException as e:
        print(f"[API] SerpAPI HTTP error: {e}")
        return jsonify({"error": "SerpAPI request failed"}), 502
    except Exception as e:
        print(f"[API] SerpAPI text search error: {e}")
        return jsonify({"error": f"SerpAPI search failed: {str(e)}"}), 500


@app.route('/api/test-3d-sites', methods=['GET'])
def test_3d_sites():
    """Probe each supported 3D download site by genuinely fetching a file
    through its real download pipeline. Probes run concurrently — the
    MakerWorld probe launches a browser and can take a minute or more."""
    probes = [("printables.com", probe_printables), ("thingiverse.com", probe_thingiverse), ("makerworld.com", probe_makerworld), ("cults3d.com", probe_cults3d), ("thangs.com", probe_thangs)]

    def run_probe(site, probe_fn):
        try:
            ok, message = probe_fn()
        except Exception as e:
            ok, message = False, str(e)
        if not ok:
            print(f"[test-3d-sites] {site} FAILED: {message}")
        return site, {"ok": ok, "message": message}

    results = {}
    with ThreadPoolExecutor(max_workers=len(probes)) as executor:
        futures = [executor.submit(run_probe, site, fn) for site, fn in probes]
        for future in as_completed(futures):
            site, result = future.result()
            results[site] = result
    return jsonify({"results": results})


@app.route('/api/scrape-site-images', methods=['POST'])
def scrape_site_images():
    """
    Return the main model gallery image URLs for a 3D file site page.

    Expects JSON: {"link": "https://..."}
    Returns JSON: {"images": ["https://...", ...]}
    Supported: thingiverse.com, printables.com, makerworld.com, cults3d.com, thangs.com
    Yeggi has no scraper and always returns an empty list.
    """
    try:
        data = request.get_json()
        if not data or not data.get("link"):
            return jsonify({"error": "link is required"}), 400

        link = data["link"].strip()
        images = _scrape_site_image_urls(link)
        return jsonify({"images": images}), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except RuntimeError as e:
        print(f"[API] scrape-site-images upstream error: {e}")
        return jsonify({"error": str(e)}), 502
    except requests.exceptions.RequestException as e:
        print(f"[API] scrape-site-images request error: {e}")
        return jsonify({"error": "Image scrape request failed"}), 502
    except Exception as e:
        print(f"[API] scrape-site-images error: {e}")
        return jsonify({"error": f"Image scrape failed: {str(e)}"}), 500


def _download_image(url, timeout=10):
    """Download one image and return its raw bytes. Raises on failure."""
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.content


def _scrape_site_image_urls(link):
    """Dispatch to the per-site image scraper. Shared by /api/scrape-site-images
    and /api/compare-images. Raises ValueError for unsupported sites."""
    if "thingiverse.com" in link:
        return tv_scrape_images(link)
    if "printables.com" in link:
        return printables_scrape_images(link)
    if "makerworld.com" in link:
        return mw_scrape_images(link)
    if "cults3d.com" in link:
        return cults3d_scrape_images(link)
    if "thangs.com" in link:
        return thangs_scrape_images(link)
    if "yeggi.com" in link:
        return []
    raise ValueError("Unsupported site — supported: thingiverse.com, printables.com, makerworld.com, cults3d.com, thangs.com, yeggi.com")


def _download_images_as_pil(urls):
    """Download image URLs, skipping any that fail, and return PIL images."""
    from PIL import Image
    images = []
    for url in urls:
        try:
            images.append(Image.open(io.BytesIO(_download_image(url))).convert("RGB"))
        except Exception as e:
            print(f"[API] compare-images: skipping undownloadable image {url}: {e}")
    return images


@app.route('/api/compare-images', methods=['POST'])
def compare_images():
    """
    Confirm a candidate 3D file page against an eBay listing's photos.

    Expects JSON: {"ebay_photos": ["https://...", ...], "site_url": "https://..."}
    Returns JSON: {"match": bool, "matched_pairs": [{"ebay_index", "site_index", "distance"}, ...],
                   "ebay_image_count": int, "site_image_count": int}
    On failure returns {"match": false, "error": "..."} — the comparison is
    non-blocking, so errors never prevent the downstream download.
    """
    try:
        data = request.get_json()
        if not data or "ebay_photos" not in data:
            return jsonify({"error": "ebay_photos is required"}), 400
        if not data.get("site_url"):
            return jsonify({"error": "site_url is required"}), 400

        ebay_photos = data["ebay_photos"]
        if not isinstance(ebay_photos, list) or not all(isinstance(u, str) for u in ebay_photos):
            return jsonify({"error": "ebay_photos must be a list of strings"}), 400

        site_url = data["site_url"].strip()

        try:
            site_image_urls = _scrape_site_image_urls(site_url)
        except Exception as e:
            print(f"[API] compare-images scrape error: {e}")
            return jsonify({"match": False, "error": f"Image scrape failed: {str(e)}"}), 200

        ebay_images = _download_images_as_pil(ebay_photos)
        site_images = _download_images_as_pil(site_image_urls)

        matched_pairs = find_matching_pairs(ebay_images, site_images, threshold=COMPARE_IMAGES_THRESHOLD)

        return jsonify({
            "match": len(matched_pairs) > 0,
            "matched_pairs": matched_pairs,
            "ebay_image_count": len(ebay_images),
            "site_image_count": len(site_images),
        }), 200

    except Exception as e:
        print(f"[API] compare-images error: {e}")
        return jsonify({"match": False, "error": f"Image comparison failed: {str(e)}"}), 200


@app.route('/api/test-3d-site-images', methods=['GET'])
def test_3d_site_images():
    """Probe each site's image scraper against a known public model. Probes run
    concurrently — the Cults3D probe launches a browser and can take a minute."""
    probes = [
        ("printables.com", probe_images_printables),
        ("thingiverse.com", probe_images_thingiverse),
        ("makerworld.com", probe_images_makerworld),
        ("cults3d.com", probe_images_cults3d),
        ("thangs.com", probe_images_thangs),
    ]

    def run_probe(site, probe_fn):
        try:
            ok, message = probe_fn()
        except Exception as e:
            ok, message = False, str(e)
        if not ok:
            print(f"[test-3d-site-images] {site} FAILED: {message}")
        return site, {"ok": ok, "message": message}

    results = {}
    with ThreadPoolExecutor(max_workers=len(probes)) as executor:
        futures = [executor.submit(run_probe, site, fn) for site, fn in probes]
        for future in as_completed(futures):
            site, result = future.result()
            results[site] = result
    return jsonify({"results": results})


@app.route('/api/makerworld-session/open', methods=['POST'])
def makerworld_session_open():
    """Open a headed MakerWorld browser and leave it open so the user can fix
    whatever the pipeline is stuck on (login, email verification code,
    Cloudflare challenge). The session persists in the local browser profile
    when the window closes."""
    data = request.get_json(silent=True) or {}
    url = data.get('url') or None
    ok, message = mw_open_session(url)
    if not ok:
        return jsonify({"error": message}), 409
    return jsonify({"ok": True, "message": message})


@app.route('/api/makerworld-session/status', methods=['GET'])
def makerworld_session_status():
    """Report whether the session browser is still open (detects the user
    closing the window), the current page, and a best-effort logged-in guess."""
    return jsonify(mw_session_status())


@app.route('/api/makerworld-session/close', methods=['POST'])
def makerworld_session_close():
    """Close the session browser gracefully, saving cookies to the profile."""
    ok, message = mw_close_session()
    return jsonify({"ok": ok, "message": message})


@app.route('/api/makerworld-probe', methods=['POST'])
def makerworld_probe_endpoint():
    """Re-test the MakerWorld pipeline after the user fixed the session in the
    headed browser. Runs the genuine download probe."""
    ok, message = probe_makerworld()
    return jsonify({"ok": ok, "message": message})


@app.route('/api/cults3d-credential-status', methods=['GET'])
def cults3d_credential_status():
    """Return the auth state for Cults3D (email/password or cookies)."""
    cookies = os.environ.get("CULTS3D_COOKIES", "").strip()
    email = os.environ.get("CULTS3D_EMAIL", "").strip()
    password = os.environ.get("CULTS3D_PASSWORD", "").strip()
    has_credentials = bool(cookies or (email and password))
    auth_type = "cookies" if cookies else ("email" if (email and password) else None)
    masked_email = ""
    if email:
        at = email.find("@")
        local = email[:at] if at > 0 else email
        domain = email[at:] if at > 0 else ""
        masked_email = local[:2] + "*" * max(0, len(local) - 2) + domain
    return jsonify({
        "has_credentials": has_credentials,
        "auth_type": auth_type,
        "email": masked_email,
    })


@app.route('/api/cults3d-credentials', methods=['POST'])
def update_cults3d_credentials():
    """Save CULTS3D_COOKIES to the .env file."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        cookies = str(data.get('cookies', '')).strip()

        if not cookies:
            return jsonify({"error": "Cookie string is required"}), 400

        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            lines = []

        new_lines = []
        found = False
        for line in lines:
            if line.strip().startswith('CULTS3D_COOKIES='):
                new_lines.append(f'CULTS3D_COOKIES={cookies}\n')
                found = True
            else:
                new_lines.append(line)

        if not found:
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines.append('\n')
            new_lines.append(f'CULTS3D_COOKIES={cookies}\n')

        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        load_dotenv(env_path, override=True)
        print("[API] Cults3D cookies updated in .env")
        return jsonify({"success": True, "message": "Cults3D cookies saved."})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to save cookies: {str(e)}"}), 500


@app.route('/api/cults3d-email-credentials', methods=['POST'])
def update_cults3d_email_credentials():
    """Save CULTS3D_EMAIL and CULTS3D_PASSWORD to the .env file."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        email = str(data.get('email', '')).strip()
        password = str(data.get('password', '')).strip()

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        updates = {'CULTS3D_EMAIL': email, 'CULTS3D_PASSWORD': password}

        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            lines = []

        new_lines = []
        found = {name: False for name in updates}
        for line in lines:
            replaced = False
            for name, value in updates.items():
                if line.strip().startswith(name + '='):
                    new_lines.append(f'{name}={value}\n')
                    found[name] = True
                    replaced = True
                    break
            if not replaced:
                new_lines.append(line)

        for name, was_found in found.items():
            if not was_found:
                if new_lines and not new_lines[-1].endswith('\n'):
                    new_lines.append('\n')
                new_lines.append(f'{name}={updates[name]}\n')

        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        load_dotenv(env_path, override=True)
        print("[API] Cults3D email credentials updated in .env")
        return jsonify({"success": True, "message": "Email credentials saved."})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to save credentials: {str(e)}"}), 500


@app.route('/api/cults3d-auto-load-cookies', methods=['POST'])
def cults3d_auto_load_cookies():
    """Read Cults3D cookies from the user's installed browser and save them to .env."""
    try:
        cookies = cults3d_load_cookies_from_browser()

        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            lines = []

        new_lines = []
        found = False
        for line in lines:
            if line.strip().startswith('CULTS3D_COOKIES='):
                new_lines.append(f'CULTS3D_COOKIES={cookies}\n')
                found = True
            else:
                new_lines.append(line)

        if not found:
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines.append('\n')
            new_lines.append(f'CULTS3D_COOKIES={cookies}\n')

        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        load_dotenv(env_path, override=True)
        print("[API] Cults3D cookies auto-loaded from browser")
        return jsonify({"success": True, "message": "Cookies loaded from browser and saved."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _update_env_vars(updates: dict) -> None:
    """Write key=value pairs into the project .env, replacing existing keys."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []

    new_lines = []
    found = {name: False for name in updates}
    for line in lines:
        replaced = False
        for name, value in updates.items():
            if line.strip().startswith(name + '='):
                new_lines.append(f'{name}={value}\n')
                found[name] = True
                replaced = True
                break
        if not replaced:
            new_lines.append(line)

    for name, was_found in found.items():
        if not was_found:
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines.append('\n')
            new_lines.append(f'{name}={updates[name]}\n')

    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    load_dotenv(env_path, override=True)


@app.route('/api/makerworld-credential-status', methods=['GET'])
def makerworld_credential_status():
    """Return the auth state for MakerWorld (email/password or existing session profile)."""
    email = os.environ.get("MAKERWORLD_EMAIL", "").strip()
    password = os.environ.get("MAKERWORLD_PASSWORD", "").strip()
    has_credentials = bool(email and password)
    masked_email = ""
    if email:
        at = email.find("@")
        local = email[:at] if at > 0 else email
        domain = email[at:] if at > 0 else ""
        masked_email = local[:2] + "*" * max(0, len(local) - 2) + domain
    profile_present = os.path.isdir(
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     'backend', 'downloaders', 'makerworld_profile')
    )
    return jsonify({
        "has_credentials": has_credentials,
        "auth_type": "email" if has_credentials else None,
        "email": masked_email,
        "profile_present": profile_present,
    })


@app.route('/api/makerworld-email-credentials', methods=['POST'])
def update_makerworld_email_credentials():
    """Save MAKERWORLD_EMAIL and MAKERWORLD_PASSWORD to the .env file."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        email = str(data.get('email', '')).strip()
        password = str(data.get('password', '')).strip()

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        _update_env_vars({'MAKERWORLD_EMAIL': email, 'MAKERWORLD_PASSWORD': password})
        print("[API] MakerWorld email credentials updated in .env")
        return jsonify({"success": True, "message": "Email credentials saved."})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to save credentials: {str(e)}"}), 500


# Root directory for persisted Saved 3D Files (GLOSSARY: "Saved 3D File") —
# the downloaded 3D file and its site-image directory live under here; the
# database stores the paths. Module-level so tests can monkeypatch it.
SAVED_3D_FILES_DIR = _SAVED_3D_FILES_DIR_NAME

# Source-site label for a 3D file page URL (the first whitelisted host that appears)
_SOURCE_SITE_HOSTS = ("thingiverse.com", "printables.com", "makerworld.com", "cults3d.com", "thangs.com", "yeggi.com")


def _source_site_from_link(link):
    for host in _SOURCE_SITE_HOSTS:
        if host in link:
            return host
    return ""


def _list_saved_3d_file_images(images_dir):
    """Sorted image filenames inside a Saved 3D File's images_dir, or []."""
    if not images_dir or not os.path.isdir(images_dir):
        return []
    try:
        return sorted(
            name for name in os.listdir(images_dir)
            if os.path.isfile(os.path.join(images_dir, name))
        )
    except OSError:
        return []


def _autosave_saved_3d_file(data, link, out_filename, out_bytes):
    """Persist a Saved 3D File (GLOSSARY) after a successful download, when the
    pipeline sent the metadata. Best-effort: any failure is logged, never raised,
    so it can never break the download response.

    - The 3D file is written to Saved_3D_Files/<id>.<ext>
    - Site images are scraped and downloaded into Saved_3D_Files/<id>_images/
      (eBay photos are NOT stored — only the listing URL)
    - The record is inserted into the saved_3d_files table
    """
    ebay_listing_url = str(data.get("ebay_listing_url") or "").strip()
    pipeline = str(data.get("pipeline") or "").strip()
    if not ebay_listing_url or not pipeline:
        return  # no pipeline metadata — a manual Step 3 download, nothing to save
    try:
        _db.ensure_db()
        ext = os.path.splitext(out_filename)[1] or ".zip"
        os.makedirs(SAVED_3D_FILES_DIR, exist_ok=True)

        # Reserve the id first so the on-disk names can use it
        record_id = _db.save_saved_3d_file({
            "ebay_listing_url": ebay_listing_url,
            "ebay_listing_title": str(data.get("ebay_listing_title") or "").strip(),
            "source_site": _source_site_from_link(link),
            "source_url": link,
            "match_label": str(data.get("match_label") or "").strip(),
            "pipeline": pipeline,
            "file_path": "",
            "images_dir": "",
        })

        file_path = os.path.join(SAVED_3D_FILES_DIR, f"{record_id}{ext}")
        with open(file_path, "wb") as f:
            f.write(out_bytes)

        # Site images are best-effort: scrape + download, skip any that fail
        images_dir = ""
        try:
            image_urls = _scrape_site_image_urls(link)
            if image_urls:
                images_dir = os.path.join(SAVED_3D_FILES_DIR, f"{record_id}_images")
                os.makedirs(images_dir, exist_ok=True)
                for index, url in enumerate(image_urls):
                    try:
                        content = _download_image(url)
                        img_ext = os.path.splitext(url.split("?")[0])[1].lower()
                        if img_ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                            img_ext = ".jpg"
                        name = os.path.basename(url.split("?")[0]) or f"image_{index}{img_ext}"
                        if not os.path.splitext(name)[1]:
                            name += img_ext
                        with open(os.path.join(images_dir, name), "wb") as f:
                            f.write(content)
                    except Exception as e:
                        print(f"[API] saved-3d-files: skipping undownloadable site image {url}: {e}")
        except Exception as e:
            print(f"[API] saved-3d-files: site image scrape failed for {link}: {e}")
            images_dir = ""

        _db.update_saved_3d_file_paths(record_id, file_path=file_path, images_dir=images_dir)
        print(f"[API] Saved 3D file #{record_id}: {out_filename} ({pipeline})")
    except Exception as e:
        print(f"[API] saved-3d-files autosave failed: {e}")


@app.route('/api/download-3d-file', methods=['POST'])
def download_3d_file():
    """
    Download a 3D file from a supported site.

    Expects JSON: {
      "link": "https://...",
      "file_download_delay": 1.0,
      "mode": "full_zip" | "single_file"   (default: "full_zip")
    }
    Supported: thingiverse.com, printables.com, makerworld.com, cults3d.com, thangs.com
    """
    try:
        data = request.get_json()
        if not data or not data.get("link"):
            return jsonify({"error": "link is required"}), 400

        link = data["link"].strip()
        file_download_delay = float(data.get("file_download_delay", 0.0))
        mode = data.get("mode", DOWNLOAD_MODE_FULL_ZIP)
        if mode not in DOWNLOAD_MODES:
            return jsonify({"error": f"mode must be one of: {', '.join(DOWNLOAD_MODES)}"}), 400

        filename: str
        raw_bytes: bytes
        is_zip: bool

        # --- Thingiverse ---
        if "thingiverse.com" in link:
            thing_id = extract_thing_id(link)
            print(f"[API] Downloading Thingiverse thing:{thing_id}")
            filename, raw_bytes = tv_stream_zip(thing_id, file_download_delay=file_download_delay)
            is_zip = True

        # --- Printables ---
        elif "printables.com" in link:
            model_id = printables_model_id(link)
            print(f"[API] Downloading Printables model:{model_id}")
            filename, raw_bytes = printables_build_zip(model_id, file_download_delay=file_download_delay)
            is_zip = True

        # --- MakerWorld ---
        elif "makerworld.com" in link:
            slug, instance_id = mw_extract_model_info(link)
            print(f"[API] Downloading MakerWorld model:{slug} instance:{instance_id}")
            filename, raw_bytes = mw_download_3mf(slug, instance_id)
            is_zip = False  # single .3mf — bypasses extraction in both modes; add any future single-file site the same way

        # --- Cults3D ---
        elif "cults3d.com" in link:
            try:
                slug = cults3d_extract_slug(link)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            print(f"[API] Downloading Cults3D creation:{slug}")
            filename, raw_bytes = cults3d_stream_zip(link, file_download_delay=file_download_delay)
            is_zip = True

        # --- Thangs ---
        elif "thangs.com" in link:
            try:
                model_id = thangs_extract_model_id(link)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            print(f"[API] Downloading Thangs model:{model_id}")
            filename, raw_bytes = thangs_build_zip(link, file_download_delay=file_download_delay)
            is_zip = True

        else:
            return jsonify({"error": "Unsupported site — supported: thingiverse.com, printables.com, makerworld.com, cults3d.com, thangs.com"}), 400

        # --- Apply mode ---
        out_filename = filename
        out_bytes = raw_bytes
        mime = "application/zip" if is_zip else "application/octet-stream"
        if mode == DOWNLOAD_MODE_SINGLE_FILE and is_zip:
            try:
                out_filename, out_bytes = extract_best_3d_file(raw_bytes)
            except ValueError as e:
                return jsonify({"error": str(e)}), 500
            mime = "application/octet-stream"

        # --- Auto-save a Saved 3D File record when the pipeline sent metadata ---
        _autosave_saved_3d_file(data, link, out_filename, out_bytes)

        return Response(
            out_bytes,
            status=200,
            mimetype=mime,
            headers={"Content-Disposition": f'attachment; filename="{out_filename}"'},
        )

    except (Cults3DPaidModelError, ThangsPaidModelError) as e:
        return jsonify({"error": str(e)}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except RuntimeError as e:
        print(f"[API] download-3d-file upstream error: {e}")
        return jsonify({"error": str(e)}), 502
    except requests.exceptions.HTTPError as e:
        print(f"[API] download-3d-file HTTP error: {e}")
        return jsonify({"error": f"Upstream download failed: {e.response.status_code}"}), 502
    except requests.exceptions.RequestException as e:
        print(f"[API] download-3d-file request error: {e}")
        return jsonify({"error": "Download request failed"}), 502
    except Exception as e:
        print(f"[API] download-3d-file error: {e}")
        return jsonify({"error": f"Download failed: {str(e)}"}), 500


@app.route('/api/saved-3d-files', methods=['GET'])
def list_saved_3d_files():
    """Paginated list of Saved 3D Files, newest first.

    Query params: page (default 1), page_size (default 25).
    Returns JSON: {"items": [...], "total": int, "page": int, "page_size": int}
    """
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 25))
    except (TypeError, ValueError):
        return jsonify({"error": "page and page_size must be integers"}), 400
    _db.ensure_db()
    result = _db.list_saved_3d_files(page=page, page_size=page_size)
    for item in result["items"]:
        item["images"] = _list_saved_3d_file_images(item.get("images_dir"))
    return jsonify(result), 200


@app.route('/api/saved-3d-files/<int:entry_id>', methods=['GET'])
def get_saved_3d_file(entry_id):
    """Full detail for one Saved 3D File."""
    _db.ensure_db()
    row = _db.get_saved_3d_file(entry_id)
    if row is None:
        return jsonify({"error": "Saved 3D file not found"}), 404
    row["images"] = _list_saved_3d_file_images(row.get("images_dir"))
    return jsonify(row), 200


@app.route('/api/saved-3d-files/<int:entry_id>', methods=['DELETE'])
def delete_saved_3d_file(entry_id):
    """Delete a Saved 3D File: removes the database record and its on-disk
    3D file + site-image directory."""
    _db.ensure_db()
    row = _db.get_saved_3d_file(entry_id)
    if row is None:
        return jsonify({"error": "Saved 3D file not found"}), 404
    for path, is_dir in ((row.get("file_path"), False), (row.get("images_dir"), True)):
        if not path:
            continue
        try:
            if is_dir:
                shutil.rmtree(path, ignore_errors=True)
            elif os.path.exists(path):
                os.remove(path)
        except OSError as e:
            print(f"[API] saved-3d-files delete: could not remove {path}: {e}")
    _db.delete_saved_3d_file(entry_id)
    return jsonify({"success": True}), 200


@app.route('/api/saved-3d-files/<int:entry_id>/images/<path:filename>', methods=['GET'])
def serve_saved_3d_file_image(entry_id, filename):
    """Serve one locally stored site image of a Saved 3D File.

    The filename must be a plain basename (no path separators) that exists in
    the record's images_dir — this rejects path traversal by construction.
    """
    _db.ensure_db()
    row = _db.get_saved_3d_file(entry_id)
    if row is None:
        return jsonify({"error": "Saved 3D file not found"}), 404
    if not filename or os.path.basename(filename) != filename:
        return jsonify({"error": "Invalid filename"}), 400
    images_dir = row.get("images_dir") or ""
    if not images_dir:
        return jsonify({"error": "Image not found"}), 404
    filepath = os.path.join(images_dir, filename)
    if not os.path.isfile(filepath):
        return jsonify({"error": "Image not found"}), 404
    mimetype = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
    with open(filepath, 'rb') as f:
        return Response(f.read(), mimetype=mimetype)


@app.route('/api/saved-3d-files/<int:entry_id>/download', methods=['GET'])
def download_saved_3d_file(entry_id):
    """Re-download the stored 3D file of a Saved 3D File as an attachment."""
    _db.ensure_db()
    row = _db.get_saved_3d_file(entry_id)
    if row is None:
        return jsonify({"error": "Saved 3D file not found"}), 404
    file_path = row.get("file_path") or ""
    if not file_path or not os.path.isfile(file_path):
        return jsonify({"error": "3D file not found on disk"}), 404
    filename = os.path.basename(file_path)
    with open(file_path, 'rb') as f:
        data = f.read()
    return Response(
        data,
        status=200,
        mimetype="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
        image_bytes = downscale_image_bytes(file.read())
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


@app.route('/api/remove-backgrounds-batch', methods=['POST'])
def api_remove_backgrounds_batch():
    """
    Remove backgrounds from a list of photo URLs in batch, streaming progress.

    Accepts JSON body:
    {
        "photos": ["url1", "url2", ...],
        "sku": "076"
    }

    Streams NDJSON: one progress event per image, then a result event with
    { "bgRemovedPhotos": { "<originalUrl>": "/api/bg-removed-image/<file>", ... } }
    Failed images are silently skipped (omitted from the result map).
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    photos = data.get("photos", [])
    sku = data.get("sku", "unknown")
    if not re.match(r'^[\w\-]{1,64}$', sku):
        return jsonify({"error": "Invalid SKU"}), 400

    if not photos:
        return jsonify({"error": "No photos provided"}), 400

    def generate():
        bg_removed_map = {}
        total = len(photos)
        os.makedirs("generated-images", exist_ok=True)

        for idx, url in enumerate(photos):
            step_label = f"Removing background {idx + 1} of {total}"
            yield progress_event(step_label, "in_progress")
            try:
                img_response = requests.get(url, timeout=15)
                img_response.raise_for_status()
                scaled_bytes = downscale_image_bytes(img_response.content)
                result_bytes = remove_background(scaled_bytes)
                filename = f"bg_removed_{sku}_{idx}.png"
                filepath = os.path.join("generated-images", filename)
                with open(filepath, 'wb') as f:
                    f.write(result_bytes)
                bg_removed_map[url] = f"/api/bg-removed-image/{filename}"
                yield progress_event(step_label, "completed")
            except Exception as e:
                print(f"[API] /api/remove-backgrounds-batch: skipping {url}: {e}")

        yield result_event({"bgRemovedPhotos": bg_removed_map})

    return streaming_response(generate())


@app.route('/api/bg-removed-image/<filename>', methods=['GET'])
def serve_bg_removed_image(filename):
    """Serve a bg-removed PNG from generated-images/. Validates filename pattern."""
    if not re.match(r'^bg_removed_[\w\-]+_\d+\.png$', filename):
        return jsonify({"error": "Invalid filename"}), 400
    filepath = os.path.join("generated-images", filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    with open(filepath, 'rb') as f:
        return Response(f.read(), mimetype='image/png')


@app.route('/api/render', methods=['POST'])
def start_render():
    """
    Stream a Render Job (Step 4 Studio Render) for an uploaded 3D model as NDJSON.

    Accepts multipart/form-data:
        file:       model file (.stl/.obj/.ply used as-is; .step/.stp/.3mf are
                    normalized to an STL Render Mesh before Blender sees them)
        color:      optional hex color (default near-black #1a1a1a)
        roughness:  optional 0..1 (default 0.3)
        resolution: optional square size, one of RENDER_RESOLUTIONS (default 1024)
        fov:        optional vertical field of view in degrees (default 40, range 20-80)
        finish:     optional Surface Finish ("smooth" or "layer-lines")
        layer_height_mm / layer_depth:
                    optional Layer Lines sub-settings (real FDM layer height,
                    bump strength)
        key_energy / fill_energy / rim_energy:
                    optional light intensities (defaults 150/60/250)
        ambient:    optional world background strength (default 0.35)
        shadow:     optional "true"/"false" — key light casts a shadow (default true)
        shadow_softness: optional key light disk size (default 1.5)
        exposure:   optional global multiplier on all energies + world (default 1.0)
        shot_mode:  optional "single" or "multi" (default single)
        rig:        optional JSON list of cameras [{"azimuth": 0, "elevation": 0}]
                    for multi Shot Mode; each camera renders one image, sequentially
        camera_position / camera_target:
                    optional "x,y,z" in three.js (Y-up) preview coordinates; both or
                    neither. Converted to Blender (Z-up) azimuth/elevation; distance
                    is auto-computed to frame the whole model (Camera Intent).

    Multi Shot Mode renders the rig cameras SEQUENTIALLY (Cycles CPU saturates the
    machine), streaming a per-shot progress event as each camera starts.

    Streams NDJSON events:
        { "type": "progress", "step": "render", "status": "sample N/M",
          "current": N, "total": M, "remaining_seconds": float|null,
          "shot": i, "shots": K }   (shot/shots present on multi-shot runs)
        { "type": "result", "data": { "image": url, "filename": str,
                                      "images": [url, ...] } }
        { "type": "error", "error": friendly message }
    """
    print("[API] /api/render endpoint called")
    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify({"error": "A model file is required"}), 400

    extension = os.path.splitext(file.filename)[1].lower()
    if extension not in SUPPORTED_RENDER_EXTENSIONS:
        return jsonify({
            "error": f"'{extension or file.filename}' files are not supported for rendering. "
                     f"Supported formats: {', '.join(SUPPORTED_RENDER_EXTENSIONS)}",
        }), 400

    color = request.form.get("color", DEFAULT_RENDER_COLOR)
    try:
        roughness = validate_roughness(request.form.get("roughness", DEFAULT_RENDER_ROUGHNESS))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    try:
        resolution = validate_resolution(request.form.get("resolution", DEFAULT_RENDER_RESOLUTION))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Camera Intent: preview camera (three.js coords) -> Blender azimuth/elevation
    try:
        fov = validate_fov(request.form.get("fov", DEFAULT_RENDER_FOV))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Expanded Render Settings: lighting, shadows, exposure, Surface Finish
    def parse_float(field, default, minimum, maximum):
        raw = request.form.get(field)
        if raw is None:
            return default, None
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None, f"{field} must be a number between {minimum} and {maximum}"
        if not minimum <= value <= maximum:
            return None, f"{field} must be between {minimum} and {maximum}"
        return value, None

    expanded = {}
    for field, default, minimum, maximum in (
        ("key_energy", DEFAULT_RENDER_KEY_ENERGY, 0.0, RENDER_ENERGY_MAX),
        ("fill_energy", DEFAULT_RENDER_FILL_ENERGY, 0.0, RENDER_ENERGY_MAX),
        ("rim_energy", DEFAULT_RENDER_RIM_ENERGY, 0.0, RENDER_ENERGY_MAX),
        ("ambient", DEFAULT_RENDER_AMBIENT, 0.0, RENDER_AMBIENT_MAX),
        ("shadow_softness", DEFAULT_RENDER_SHADOW_SOFTNESS, RENDER_SHADOW_SOFTNESS_MIN, RENDER_SHADOW_SOFTNESS_MAX),
        ("exposure", DEFAULT_RENDER_EXPOSURE, RENDER_EXPOSURE_MIN, RENDER_EXPOSURE_MAX),
        ("layer_height_mm", DEFAULT_RENDER_LAYER_HEIGHT_MM, RENDER_LAYER_HEIGHT_MM_MIN, RENDER_LAYER_HEIGHT_MM_MAX),
        ("layer_depth", DEFAULT_RENDER_LAYER_DEPTH, RENDER_LAYER_DEPTH_MIN, RENDER_LAYER_DEPTH_MAX),
    ):
        value, error = parse_float(field, default, minimum, maximum)
        if error:
            return jsonify({"error": error}), 400
        expanded[field] = value

    finish = request.form.get("finish", DEFAULT_RENDER_FINISH)
    if finish not in RENDER_FINISHES:
        return jsonify({"error": f"finish must be one of {list(RENDER_FINISHES)}"}), 400

    raw_shadow = request.form.get("shadow")
    if raw_shadow is None:
        shadow = DEFAULT_RENDER_SHADOW
    elif raw_shadow.lower() in ("true", "1", "on", "yes"):
        shadow = True
    elif raw_shadow.lower() in ("false", "0", "off", "no"):
        shadow = False
    else:
        return jsonify({"error": "shadow must be true or false"}), 400

    def parse_vec3(field):
        raw = request.form.get(field)
        if raw is None:
            return None
        parts = raw.split(",")
        if len(parts) != 3:
            raise ValueError
        return tuple(float(p) for p in parts)

    try:
        camera_position = parse_vec3("camera_position")
        camera_target = parse_vec3("camera_target")
    except (TypeError, ValueError):
        return jsonify({"error": "camera_position and camera_target must be \"x,y,z\" numbers"}), 400
    if (camera_position is None) != (camera_target is None):
        return jsonify({"error": "camera_position and camera_target must be sent together"}), 400
    if camera_position is not None:
        try:
            azimuth, elevation = compute_blender_camera(camera_position, camera_target)
        except ValueError:
            return jsonify({"error": "camera position and target must differ"}), 400
    else:
        azimuth, elevation = DEFAULT_RENDER_AZIMUTH, DEFAULT_RENDER_ELEVATION

    # Shot Mode + Camera Rig: multi runs one sequential Render Job per rig
    # camera (Cycles CPU saturates the machine — never parallel). An empty
    # rig in multi mode falls back to the single camera above.
    shot_mode = request.form.get("shot_mode", DEFAULT_RENDER_SHOT_MODE)
    if shot_mode not in RENDER_SHOT_MODES:
        return jsonify({"error": f"shot_mode must be one of {list(RENDER_SHOT_MODES)}"}), 400
    rig = []
    raw_rig = request.form.get("rig")
    if raw_rig is not None:
        try:
            rig = validate_rig(json.loads(raw_rig))
        except (ValueError, TypeError):
            return jsonify({"error": "rig must be a JSON list of cameras like [{\"azimuth\": 0, \"elevation\": 0}]"}), 400
    cameras = rig if (shot_mode == "multi" and rig) else [{"azimuth": azimuth, "elevation": elevation}]

    os.makedirs(GENERATED_IMAGES_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def claim_filename(name):
        suffix = 1
        while os.path.exists(os.path.join(GENERATED_IMAGES_DIR, name)):
            stem, dot, ext = name.rpartition(".")
            base = stem.rsplit("_", 1)[0] if suffix > 1 else stem
            name = f"{base}_{suffix}{dot}{ext}"
            suffix += 1
        return name

    if shot_mode == "multi":
        filenames = [claim_filename(f"{RENDER_OUTPUT_PREFIX}{timestamp}_shot{i + 1}.png")
                     for i in range(len(cameras))]
    else:
        filenames = [claim_filename(f"{RENDER_OUTPUT_PREFIX}{timestamp}.png")]

    fd, input_path = tempfile.mkstemp(prefix="render_upload_", suffix=extension)
    os.close(fd)
    file.save(input_path)

    def generate():
        try:
            yield progress_event("render", "Preparing the model...")
            # Normalize to the Render Mesh first (native formats pass through).
            # The converted STL is cache-owned — only the uploaded temp is removed below.
            mesh_path = normalize_to_render_mesh(input_path)

            shots_total = len(cameras)
            images = []
            # Multi Shot Mode runs the rig cameras SEQUENTIALLY (Cycles CPU
            # saturates the machine — never parallel), one Render Job per camera.
            for shot_index, (camera, shot_filename) in enumerate(zip(cameras, filenames)):
                output_path = os.path.join(GENERATED_IMAGES_DIR, shot_filename)
                if shots_total > 1:
                    yield json.dumps({
                        "type": "progress", "step": "render",
                        "status": f"shot {shot_index + 1} of {shots_total}",
                        "shot": shot_index + 1, "shots": shots_total,
                    }) + "\n"
                # Drive Blender and stream each Cycles checkpoint as it arrives.
                progress = iter_render_progress(
                    mesh_path, output_path,
                    color=color, roughness=roughness, resolution=resolution,
                    azimuth=camera["azimuth"], elevation=camera["elevation"], fov=fov,
                    finish=finish,
                    layer_height_mm=expanded["layer_height_mm"],
                    layer_depth=expanded["layer_depth"],
                    key_energy=expanded["key_energy"],
                    fill_energy=expanded["fill_energy"],
                    rim_energy=expanded["rim_energy"],
                    ambient=expanded["ambient"],
                    shadow=shadow,
                    shadow_softness=expanded["shadow_softness"],
                    exposure=expanded["exposure"],
                )
                while True:
                    try:
                        current, total, remaining_seconds = next(progress)
                    except StopIteration:
                        break
                    event = {
                        "type": "progress", "step": "render",
                        "status": f"sample {current}/{total}",
                        "current": current, "total": total,
                        "remaining_seconds": remaining_seconds,
                    }
                    if shots_total > 1:
                        event["shot"] = shot_index + 1
                        event["shots"] = shots_total
                    yield json.dumps(event) + "\n"
                images.append(f"/api/render-image/{shot_filename}")
            yield result_event({
                "image": images[0],
                "filename": filenames[0],
                "images": images,
            })
        except RenderError as e:
            print(f"[API] /api/render failed: {e}")
            yield error_event(str(e))
        except Exception as e:
            print(f"[API] /api/render unexpected error: {e}")
            yield error_event(f"Unexpected render error: {e}")
        finally:
            try:
                os.remove(input_path)
            except OSError:
                pass

    return streaming_response(generate())


@app.route('/api/render-preview', methods=['POST'])
def render_preview():
    """
    Return the normalized Render Mesh (STL bytes) for an uploaded model.

    Accepts multipart/form-data with a 'file' field (.stl/.obj/.ply pass
    through; .step/.stp/.3mf are converted server-side). The Step 4 panel
    previews exactly these bytes, so preview and render show identical geometry.

    Returns:
        STL bytes (model/stl), or a JSON friendly error
    """
    try:
        file = request.files.get('file')
        if not file or not file.filename:
            return jsonify({"error": "A model file is required"}), 400

        extension = os.path.splitext(file.filename)[1].lower()
        fd, input_path = tempfile.mkstemp(prefix="render_preview_", suffix=extension or ".bin")
        os.close(fd)
        try:
            file.save(input_path)
            mesh_path = normalize_to_render_mesh(input_path)
            with open(mesh_path, 'rb') as f:
                return Response(f.read(), mimetype='model/stl')
        finally:
            try:
                os.remove(input_path)
            except OSError:
                pass
    except RenderError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred while preparing the preview: {str(e)}"}), 500


@app.route('/api/render-image/<filename>', methods=['GET'])
def serve_render_image(filename):
    """Serve a rendered PNG from the generated-images dir. Validates filename pattern."""
    if not re.match(rf'^{RENDER_OUTPUT_PREFIX}\d{{8}}_\d{{6}}(_(shot)?\d+)?\.png$', filename):
        return jsonify({"error": "Invalid filename"}), 400
    filepath = os.path.join(GENERATED_IMAGES_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    with open(filepath, 'rb') as f:
        return Response(f.read(), mimetype='image/png')


@app.route('/api/render-settings', methods=['GET', 'POST'])
def api_render_settings():
    """
    Read or update persisted Render Settings (Step 4 Studio Render).

    GET:        returns the full Render Settings surface (material, lighting,
                shadows, exposure, resolution, fov, shot mode, camera rig)
    POST:       JSON body with any subset of those keys; persists and returns
                the saved state. Camera angle/target are ephemeral by design.
    """
    if request.method == 'GET':
        try:
            return jsonify(get_render_settings()), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    body = request.get_json(silent=True) or {}
    try:
        settings = save_render_settings(
            color=body.get('color'),
            roughness=body.get('roughness'),
            resolution=body.get('resolution'),
            fov=body.get('fov'),
            finish=body.get('finish'),
            layer_height_mm=body.get('layer_height_mm'),
            layer_depth=body.get('layer_depth'),
            key_energy=body.get('key_energy'),
            fill_energy=body.get('fill_energy'),
            rim_energy=body.get('rim_energy'),
            ambient=body.get('ambient'),
            shadow=body.get('shadow'),
            shadow_softness=body.get('shadow_softness'),
            exposure=body.get('exposure'),
            shot_mode=body.get('shot_mode'),
            rig=body.get('rig'),
        )
        return jsonify(settings), 200
    except (TypeError, ValueError) as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/render-profiles', methods=['GET', 'POST'])
def api_render_profiles():
    """
    List or create Render Profiles (named snapshots of the full Render Settings).

    GET:        returns {"profiles": {name: settings}, "active": name|null}.
                active=null means "Current Settings" (the flat render settings),
                which is the implicit default and never a stored profile.
    POST:       JSON body {"name": str, "settings": {...}}; creates the profile
                and returns it. Duplicate names are rejected with 400 — use
                POST/PUT /api/render-profiles/<name> to overwrite.
    """
    if request.method == 'GET':
        try:
            return jsonify({
                'profiles': get_render_profiles(),
                'active': get_active_render_profile(),
            }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    body = request.get_json(silent=True) or {}
    name = body.get('name')
    try:
        if name is not None and str(name).strip() in get_render_profiles():
            return jsonify({'error': f"A render profile named '{str(name).strip()}' already exists"}), 400
        profile = save_render_profile(name, body.get('settings'))
        return jsonify(profile), 201
    except (TypeError, ValueError) as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/render-profiles/<name>', methods=['POST', 'PUT', 'DELETE'])
def api_render_profile_by_name(name):
    """
    Update (overwrite) or delete one Render Profile by name.

    POST/PUT:   JSON body {"settings": {...}}; overwrites the stored snapshot.
    DELETE:     removes the profile; if it was active, active resets to null
                ("Current Settings").
    """
    if request.method == 'DELETE':
        try:
            if delete_render_profile(name):
                return jsonify({'deleted': name}), 200
            return jsonify({'error': f"No render profile named '{name}'"}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    if name not in get_render_profiles():
        return jsonify({'error': f"No render profile named '{name}'"}), 404
    body = request.get_json(silent=True) or {}
    try:
        profile = save_render_profile(name, body.get('settings'))
        return jsonify(profile), 200
    except (TypeError, ValueError) as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/render-profiles/active', methods=['POST'])
def api_render_profile_active():
    """
    Set the active Render Profile. JSON body {"name": str|null}; null selects
    "Current Settings" (the flat render settings).
    """
    body = request.get_json(silent=True) or {}
    try:
        active = set_active_render_profile(body.get('name'))
        return jsonify({'active': active}), 200
    except (TypeError, ValueError) as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload-image', methods=['POST'])
def api_upload_image():
    """
    Upload a PNG/JPEG image to eBay Picture Services.
    
    Accepts a multipart/form-data request with an 'image' file field.
    
    Returns:
        JSON with the eBay-hosted image URL.
    """
    try:
        file = request.files.get('image')
        if not file:
            return jsonify({"error": "No image file provided"}), 400

        print(f"[API] /api/upload-image called with file: {file.filename}")
        image_bytes = file.read()

        if not image_bytes:
            return jsonify({"error": "Empty image file"}), 400

        user_token = os.getenv('user_token')
        if not user_token:
            return jsonify({"error": "eBay user token not configured"}), 500

        content_type = file.content_type or 'image/png'

        print(f"[API] Uploading {len(image_bytes)} bytes to eBay Picture Services...")
        ebay_url = upload_image_bytes_to_ebay(image_bytes, content_type, picture_name="Uploaded Image")
        if ebay_url:
            print(f"[API] Image uploaded successfully: {ebay_url}")
            return jsonify({"url": ebay_url}), 200

        print("[API] eBay upload failed (no URL returned)")
        return jsonify({"error": "eBay upload failed"}), 502

    except Exception as e:
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred during image upload (encoding error)"

        import traceback
        traceback.print_exc()

        return jsonify({
            "error": f"An error occurred during image upload: {error_msg}"
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


@app.route('/api/tokens', methods=['GET'])
def get_tokens():
    """Get current token values (masked) from the .env file"""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    tokens = {'user_token': '', 'application_token': ''}
    token_last_updated_ms = None

    try:
        token_last_updated_ms = int(os.path.getmtime(env_path) * 1000)
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith('user_token='):
                    tokens['user_token'] = stripped[len('user_token='):]
                elif stripped.startswith('application_token='):
                    tokens['application_token'] = stripped[len('application_token='):]
    except Exception as e:
        return jsonify({"error": f"Failed to read .env: {str(e)}"}), 500

    def mask(val):
        if not val:
            return ''
        if len(val) > 30:
            return val[:15] + '...' + val[-15:]
        return val

    return jsonify({
        'user_token': mask(tokens['user_token']),
        'application_token': mask(tokens['application_token']),
        'user_token_set': bool(tokens['user_token']),
        'application_token_set': bool(tokens['application_token']),
        'user_token_valid': None,
        'application_token_valid': None,
        'token_last_updated_ms': token_last_updated_ms
    })


@app.route('/api/update-tokens', methods=['POST'])
def update_tokens():
    """
    Update user_token and/or application_token in the .env file.
    Handles values with special characters like ^ # = etc.
    Writes values unquoted to avoid shell-escaping issues.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        user_token = data.get('user_token', '').strip()
        application_token = data.get('application_token', '').strip()

        if not user_token and not application_token:
            return jsonify({"error": "At least one token must be provided"}), 400

        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

        # Read current .env file preserving exact content
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        user_token_found = False
        app_token_found = False

        for line in lines:
            stripped = line.strip()
            if user_token and stripped.startswith('user_token='):
                new_lines.append(f'user_token={user_token}\n')
                user_token_found = True
            elif application_token and stripped.startswith('application_token='):
                new_lines.append(f'application_token={application_token}\n')
                app_token_found = True
            else:
                new_lines.append(line)

        # Append tokens that weren't found in the file
        if user_token and not user_token_found:
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines.append('\n')
            new_lines.append(f'user_token={user_token}\n')
        if application_token and not app_token_found:
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines.append('\n')
            new_lines.append(f'application_token={application_token}\n')

        # Write back the file
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        print(f"[API] Tokens updated in .env - user_token: {'yes' if user_token else 'no'}, application_token: {'yes' if application_token else 'no'}")

        return jsonify({
            "success": True,
            "message": "Tokens updated successfully",
            "user_token_updated": bool(user_token),
            "application_token_updated": bool(application_token)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to update tokens: {str(e)}"}), 500


@app.route('/api/refresh-tokens', methods=['POST'])
def api_refresh_tokens():
    """Refresh both user and application tokens via OAuth."""
    try:
        from backend.refreshToken import refresh_user_and_app_token
        result = refresh_user_and_app_token()
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        load_dotenv(env_path, override=True)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


_API_KEY_NAMES = ('openrouter_api_key', 'bedrock_api_key')


def _mask_secret(val):
    if not val:
        return ''
    if len(val) > 30:
        return val[:15] + '...' + val[-15:]
    return val


@app.route('/api/api-keys', methods=['GET'])
def get_api_keys():
    """Get current API key values (masked) from the .env file."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    values = {name: '' for name in _API_KEY_NAMES}

    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                for name in _API_KEY_NAMES:
                    prefix = name + '='
                    if stripped.startswith(prefix):
                        values[name] = stripped[len(prefix):]
                        break
    except FileNotFoundError:
        pass
    except Exception as e:
        return jsonify({"error": f"Failed to read .env: {str(e)}"}), 500

    response = {}
    for name in _API_KEY_NAMES:
        response[name] = _mask_secret(values[name])
        response[f'{name}_set'] = bool(values[name])
    return jsonify(response)


@app.route('/api/api-keys', methods=['POST'])
def update_api_keys():
    """
    Update openrouter_api_key and/or bedrock_api_key in the .env file.
    Writes values unquoted to preserve any special characters.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        updates = {}
        for name in _API_KEY_NAMES:
            raw = data.get(name)
            if raw is None:
                continue
            value = str(raw).strip()
            if value:
                updates[name] = value

        if not updates:
            return jsonify({"error": "At least one API key must be provided"}), 400

        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            lines = []

        new_lines = []
        found = {name: False for name in updates}
        for line in lines:
            stripped = line.strip()
            replaced = False
            for name, value in updates.items():
                if stripped.startswith(name + '='):
                    new_lines.append(f'{name}={value}\n')
                    found[name] = True
                    replaced = True
                    break
            if not replaced:
                new_lines.append(line)

        for name, was_found in found.items():
            if not was_found:
                if new_lines and not new_lines[-1].endswith('\n'):
                    new_lines.append('\n')
                new_lines.append(f'{name}={updates[name]}\n')

        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        load_dotenv(env_path, override=True)

        # ebay_cli caches openrouter_api_key at import time and mirrors
        # bedrock_api_key into AWS_BEARER_TOKEN_BEDROCK for boto3; refresh
        # both so new keys take effect without a server restart.
        try:
            import backend.ebay_cli as ebay_cli
            if 'openrouter_api_key' in updates:
                ebay_cli.OPENROUTER_API_KEY = os.getenv('openrouter_api_key')
            if 'bedrock_api_key' in updates:
                ebay_cli._sync_bedrock_bearer_token()
        except Exception:
            pass

        print(
            "[API] API keys updated in .env - "
            + ", ".join(f"{name}: yes" for name in updates)
        )

        result = {"success": True, "message": "API keys updated successfully"}
        for name in _API_KEY_NAMES:
            result[f'{name}_updated'] = name in updates
        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to update API keys: {str(e)}"}), 500


@app.route('/api/text-models', methods=['GET'])
def get_text_models():
    """Return the text models the user can actually call right now,
    gated by which provider API keys are set in the .env file."""
    from backend.text_models import get_available_text_models
    return jsonify({"models": get_available_text_models()})


def _test_text_model_result(payload=None, error=None, log_lines=None):
    """Structured result for api_test_ai_model (avoids tuple unpack mismatches)."""
    return {
        'payload': payload,
        'error': error,
        'server_log': '\n'.join(log_lines) if log_lines else None,
    }


def _test_text_model(prompt, model):
    from backend.text_models import is_bedrock_model, is_openrouter_model

    log = []

    def add(line):
        log.append(line)
        print(line)

    def fail(message):
        return _test_text_model_result(error=message, log_lines=log)

    def ok(content):
        return _test_text_model_result(
            payload={'content': content.strip()},
            log_lines=log,
        )

    if is_bedrock_model(model):
        if not os.getenv('bedrock_api_key'):
            add('Bedrock API key is not set.')
            return fail('Bedrock API key is not set. Add bedrock_api_key in Settings.')
        add(f'Calling Bedrock model: {model}')
        try:
            from backend.ebay_cli import (
                _BEDROCK_REGION,
                _extract_bedrock_message_text,
                _sync_bedrock_bearer_token,
            )

            _sync_bedrock_bearer_token()
            import boto3

            client = boto3.client(
                service_name='bedrock-runtime',
                region_name=_BEDROCK_REGION,
            )
            response = client.converse(
                modelId=model,
                messages=[
                    {
                        'role': 'user',
                        'content': [{'text': prompt}],
                    }
                ],
            )
            content = _extract_bedrock_message_text(response)
            if content:
                add('Received response from Bedrock.')
                return ok(content)
            add('Bedrock returned no text content.')
            return fail('No response from the text model.')
        except ImportError:
            add('boto3 is not installed. Run: pip install -r requirements.txt')
            return fail('boto3 is not installed.')
        except Exception as e:
            add(f'Error calling Bedrock API: {e}')
            import traceback
            add(traceback.format_exc().strip())
            return fail('No response from the text model.')

    if is_openrouter_model(model) and not os.getenv('openrouter_api_key'):
        add('OpenRouter API key is not set.')
        return fail('OpenRouter API key is not set. Add openrouter_api_key in Settings.')

    api_key = os.getenv('openrouter_api_key')
    url = 'https://openrouter.ai/api/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    data = {
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
    }

    add(f'Calling OpenRouter model: {model}')
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        add(f'HTTP {response.status_code}')
        body_preview = (response.text or '')[:4000]
        if body_preview:
            add(f'Response body: {body_preview}')
        response.raise_for_status()
        result = response.json()
        if 'choices' in result and result['choices']:
            content = result['choices'][0].get('message', {}).get('content', '')
            if content:
                add('Received response from OpenRouter.')
                return ok(str(content))
        add('Unexpected response format: no choices in response.')
        return fail('No response from the text model.')
    except requests.exceptions.RequestException as e:
        add(f'Error calling OpenRouter API: {e}')
        return fail('No response from the text model.')
    except json.JSONDecodeError as e:
        add(f'Error parsing OpenRouter response: {e}')
        return fail('No response from the text model.')
    except Exception as e:
        add(f'Unexpected error: {e}')
        import traceback
        add(traceback.format_exc().strip())
        return fail('No response from the text model.')


def _test_image_model(prompt, model):
    import base64

    api_key = os.getenv('openrouter_api_key')
    if not api_key:
        return None, 'OpenRouter API key is not set. Add openrouter_api_key in Settings.'

    url = 'https://openrouter.ai/api/v1/images'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    data = {
        'model': model,
        'prompt': prompt,
        'aspect_ratio': '1:1',
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        result = response.json()
    except requests.exceptions.RequestException as e:
        detail = ''
        if getattr(e, 'response', None) is not None:
            try:
                detail = e.response.json().get('error', {}).get('message', '')
            except Exception:
                detail = (e.response.text or '')[:300]
        msg = str(e) if not detail else f'{e} — {detail}'
        return None, msg

    parsed = _openrouter_response_dict_to_image_bytes_and_mime(result)
    if parsed:
        image_bytes, mime_type = parsed
        b64 = base64.b64encode(image_bytes).decode('ascii')
        data_url = f'data:{mime_type};base64,{b64}'
        return {
            'content': 'Image generated successfully.',
            'image_url': data_url,
        }, None

    if 'choices' in result and result['choices']:
        message = result['choices'][0].get('message', {})
        text = message.get('content', '')
        if isinstance(text, list):
            text = ' '.join(
                part.get('text', '') for part in text if isinstance(part, dict)
            )
        if text and str(text).strip():
            return {'content': str(text).strip()}, None

    return None, (
        'Model responded but no image was returned. '
        'Try a different prompt or image model.'
    )


@app.route('/api/test-ai-model', methods=['POST'])
def api_test_ai_model():
    """
    Quick connectivity test for text or image generation models via OpenRouter.

    JSON body: { "kind": "text"|"image", "model": "...", "prompt": "..." }
    """
    try:
        data = request.get_json() or {}
        kind = (data.get('kind') or 'text').strip().lower()
        model = (data.get('model') or '').strip()
        prompt = (data.get('prompt') or '').strip()

        if kind not in ('text', 'image'):
            return jsonify({'error': 'kind must be "text" or "image"'}), 400
        if not model:
            return jsonify({'error': 'model is required'}), 400
        if not prompt:
            return jsonify({'error': 'prompt is required'}), 400

        server_log = None
        if kind == 'text':
            text_result = _test_text_model(prompt, model)
            payload = text_result['payload']
            err = text_result['error']
            server_log = text_result['server_log']
        else:
            payload, err = _test_image_model(prompt, model)

        if err:
            body = {'error': err}
            if server_log:
                body['server_log'] = server_log
            return jsonify(body), 502
        return jsonify({'error': None, **payload}), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok"}), 200


class _QuietTokensRequestHandler(WSGIRequestHandler):
    """Omit access-log lines for frequent GET /api/tokens status polls."""

    def log_request(self, code="-", size="-"):
        path = self.path.split("?", 1)[0]
        if path == "/api/tokens":
            return
        super().log_request(code, size)


def _free_port_from_stale_backend(port: int) -> None:
    """Kill a stale AxisResearcher backend still holding `port`.

    A previous backend can be orphaned when its terminal dies without shutting
    Flask down. Without this, a new `npm run dev` cannot bind the port and the
    frontend ends up proxying to the stale process serving old code.
    Only kills processes whose command line looks like `python ... app.py`.
    """
    import socket
    import subprocess

    def port_is_free() -> bool:
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return False
        probe.close()
        return True

    if port_is_free():
        return

    try:
        out = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True, text=True, timeout=15,
        ).stdout
    except Exception:
        return

    pids = set()
    for line in out.splitlines():
        parts = line.split()
        if (
            len(parts) >= 5
            and parts[0] == "TCP"
            and parts[1].endswith(f":{port}")
            and parts[3].upper() == "LISTENING"
        ):
            pids.add(parts[-1])

    for pid in pids:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"],
                capture_output=True, text=True, timeout=15,
            )
            cmdline = (r.stdout or "").lower()
        except Exception:
            continue
        if "python" in cmdline and "app.py" in cmdline:
            print(f"[startup] Port {port} is held by a stale backend (PID {pid}); killing it.")
            subprocess.run(["taskkill", "/PID", pid, "/T", "/F"],
                           capture_output=True, timeout=15)

    for _ in range(20):
        if port_is_free():
            return
        time.sleep(0.5)
    print(f"[startup] WARNING: port {port} is still busy; Flask may fail to bind.")


if __name__ == '__main__':
    _free_port_from_stale_backend(5000)
    try:
        # Create axis.db and, on first run, migrate all existing JSON data into it.
        _db.ensure_db()
    except Exception as e:
        print(f"[startup] database initialization failed: {e}")
    try:
        migrate_hide_not_found_listings()
    except Exception as e:
        print(f"[startup] migrate_hide_not_found_listings failed: {e}")
    # Warm the lazy rembg import off the critical path so the first
    # background-removal request doesn't pay the ~2.5s import. Daemon thread:
    # never blocks shutdown, and warm_rembg swallows its own import errors.
    threading.Thread(target=warm_rembg, daemon=True).start()
    app.run(debug=True, use_reloader=False, port=5000, request_handler=_QuietTokensRequestHandler)
