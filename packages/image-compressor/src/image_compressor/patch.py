"""
Image Patching Utility using OpenCV.
"""
import cv2
import numpy as np
from PIL import Image

from .config import PatchConfig

def apply_smart_patch(image: Image.Image, config: PatchConfig) -> Image.Image:
    """
    Applies an inpainting algorithm ("smart patch") to a specified rectangular
    area of an image.

    This function is designed to handle various image sizes and formats by
    defining the patch area relative to the bottom-right corner.

    Args:
        image: A PIL.Image object.
        config: A PatchConfig object with the patch dimensions.

    Returns:
        A new PIL.Image object with the patch applied.
    """
    # --- 1. Convert PIL Image to OpenCV format (NumPy array) ---
    # The function is format-agnostic (JPG, PNG, etc.) because it works on
    # the raw pixel data after the image is opened. The original compression
    # script already handles converting RGBA (PNG with transparency) to RGB.
    open_cv_image = np.array(image.convert('RGB'))
    # OpenCV's default color order is BGR, so we convert from RGB.
    open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)

    # --- 2. Define the Rectangle to Patch ---
    # The coordinates are calculated relative to the image's dimensions,
    # making this logic work correctly for any image size (e.g., 1024x1024
    # or 1408x768).
    height, width, _ = open_cv_image.shape
    rect_width = config.rect_width
    rect_height = config.rect_height
    bottom_margin = config.bottom_margin
    right_margin = config.right_margin

    # Calculate the top-left (x1, y1) and bottom-right (x2, y2) corners
    # of the rectangle.
    x1 = width - right_margin - rect_width
    y1 = height - bottom_margin - rect_height
    x2 = width - right_margin
    y2 = height - bottom_margin

    # --- 3. Create the Mask ---
    # The mask is a black image with a white shape indicating the area to be
    # filled. A rectangle is the most straightforward and common shape.
    # While other shapes (like circles or polygons) are possible, a rectangle
    # is perfectly sufficient for the inpainting algorithm. The quality of
    # the result depends more on the pixels *surrounding* the mask than the
    # mask's specific shape.
    mask = np.zeros((height, width), dtype=np.uint8)
    mask[y1:y2, x1:x2] = 255

    # --- 4. Apply the Inpainting Algorithm ---
    # cv2.inpaint takes the source image, the mask, a radius for the
    # neighborhood to consider, and the algorithm flag.
    # - cv2.INPAINT_TELEA: Generally fast and effective.
    # - cv2.INPAINT_NS: Can be slower but may produce different results.
    inpainted_image = cv2.inpaint(open_cv_image, mask, inpaintRadius=3, flags=cv2.INPAINT_NS)

    # --- 5. Convert Back to PIL Image ---
    # Convert from BGR back to RGB and then create a PIL Image object.
    inpainted_image_rgb = cv2.cvtColor(inpainted_image, cv2.COLOR_BGR2RGB)
    final_image = Image.fromarray(inpainted_image_rgb)

    return final_image
