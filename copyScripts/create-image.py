"""
Create Image Module

This module contains functions for generating images using OpenRouter's Gemini 2.5 Flash Image API.
"""

import os
import json
import base64
import requests
from enum import Enum
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


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

