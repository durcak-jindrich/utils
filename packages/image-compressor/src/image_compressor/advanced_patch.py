"""
Advanced Image Patching Utility using a patch-based algorithm.
"""
import numpy as np
from PIL import Image
from patch_based_inpainting import Inpaint

from .config import PatchConfig

def apply_advanced_patch(image: Image.Image, config: PatchConfig) -> Image.Image:
    """
    Applies a patch-based inpainting algorithm, which is often better for
    recreating textures than diffusion-based methods like cv2.inpaint.

    Args:
        image: A PIL.Image object.
        config: A PatchConfig object with the patch dimensions.

    Returns:
        A new PIL.Image object with the patch applied.
    """
    # --- 1. Convert PIL Image to NumPy array ---
    image_np = np.array(image.convert('RGB'))

    # --- 2. Define the Rectangle to Patch and Create Mask ---
    height, width, _ = image_np.shape
    rect_width = config.rect_width
    rect_height = config.rect_height
    bottom_margin = config.bottom_margin
    right_margin = config.right_margin

    x1 = width - right_margin - rect_width
    y1 = height - bottom_margin - rect_height
    x2 = width - right_margin
    y2 = height - bottom_margin

    # The library expects a uint8 mask where non-zero values indicate the hole.
    mask = np.zeros((height, width), dtype=np.uint8)
    mask[y1:y2, x1:x2] = 255

    # --- 3. Apply the Patch-Based Inpainting Algorithm ---
    # The `patch_size` is a crucial parameter. It should be an odd number,
    # and its size should be similar to or slightly larger than the
    # texture elements you want to replicate. We start with 9.
    inpainter = Inpaint(
        image=image_np,
        mask=mask,
        patch_size=25,
        overlap_size=9,
        method='gaussian' # Use Gaussian weighting for smoother patch transitions
    )

    # Perform the inpainting.
    inpainted_image_np = inpainter.resolve()

    # --- 4. Convert Back to PIL Image ---
    final_image = Image.fromarray(inpainted_image_np)

    return final_image
