"""
Image editing utilities.

Provides functions for image manipulation such as background removal
and canvas-based image composition.
"""

import io
import base64

from rembg import remove
from PIL import Image


def remove_background(image_bytes: bytes) -> bytes:
    """
    Remove the background from an image.

    Args:
        image_bytes (bytes): Binary image data (PNG, JPG, etc.)

    Returns:
        bytes: PNG image data with background removed (transparent).
    """
    output = remove(image_bytes)
    return output


def compile_images(layers: list, canvas_width: int = 1080, canvas_height: int = 1080, bg_color: str = "#FFFFFF") -> bytes:
    """
    Compile multiple images onto a single canvas with transform support.

    Args:
        layers (list): List of layer dicts, each containing:
            - image_base64 (str): Base64-encoded image data
            - left (float): X position on canvas
            - top (float): Y position on canvas
            - scaleX (float): Horizontal scale factor
            - scaleY (float): Vertical scale factor
            - angle (float): Rotation angle in degrees
        canvas_width (int): Width of the output canvas in pixels
        canvas_height (int): Height of the output canvas in pixels
        bg_color (str): Background color as hex string (e.g. "#FFFFFF")

    Returns:
        bytes: PNG image data of the composed canvas.
    """
    # Create the canvas with the background color
    canvas = Image.new("RGBA", (canvas_width, canvas_height), bg_color)

    for layer in layers:
        image_base64 = layer.get("image_base64", "")
        left = layer.get("left", 0)
        top = layer.get("top", 0)
        scale_x = layer.get("scaleX", 1)
        scale_y = layer.get("scaleY", 1)
        angle = layer.get("angle", 0)

        # Decode the base64 image
        image_data = base64.b64decode(image_base64)
        img = Image.open(io.BytesIO(image_data)).convert("RGBA")

        # Apply scaling
        new_width = max(1, int(img.width * scale_x))
        new_height = max(1, int(img.height * scale_y))
        img = img.resize((new_width, new_height), Image.LANCZOS)

        # Apply rotation (expand=True to avoid clipping)
        if angle != 0:
            img = img.rotate(-angle, resample=Image.BICUBIC, expand=True)

        # Paste onto canvas using alpha compositing
        # Calculate integer position
        paste_x = int(left)
        paste_y = int(top)

        # Create a temporary canvas to handle the paste with alpha
        temp = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        temp.paste(img, (paste_x, paste_y))
        canvas = Image.alpha_composite(canvas, temp)

    # Convert to bytes
    output = io.BytesIO()
    canvas.save(output, format="PNG")
    return output.getvalue()
