"""
Create Image Module

This module contains functions for generating images using OpenRouter's Gemini 2.5 Flash Image API.
"""

import os
import json
import base64
import requests
import xml.etree.ElementTree as ET
from enum import Enum
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from helper_functions import helper_get_valid_token

# Load environment variables
load_dotenv()

# eBay API credentials
CLIENT_ID = os.getenv('client_id')
API_KEY = os.getenv('api_key')
CLIENT_SECRET = os.getenv('client_secret')
USER_TOKEN = os.getenv('user_token')


class ImageType(Enum):
    """Enum for image generation types."""
    PROFESSIONAL = "PROFESSIONAL"
    REAL_WORLD = "REAL_WORLD"


def generate_image_from_urls(image_urls, image_type):
    """
    Generate an image using OpenRouter's Gemini 2.5 Flash Image API from input image URLs.
    Saves the API response as JSON to api-responses/ directory.
    
    Args:
        image_urls (list[str]): Array of image URLs to use as input
        image_type (ImageType): Enum value indicating PROFESSIONAL or REAL_WORLD
    
    Returns:
        str: Path to the saved JSON response file, or None on failure
    """
    # Load API key
    openrouter_api_key = os.getenv('openrouter_api_key')
    if not openrouter_api_key:
        print("❌ OpenRouter API key not found. Please set openrouter_api_key in your .env file")
        return None
    
    # Validate image_type
    if not isinstance(image_type, ImageType):
        print(f"❌ Invalid image_type. Must be ImageType.PROFESSIONAL or ImageType.REAL_WORLD")
        return None
    
    # Validate image_urls
    if not image_urls or not isinstance(image_urls, list) or len(image_urls) == 0:
        print("❌ image_urls must be a non-empty list of image URLs")
        return None
    
    # Load the appropriate prompt file based on image_type
    if image_type == ImageType.PROFESSIONAL:
        prompt_file_path = "prompts/generateImageFromProfessional"
    else:  # ImageType.REAL_WORLD
        prompt_file_path = "prompts/generateImageFromWorld"
    
    try:
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            prompt_text = f.read().strip()
    except FileNotFoundError:
        print(f"❌ Prompt file not found: {prompt_file_path}")
        return None
    except Exception as e:
        print(f"❌ Error loading prompt file: {e}")
        return None
    
    # Construct the content array for the API request
    content = [
        {
            "type": "text",
            "text": prompt_text
        }
    ]
    
    # Add image URLs to content array
    for image_url in image_urls:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": image_url
            }
        })
    
    # Prepare API request
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json",
    }
    
    data = {
        "model": "google/gemini-2.5-flash-image",
        "messages": [
            {
                "role": "user",
                "content": content
            }
        ]
    }
    
    try:
        print(f"🤖 Calling OpenRouter Gemini 2.5 Flash Image API ({image_type.value})...")
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        print("✅ Received response from OpenRouter API")
        
        # Save the JSON response to a file
        try:
            # Create api-responses directory if it doesn't exist
            output_dir = Path("api-responses")
            output_dir.mkdir(exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"response_{image_type.value}_{timestamp}.json"
            file_path = output_dir / filename
            
            # Save the JSON response
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"✅ API response saved to: {file_path}")
            return str(file_path)
            
        except Exception as e:
            print(f"❌ Error saving API response: {e}")
            import traceback
            traceback.print_exc()
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error calling OpenRouter API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"Error details: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"Error response: {e.response.text[:200]}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing OpenRouter response: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def decode_image_from_response():
    """
    Decode and save an image from the most recent OpenRouter API response JSON file.
    Automatically finds the most recent JSON file in the api-responses directory.
    
    Returns:
        str: Path to the saved image file, or None on failure
    """
    try:
        # Find the most recent JSON file in api-responses directory
        output_dir = Path("api-responses")
        if not output_dir.exists():
            print(f"❌ api-responses directory not found")
            return None
        
        # Get all JSON files in the directory
        json_files = list(output_dir.glob("*.json"))
        if not json_files:
            print(f"❌ No JSON files found in api-responses directory")
            return None
        
        # Sort by modification time and get the most recent
        json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        json_path = json_files[0]
        
        print(f"📖 Using most recent API response: {json_path}")
        
        if not json_path.exists():
            print(f"❌ JSON file not found: {json_path}")
            return None
        
        with open(json_path, 'r', encoding='utf-8') as f:
            result = json.load(f)
        
        print(f"📖 Reading API response from: {json_path}")
        
        # Parse response to extract generated image URL or base64 data
        # The response format may vary, but typically contains image data or URL
        image_data = None
        image_url = None
        is_base64 = False
        mime_type = None  # Store mime type from inline_data if available
        
        if 'choices' in result and len(result['choices']) > 0:
            choice = result['choices'][0]
            message = choice.get('message', {})
            
            # Check for images array in message (Gemini API format)
            if 'images' in message and isinstance(message['images'], list) and len(message['images']) > 0:
                # Extract images from the images array
                for img_obj in message['images']:
                    if isinstance(img_obj, dict):
                        # Check for image_url format
                        if img_obj.get('type') == 'image_url':
                            image_url_data = img_obj.get('image_url', {})
                            if isinstance(image_url_data, dict):
                                extracted_url = image_url_data.get('url', '')
                                if extracted_url:
                                    # Check if it's a data URI (base64)
                                    if extracted_url.startswith('data:image'):
                                        is_base64 = True
                                        # Extract mime type from data URI
                                        if 'image/png' in extracted_url:
                                            mime_type = 'image/png'
                                        elif 'image/jpeg' in extracted_url or 'image/jpg' in extracted_url:
                                            mime_type = 'image/jpeg'
                                        elif 'image/webp' in extracted_url:
                                            mime_type = 'image/webp'
                                        else:
                                            mime_type = 'image/png'  # Default
                                        
                                        # Extract base64 data from data URI
                                        if ',' in extracted_url:
                                            image_data = extracted_url.split(',', 1)[1]
                                        else:
                                            image_data = extracted_url
                                        print(f"✅ Found image in images array (mime_type: {mime_type})")
                                        break  # Use the first image found
                                    elif extracted_url.startswith('http://') or extracted_url.startswith('https://'):
                                        image_url = extracted_url
                                        break
                            elif isinstance(image_url_data, str):
                                if image_url_data.startswith('data:image'):
                                    is_base64 = True
                                    if ',' in image_url_data:
                                        image_data = image_url_data.split(',', 1)[1]
                                        # Extract mime type
                                        if 'image/png' in image_url_data:
                                            mime_type = 'image/png'
                                        elif 'image/jpeg' in image_url_data or 'image/jpg' in image_url_data:
                                            mime_type = 'image/jpeg'
                                        elif 'image/webp' in image_url_data:
                                            mime_type = 'image/webp'
                                        else:
                                            mime_type = 'image/png'
                                    else:
                                        image_data = image_url_data
                                    print(f"✅ Found image in images array (mime_type: {mime_type})")
                                    break
                                elif image_url_data.startswith('http'):
                                    image_url = image_url_data
                                    break
            
            # Fallback: Check content field if images array not found
            if not image_url and not image_data:
                message_content = message.get('content', '')
                
                # Check if content is a string (might be JSON string or direct URL)
                if isinstance(message_content, str):
                    if message_content.strip():
                        # Try to parse as JSON first
                        try:
                            content_json = json.loads(message_content)
                            # Look for image URL in various possible formats
                            if isinstance(content_json, dict):
                                image_url = content_json.get('url') or content_json.get('image_url') or content_json.get('imageUrl')
                                image_data = content_json.get('image_data') or content_json.get('b64_json')
                        except json.JSONDecodeError:
                            # If not JSON, check if it's a direct URL
                            if message_content.startswith('http'):
                                image_url = message_content.strip()
                            elif message_content.startswith('data:image'):
                                # Data URI
                                is_base64 = True
                                image_data = message_content.split(',', 1)[1] if ',' in message_content else message_content
                            else:
                                # Might be raw base64
                                try:
                                    # Try to decode to verify it's base64
                                    base64.b64decode(message_content)
                                    is_base64 = True
                                    image_data = message_content
                                except:
                                    pass
                elif isinstance(message_content, dict):
                    image_url = message_content.get('url') or message_content.get('image_url') or message_content.get('imageUrl')
                    image_data = message_content.get('image_data') or message_content.get('b64_json')
                elif isinstance(message_content, list):
                    # Content might be an array of content parts (most common format)
                    # Check for inline_data structure first (Gemini format)
                    for part in message_content:
                        if isinstance(part, dict):
                            # Check for inline_data structure (Gemini API format)
                            if 'inline_data' in part:
                                inline_data = part.get('inline_data', {})
                                if isinstance(inline_data, dict) and 'data' in inline_data:
                                    image_data = inline_data.get('data')
                                    mime_type = inline_data.get('mime_type', 'image/png')
                                    is_base64 = True
                                    print(f"✅ Found image in inline_data format (mime_type: {mime_type})")
                                    break  # Use the first image found
                            
                            # Legacy format: type == 'image_url'
                            if part.get('type') == 'image_url':
                                image_url_data = part.get('image_url', {})
                                if isinstance(image_url_data, dict):
                                    extracted_url = image_url_data.get('url')
                                    if extracted_url:
                                        # Check if it's a URL or base64
                                        if extracted_url.startswith('http://') or extracted_url.startswith('https://'):
                                            image_url = extracted_url
                                        elif extracted_url.startswith('data:image'):
                                            is_base64 = True
                                            image_data = extracted_url.split(',', 1)[1] if ',' in extracted_url else extracted_url
                                            # Extract mime type from data URI
                                            if 'image/png' in extracted_url:
                                                mime_type = 'image/png'
                                            elif 'image/jpeg' in extracted_url or 'image/jpg' in extracted_url:
                                                mime_type = 'image/jpeg'
                                            elif 'image/webp' in extracted_url:
                                                mime_type = 'image/webp'
                                        else:
                                            # Likely raw base64 data
                                            try:
                                                base64.b64decode(extracted_url)
                                                is_base64 = True
                                                image_data = extracted_url
                                            except:
                                                # If decoding fails, treat as URL anyway
                                                image_url = extracted_url
                                elif isinstance(image_url_data, str):
                                    if image_url_data.startswith('http'):
                                        image_url = image_url_data
                                    else:
                                        try:
                                            base64.b64decode(image_url_data)
                                            is_base64 = True
                                            image_data = image_url_data
                                        except:
                                            image_url = image_url_data
                                break
                            elif part.get('type') == 'text' and part.get('text', '').startswith('http'):
                                image_url = part.get('text', '').strip()
                                break
                            elif part.get('type') == 'image_data':
                                image_data = part.get('image_data')
                                is_base64 = True
                                break
                
                # Check message for image_url directly
                if not image_url and not image_data and 'image_url' in message:
                    image_url = message.get('image_url')
        
        # Check alternative response formats
        if not image_url and not image_data:
            # Check if there's an image in the response directly
            if 'image' in result:
                image_data = result['image']
                is_base64 = True
            elif 'data' in result:
                if isinstance(result['data'], list) and len(result['data']) > 0:
                    item = result['data'][0]
                    image_url = item.get('url')
                    image_data = item.get('b64_json') or item.get('base64_image')
                elif isinstance(result['data'], dict):
                    image_url = result['data'].get('url')
                    image_data = result['data'].get('b64_json') or result['data'].get('base64_image')
            elif 'url' in result:
                image_url = result['url']
            elif 'b64_json' in result:
                image_data = result['b64_json']
                is_base64 = True
        
        if not image_url and not image_data:
            print(f"❌ Could not find image URL or base64 data in response.")
            print(f"Full response: {json.dumps(result, indent=2)}")
            return None
        
        if image_data:
            print("✅ Found base64 image data in response.")
            is_base64 = True
        elif image_url:
            print(f"✅ Found image URL in response: {image_url[:100]}...")
        
        # Handle base64 encoded image or URL
        if is_base64 and image_data:
            # Already have base64 data
            pass
        elif image_url:
            # Check if it's a base64 data URI
            if image_url.startswith('data:image/'):
                is_base64 = True
                # Extract base64 data from data URI (format: data:image/png;base64,<data>)
                if ',' in image_url:
                    image_data = image_url.split(',', 1)[1]
                else:
                    image_data = image_url
            elif image_url.startswith('http://') or image_url.startswith('https://'):
                # It's a regular URL, will download it
                is_base64 = False
            else:
                # Assume it's raw base64 data
                try:
                    base64.b64decode(image_url)
                    is_base64 = True
                    image_data = image_url
                except:
                    # If decoding fails, treat as URL
                    is_base64 = False
        
        try:
            if is_base64 and image_data:
                print("📥 Decoding base64 image data...")
                # Decode base64 data
                try:
                    image_bytes = base64.b64decode(image_data)
                    # Determine file extension from mime_type if available
                    if mime_type:
                        if 'jpeg' in mime_type or 'jpg' in mime_type:
                            ext = '.jpg'
                        elif 'png' in mime_type:
                            ext = '.png'
                        elif 'webp' in mime_type:
                            ext = '.webp'
                        else:
                            ext = '.png'  # Default to png
                    else:
                        ext = '.png'  # Default to png for base64 images
                except Exception as e:
                    print(f"❌ Error decoding base64 data: {e}")
                    return None
            elif image_url:
                print("📥 Downloading generated image...")
                img_response = requests.get(image_url, timeout=30)
                img_response.raise_for_status()
                image_bytes = img_response.content
                
                # Determine file extension from content type or URL
                content_type = img_response.headers.get('content-type', '')
                if 'jpeg' in content_type or 'jpg' in content_type:
                    ext = '.jpg'
                elif 'png' in content_type:
                    ext = '.png'
                elif 'webp' in content_type:
                    ext = '.webp'
                else:
                    # Try to infer from URL
                    if '.jpg' in image_url.lower() or '.jpeg' in image_url.lower():
                        ext = '.jpg'
                    elif '.png' in image_url.lower():
                        ext = '.png'
                    elif '.webp' in image_url.lower():
                        ext = '.webp'
                    else:
                        ext = '.jpg'  # Default to jpg
            else:
                print("❌ No image data or URL found")
                return None
            
            # Create output directory if it doesn't exist
            output_dir = Path("generated-images")
            output_dir.mkdir(exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Try to infer image type from JSON filename if possible
            json_filename = json_path.stem
            if 'PROFESSIONAL' in json_filename.upper():
                image_type_str = 'professional'
            elif 'REAL_WORLD' in json_filename.upper() or 'REALWORLD' in json_filename.upper():
                image_type_str = 'real_world'
            else:
                image_type_str = 'generated'
            
            filename = f"generated_{image_type_str}_{timestamp}{ext}"
            file_path = output_dir / filename
            
            # Save the image
            with open(file_path, 'wb') as f:
                f.write(image_bytes)
            
            print(f"✅ Image saved to: {file_path}")
            return str(file_path)
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error downloading image: {e}")
            return None
        except Exception as e:
            print(f"❌ Error processing image: {e}")
            import traceback
            traceback.print_exc()
            return None
            
    except FileNotFoundError:
        print(f"❌ JSON file not found: {json_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON file: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return None


def upload_image_to_ebay(picture_name="Uploaded Image"):
    """
    Upload a base64-encoded image to eBay Picture Services.
    Automatically finds and parses the most recent JSON file in api-responses directory.
    
    Args:
        picture_name (str): Optional name for the picture (default: "Uploaded Image")
    
    Returns:
        str: Full URL of the uploaded image, or None on failure
    """
    # Validate eBay credentials - only need token for OAuth, but check if legacy headers are available
    # Note: We're trying OAuth-only first, but Trading API might require legacy headers
    if not CLIENT_ID:
        print("⚠️ Warning: CLIENT_ID not found, but trying OAuth-only authentication")
    
    # Get user token from environment (Trading API requires user token, not application token)
    valid_token = USER_TOKEN
    if not valid_token:
        print("❌ Error: Could not get valid user token")
        print("💡 Make sure user_token is set in your .env file")
        return None
    
    # Find the most recent JSON file in api-responses directory
    try:
        output_dir = Path("api-responses")
        if not output_dir.exists():
            print(f"❌ api-responses directory not found")
            return None
        
        # Get all JSON files in the directory
        json_files = list(output_dir.glob("*.json"))
        if not json_files:
            print(f"❌ No JSON files found in api-responses directory")
            return None
        
        # Sort by modification time and get the most recent
        json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        json_path = json_files[0]
        
        print(f"📖 Using most recent API response: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            result = json.load(f)
        
        print(f"📖 Reading API response from: {json_path}")
        
    except FileNotFoundError:
        print(f"❌ JSON file not found")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON file: {e}")
        return None
    except Exception as e:
        print(f"❌ Error reading JSON file: {e}")
        return None
    
    # Parse response to extract generated image URL or base64 data
    # Using the same logic as decode_image_from_response
    image_data = None
    image_url = None
    is_base64 = False
    mime_type = None  # Store mime type from inline_data if available
    
    if 'choices' in result and len(result['choices']) > 0:
        choice = result['choices'][0]
        message = choice.get('message', {})
        
        # Check for images array in message (Gemini API format)
        if 'images' in message and isinstance(message['images'], list) and len(message['images']) > 0:
            # Extract images from the images array
            for img_obj in message['images']:
                if isinstance(img_obj, dict):
                    # Check for image_url format
                    if img_obj.get('type') == 'image_url':
                        image_url_data = img_obj.get('image_url', {})
                        if isinstance(image_url_data, dict):
                            extracted_url = image_url_data.get('url', '')
                            if extracted_url:
                                # Check if it's a data URI (base64)
                                if extracted_url.startswith('data:image'):
                                    is_base64 = True
                                    # Extract mime type from data URI
                                    if 'image/png' in extracted_url:
                                        mime_type = 'image/png'
                                    elif 'image/jpeg' in extracted_url or 'image/jpg' in extracted_url:
                                        mime_type = 'image/jpeg'
                                    elif 'image/webp' in extracted_url:
                                        mime_type = 'image/webp'
                                    else:
                                        mime_type = 'image/png'  # Default
                                    
                                    # Extract base64 data from data URI
                                    # Format: data:image/png;base64,<base64_data>
                                    if ',' in extracted_url:
                                        image_data = extracted_url.split(',', 1)[1]
                                        print(f"✅ Extracted base64 data from data URI ({len(image_data)} characters)")
                                    else:
                                        image_data = extracted_url
                                    print(f"✅ Found image in images array (mime_type: {mime_type})")
                                    break  # Use the first image found
                                elif extracted_url.startswith('http://') or extracted_url.startswith('https://'):
                                    image_url = extracted_url
                                    break
                        elif isinstance(image_url_data, str):
                            if image_url_data.startswith('data:image'):
                                is_base64 = True
                                if ',' in image_url_data:
                                    image_data = image_url_data.split(',', 1)[1]
                                    # Extract mime type
                                    if 'image/png' in image_url_data:
                                        mime_type = 'image/png'
                                    elif 'image/jpeg' in image_url_data or 'image/jpg' in image_url_data:
                                        mime_type = 'image/jpeg'
                                    elif 'image/webp' in image_url_data:
                                        mime_type = 'image/webp'
                                    else:
                                        mime_type = 'image/png'
                                else:
                                    image_data = image_url_data
                                print(f"✅ Found image in images array (mime_type: {mime_type})")
                                break
                            elif image_url_data.startswith('http'):
                                image_url = image_url_data
                                break
        
        # Fallback: Check content field if images array not found
        if not image_url and not image_data:
            message_content = message.get('content', '')
            
            # Check if content is a string (might be JSON string or direct URL)
            if isinstance(message_content, str):
                if message_content.strip():
                    # Try to parse as JSON first
                    try:
                        content_json = json.loads(message_content)
                        # Look for image URL in various possible formats
                        if isinstance(content_json, dict):
                            image_url = content_json.get('url') or content_json.get('image_url') or content_json.get('imageUrl')
                            image_data = content_json.get('image_data') or content_json.get('b64_json')
                    except json.JSONDecodeError:
                        # If not JSON, check if it's a direct URL
                        if message_content.startswith('http'):
                            image_url = message_content.strip()
                        elif message_content.startswith('data:image'):
                            # Data URI
                            is_base64 = True
                            image_data = message_content.split(',', 1)[1] if ',' in message_content else message_content
                        else:
                            # Might be raw base64
                            try:
                                # Try to decode to verify it's base64
                                base64.b64decode(message_content)
                                is_base64 = True
                                image_data = message_content
                            except:
                                pass
            elif isinstance(message_content, dict):
                image_url = message_content.get('url') or message_content.get('image_url') or message_content.get('imageUrl')
                image_data = message_content.get('image_data') or message_content.get('b64_json')
            elif isinstance(message_content, list):
                # Content might be an array of content parts (most common format)
                # Check for inline_data structure first (Gemini format)
                for part in message_content:
                    if isinstance(part, dict):
                        # Check for inline_data structure (Gemini API format)
                        if 'inline_data' in part:
                            inline_data = part.get('inline_data', {})
                            if isinstance(inline_data, dict) and 'data' in inline_data:
                                image_data = inline_data.get('data')
                                mime_type = inline_data.get('mime_type', 'image/png')
                                is_base64 = True
                                print(f"✅ Found image in inline_data format (mime_type: {mime_type})")
                                break  # Use the first image found
                        
                        # Legacy format: type == 'image_url'
                        if part.get('type') == 'image_url':
                            image_url_data = part.get('image_url', {})
                            if isinstance(image_url_data, dict):
                                extracted_url = image_url_data.get('url')
                                if extracted_url:
                                    # Check if it's a URL or base64
                                    if extracted_url.startswith('http://') or extracted_url.startswith('https://'):
                                        image_url = extracted_url
                                    elif extracted_url.startswith('data:image'):
                                        is_base64 = True
                                        image_data = extracted_url.split(',', 1)[1] if ',' in extracted_url else extracted_url
                                        # Extract mime type from data URI
                                        if 'image/png' in extracted_url:
                                            mime_type = 'image/png'
                                        elif 'image/jpeg' in extracted_url or 'image/jpg' in extracted_url:
                                            mime_type = 'image/jpeg'
                                        elif 'image/webp' in extracted_url:
                                            mime_type = 'image/webp'
                                    else:
                                        # Likely raw base64 data
                                        try:
                                            base64.b64decode(extracted_url)
                                            is_base64 = True
                                            image_data = extracted_url
                                        except:
                                            # If decoding fails, treat as URL anyway
                                            image_url = extracted_url
                            elif isinstance(image_url_data, str):
                                if image_url_data.startswith('http'):
                                    image_url = image_url_data
                                else:
                                    try:
                                        base64.b64decode(image_url_data)
                                        is_base64 = True
                                        image_data = image_url_data
                                    except:
                                        image_url = image_url_data
                            break
                        elif part.get('type') == 'text' and part.get('text', '').startswith('http'):
                            image_url = part.get('text', '').strip()
                            break
                        elif part.get('type') == 'image_data':
                            image_data = part.get('image_data')
                            is_base64 = True
                            break
            
            # Check message for image_url directly
            if not image_url and not image_data and 'image_url' in message:
                image_url = message.get('image_url')
    
    # Check alternative response formats
    if not image_url and not image_data:
        # Check if there's an image in the response directly
        if 'image' in result:
            image_data = result['image']
            is_base64 = True
        elif 'data' in result:
            if isinstance(result['data'], list) and len(result['data']) > 0:
                item = result['data'][0]
                image_url = item.get('url')
                image_data = item.get('b64_json') or item.get('base64_image')
            elif isinstance(result['data'], dict):
                image_url = result['data'].get('url')
                image_data = result['data'].get('b64_json') or result['data'].get('base64_image')
        elif 'url' in result:
            image_url = result['url']
        elif 'b64_json' in result:
            image_data = result['b64_json']
            is_base64 = True
    
    if not image_url and not image_data:
        print(f"❌ Could not find image URL or base64 data in response.")
        print(f"Full response: {json.dumps(result, indent=2)}")
        return None
    
    if image_data:
        print("✅ Found base64 image data in response.")
        is_base64 = True
    elif image_url:
        print(f"✅ Found image URL in response: {image_url[:100]}...")
        # If we have a URL but need base64, we can't proceed
        print("❌ Image is a URL, not base64 data. Cannot upload URL to eBay.")
        return None
    
    # Handle base64 encoded image
    if is_base64 and image_data:
        # Already have base64 data
        pass
    elif image_url:
        # Check if it's a base64 data URI
        if image_url.startswith('data:image/'):
            is_base64 = True
            # Extract base64 data from data URI (format: data:image/png;base64,<data>)
            if ',' in image_url:
                image_data = image_url.split(',', 1)[1]
            else:
                image_data = image_url
        else:
            print("❌ Image is a URL, not base64 data. Cannot upload URL to eBay.")
            return None
    
    # Determine content type from mime_type or default (for contentType attribute)
    content_type = "image/jpeg"  # Default
    if mime_type:
        content_type = mime_type
    elif image_data:
        # Try to detect from data if it's a data URI (shouldn't happen at this point, but just in case)
        pass
    
    # Clean and validate base64 data before sending
    # Remove any whitespace, newlines, or invalid characters
    print("📤 Preparing image data for upload...")
    print(f"📊 Original base64 length: {len(image_data)} characters")
    
    # Clean the base64 data - remove whitespace and newlines
    image_data_cleaned = image_data.strip().replace('\n', '').replace('\r', '').replace(' ', '').replace('\t', '')
    
    print(f"📊 Cleaned base64 length: {len(image_data_cleaned)} characters")
    
    # Decode base64 to binary for multipart upload
    try:
        # Decode base64 to binary image data
        image_bytes = base64.b64decode(image_data_cleaned, validate=True)
        print(f"✅ Base64 data decoded ({len(image_data_cleaned)} chars -> {len(image_bytes)} bytes)")
    except Exception as e:
        print(f"❌ Invalid base64 data: {e}")
        print(f"💡 First 100 chars of base64: {image_data_cleaned[:100]}...")
        return None
    
    # Determine file extension and filename from mime type
    if 'jpeg' in content_type or 'jpg' in content_type:
        file_ext = '.jpg'
    elif 'png' in content_type:
        file_ext = '.png'
    elif 'webp' in content_type:
        file_ext = '.webp'
    else:
        file_ext = '.jpg'  # Default
    
    # Create a safe filename from picture_name
    safe_filename = "".join(c for c in picture_name if c.isalnum() or c in (' ', '-', '_')).strip()
    if not safe_filename:
        safe_filename = "uploaded_image"
    safe_filename = safe_filename.replace(' ', '_') + file_ext
    
    # Construct XML request payload WITHOUT PictureData field
    # According to eBay API docs, when using binary attachment, PictureData should not be in XML
    xml_payload = f"""<?xml version="1.0" encoding="utf-8"?>
<UploadSiteHostedPicturesRequest xmlns="urn:ebay:apis:eBLBaseComponents">
    <RequesterCredentials>
        <eBayAuthToken>{valid_token}</eBayAuthToken>
    </RequesterCredentials>
    <PictureName><![CDATA[{picture_name}]]></PictureName>
    <PictureSet>Standard</PictureSet>
</UploadSiteHostedPicturesRequest>"""
    
    # Set headers for eBay Trading API
    # Note: Content-Type will be set by requests library for multipart/form-data
    headers = {
        "X-EBAY-API-SITEID": "0",  # US Production
        "X-EBAY-API-COMPATIBILITY-LEVEL": "967",
        "X-EBAY-API-CALL-NAME": "UploadSiteHostedPictures",
        "X-EBAY-API-RESPONSE-ENCODING": "XML"
    }
    
    # eBay API endpoint
    url = "https://api.ebay.com/ws/api.dll"
    
    try:
        print(f"📤 Uploading image to eBay Picture Services...")
        print(f"📝 Picture name: {picture_name}")
        print(f"📦 Using multipart/form-data with binary attachment ({len(image_bytes)} bytes)")
        
        # Manually construct multipart/form-data to match eBay API documentation format exactly
        # According to eBay docs example:
        # - First part: name="XML Payload" with XML content (text/xml; charset=utf-8)
        # - Second part: name=picture_name with filename and binary data (content_type)
        import uuid
        
        # Generate a unique boundary
        boundary = f"----FormBoundary{uuid.uuid4().hex[:16]}"
        
        # Build multipart body
        body_parts = []
        
        # First part: XML Payload
        body_parts.append(f"--{boundary}\r\n".encode('utf-8'))
        body_parts.append(f'Content-Disposition: form-data; name="XML Payload"\r\n'.encode('utf-8'))
        body_parts.append(f'\r\n'.encode('utf-8'))
        body_parts.append(xml_payload.encode('utf-8'))
        body_parts.append(f'\r\n'.encode('utf-8'))
        
        # Second part: Binary image
        # Escape quotes in picture_name for Content-Disposition header
        escaped_picture_name = picture_name.replace('"', '\\"')
        escaped_filename = safe_filename.replace('"', '\\"')
        
        body_parts.append(f"--{boundary}\r\n".encode('utf-8'))
        body_parts.append(f'Content-Disposition: form-data; name="{escaped_picture_name}"; filename="{escaped_filename}"\r\n'.encode('utf-8'))
        body_parts.append(f'Content-Type: {content_type}\r\n'.encode('utf-8'))
        body_parts.append(f'\r\n'.encode('utf-8'))
        body_parts.append(image_bytes)
        body_parts.append(f'\r\n'.encode('utf-8'))
        
        # Closing boundary
        body_parts.append(f"--{boundary}--\r\n".encode('utf-8'))
        
        # Combine all parts
        multipart_body = b''.join(body_parts)
        
        # Update headers with multipart content type
        headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'
        
        response = requests.post(url, data=multipart_body, headers=headers, timeout=60)
        
        if response.status_code != 200:
            print(f"❌ HTTP Error {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None
        
        # Check if response is valid XML before parsing
        response_text = response.text.strip()
        
        # Check if response starts with XML declaration or <
        if not response_text.startswith('<?xml') and not response_text.startswith('<'):
            # Response is not XML - likely an error message
            print(f"❌ eBay API returned non-XML error response:")
            print(f"Response: {response_text}")
            
            # Try to extract error information from the error message
            if "ErrorId=" in response_text:
                # Parse error message format: ErrorId=9003&ErrorMessage=...
                import urllib.parse
                try:
                    # Extract the error part after "Error from PES, "
                    if "Error from PES" in response_text:
                        error_part = response_text.split("Error from PES, ")[-1]
                        # Parse as query string
                        error_params = urllib.parse.parse_qs(error_part)
                        error_id = error_params.get('ErrorId', ['Unknown'])[0]
                        error_msg = error_params.get('ErrorMessage', ['Unknown error'])[0]
                        print(f"Error ID: {error_id}")
                        print(f"Error Message: {error_msg}")
                    else:
                        print(f"Full error: {response_text}")
                except:
                    print(f"Full error: {response_text}")
            
            return None
        
        # Parse XML response
        try:
            root = ET.fromstring(response.content)
            
            # Check for errors
            ack = root.find(".//{urn:ebay:apis:eBLBaseComponents}Ack")
            if ack is not None and ack.text != "Success":
                print(f"❌ eBay API returned error: {ack.text}")
                
                # Try to extract error message
                errors = root.findall(".//{urn:ebay:apis:eBLBaseComponents}Errors")
                for error in errors:
                    short_message = error.find(".//{urn:ebay:apis:eBLBaseComponents}ShortMessage")
                    long_message = error.find(".//{urn:ebay:apis:eBLBaseComponents}LongMessage")
                    error_code = error.find(".//{urn:ebay:apis:eBLBaseComponents}ErrorCode")
                    
                    if short_message is not None:
                        print(f"Error: {short_message.text}")
                    if long_message is not None:
                        print(f"Details: {long_message.text}")
                    if error_code is not None:
                        print(f"Error Code: {error_code.text}")
                
                return None
            
            # Extract FullURL from SiteHostedPictureDetails
            full_url_elem = root.find(".//{urn:ebay:apis:eBLBaseComponents}FullURL")
            
            if full_url_elem is not None and full_url_elem.text:
                image_url = full_url_elem.text
                print(f"✅ Image uploaded successfully!")
                print(f"🔗 Image URL: {image_url}")
                return image_url
            else:
                print("❌ Could not find FullURL in response")
                print(f"Response XML: {response.text[:1000]}")
                return None
                
        except ET.ParseError as e:
            print(f"❌ Error parsing XML response: {e}")
            print(f"Response: {response.text[:500]}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error calling eBay API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text[:500]}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return None

