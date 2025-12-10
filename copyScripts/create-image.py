"""
Create Image Module

This module contains functions for generating images using OpenRouter's Gemini 2.5 Flash Image API.
"""

import os
import json
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
    
    Args:
        image_urls (list[str]): Array of image URLs to use as input
        image_type (ImageType): Enum value indicating PROFESSIONAL or REAL_WORLD
    
    Returns:
        str: Path to the saved generated image file, or None on failure
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
        
        # Parse response to extract generated image URL
        # The response format may vary, but typically contains image data or URL
        if 'choices' in result and len(result['choices']) > 0:
            message_content = result['choices'][0].get('message', {}).get('content', '')
            
            # Check if content is a string (might be JSON string or direct URL)
            if isinstance(message_content, str):
                # Try to parse as JSON first
                try:
                    content_json = json.loads(message_content)
                    # Look for image URL in various possible formats
                    image_url = None
                    if isinstance(content_json, dict):
                        image_url = content_json.get('url') or content_json.get('image_url') or content_json.get('imageUrl')
                    if not image_url and message_content.startswith('http'):
                        image_url = message_content.strip()
                except json.JSONDecodeError:
                    # If not JSON, check if it's a direct URL
                    if message_content.startswith('http'):
                        image_url = message_content.strip()
                    else:
                        print(f"❌ Unexpected response format. Content: {message_content[:200]}")
                        return None
            elif isinstance(message_content, dict):
                image_url = message_content.get('url') or message_content.get('image_url') or message_content.get('imageUrl')
            else:
                print(f"❌ Unexpected response content type: {type(message_content)}")
                return None
            
            if not image_url:
                # Check if there's an image in the response directly
                if 'image' in result:
                    image_url = result['image']
                elif 'data' in result and len(result['data']) > 0:
                    image_url = result['data'][0].get('url')
                else:
                    print(f"❌ Could not find image URL in response. Full response: {json.dumps(result, indent=2)[:500]}")
                    return None
            
            print(f"✅ Received image URL from OpenRouter: {image_url[:100]}...")
            
            # Download the generated image
            try:
                print("📥 Downloading generated image...")
                img_response = requests.get(image_url, timeout=30)
                img_response.raise_for_status()
                
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
                
                # Create output directory if it doesn't exist
                output_dir = Path("generated-images")
                output_dir.mkdir(exist_ok=True)
                
                # Generate filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"generated_{image_type.value.lower()}_{timestamp}{ext}"
                file_path = output_dir / filename
                
                # Save the image
                with open(file_path, 'wb') as f:
                    f.write(img_response.content)
                
                print(f"✅ Image saved to: {file_path}")
                return str(file_path)
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Error downloading image: {e}")
                return None
            except Exception as e:
                print(f"❌ Error saving image: {e}")
                return None
        else:
            print("❌ Unexpected response format from OpenRouter")
            print(f"Response: {json.dumps(result, indent=2)[:500]}")
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

