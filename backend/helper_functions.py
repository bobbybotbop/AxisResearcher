"""
Helper Functions Module

This module contains utility functions extracted from ebay_cli.py
for better code organization and reusability.
"""

import os
import re
import requests
from dotenv import load_dotenv

# Load .env from project root (one level up from backend/)
_env_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_env_dir, '.env'))

# Constants
APPLICATION_TOKEN = os.getenv('application_token')
REFRESH_TOKEN = os.getenv('refresh_token')


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


def helper_get_valid_token():
    """Get a valid access token, refresh if needed"""
    if not APPLICATION_TOKEN:
        print("❌ No application token available")
        print("🔄 Attempting to refresh access token...")
        new_token = refreshToken()
        return new_token
    else:
        return APPLICATION_TOKEN


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
    """Open eBay OAuth link for token refresh"""
    import webbrowser
    webbrowser.open("https://developer.ebay.com/my/auth/?env=production&index=0")

    
