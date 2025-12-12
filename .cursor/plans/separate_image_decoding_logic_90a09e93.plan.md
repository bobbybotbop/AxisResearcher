---
name: Separate image decoding logic
overview: Refactor image generation to save API responses as JSON files, extract decoding logic into a separate function, and add a new "decode" command to decode images from stored JSON responses.
todos:
  - id: create_enum
    content: Create ImageType enum with PROFESSIONAL and REAL_WORLD values
    status: completed
  - id: create_main_function
    content: Implement generate_image_from_urls() function with API key loading, prompt file loading, and OpenRouter API call
    status: completed
  - id: handle_image_response
    content: Parse API response, download generated image, save to file, and return file path
    status: completed
  - id: add_error_handling
    content: Add comprehensive error handling for API key, prompt files, API requests, and file operations
    status: completed
---

# Separate Image Decoding Logic

## Overview

Refactor the image generation workflow to:

1. Store API responses as JSON files in an "api-responses" directory
2. Extract image decoding logic into a separate reusable function
3. Add a new "decode" command to decode images from stored JSON files

## Changes

### 1. Modify `generate_image_from_urls` in `copyScripts/create-image.py`

- Save the full API response JSON to a file in `api-responses/` directory
- Remove image decoding/saving logic (keep only API call and JSON storage)
- Return the path to the saved JSON file instead of the image file
- Use timestamp-based filename: `response_<image_type>_<timestamp>.json`

### 2. Create `decode_image_from_response` function in `copyScripts/create-image.py`

- Accept a JSON file path as parameter
- Read and parse the JSON file
- Extract image data using the existing parsing logic (handles `inline_data`, `image_url`, etc.)
- Decode base64 data and save image to `generated-images/` directory
- Return the path to the saved image file, or None on failure
- Handle errors gracefully with clear error messages

### 3. Add "decode" command in `main_ebay_commands.py`

- Add new `elif command == "decode":` block after the "image" command
- Accept JSON file path as argument: `decode <json_file_path>`
- Import and call `decode_image_from_response` from the create-image module
- Print success message with image path, or error message on failure
- Update help text to include: `decode <json_file>`

### 4. Update help text

- Add "decode" command to all help messages in `main_ebay_commands.py`
- Update command list in the else clause and usage message

## File Structure

```
api-responses/
  └── response_PROFESSIONAL_20240101_120000.json
  └── response_REAL_WORLD_20240101_120100.json

generated-images/
  └── generated_professional_20240101_120000.png
  └── generated_real_world_20240101_120100.png
```

## Workflow

1. User runs: `image <url> <type>` → Saves JSON response to `api-responses/`
2. User runs: `decode <json_file>` → Reads JSON, decodes image, saves to `generated-images/`