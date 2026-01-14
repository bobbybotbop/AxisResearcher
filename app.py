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

from flask import Flask, jsonify
from flask_cors import CORS
from copyScripts.CopyListingMain import copy_listing_main

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
                "listing": None
            }), 404
        
        return jsonify({
            "photos": result.get("photos", []),
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
            "listing": None
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
