"""
Image Blending Utility to soften patch edges using a two-step Poisson blend.
"""
import cv2
import numpy as np
from PIL import Image

from .config import PatchConfig

def apply_seamless_blending(original_image: Image.Image, inpainted_image: Image.Image, config: PatchConfig, blend_margin: int = 5) -> Image.Image:
    """
    Uses a two-step Poisson Blending process to eliminate boundary artifacts.
    It blends the clean inpainted patch into the context of the already
    inpainted image, avoiding contact with the original image's artifacts.

    Args:
        original_image: The original PIL image before any patching. This is
                        no longer directly used for blending but kept for
                        potential future strategies.
        inpainted_image: The PIL image with the hard-edged patch applied.
        config: The PatchConfig object used for the inpainting.
        blend_margin: A small margin to ensure the blend happens in a clean area.

    Returns:
        A new PIL.Image object with the patch area's edges seamlessly blended.
    """
    # 1. Get patch coordinates and image dimensions
    height, width = inpainted_image.height, inpainted_image.width
    x1 = width - config.right_margin - config.rect_width
    y1 = height - config.bottom_margin - config.rect_height
    x2 = width - config.right_margin
    y2 = height - config.bottom_margin

    # 2. Prepare the inpainted image for OpenCV
    # This image contains the clean patch and the clean surrounding area.
    dest_bgr = cv2.cvtColor(np.array(inpainted_image.convert('RGB')), cv2.COLOR_RGB2BGR)

    # 3. The source is also the inpainted image. We are re-blending a portion
    # of the image onto itself to fix the hard edges.
    src_bgr = dest_bgr.copy()

    # 4. Create a mask for the central part of the patch, avoiding the very edge.
    # By making the mask slightly smaller than the patch, we ensure the
    # boundary for the blend is entirely within the clean, inpainted region.
    mask = np.zeros(dest_bgr.shape[:2], dtype=np.uint8)
    mask_x1 = x1 + blend_margin
    mask_y1 = y1 + blend_margin
    mask_x2 = x2 - blend_margin
    mask_y2 = y2 - blend_margin
    
    # Ensure the mask has a valid area
    if mask_x1 < mask_x2 and mask_y1 < mask_y2:
        cv2.rectangle(mask, (mask_x1, mask_y1), (mask_x2, mask_y2), 255, -1)
    else:
        # If the patch is too small for a margin, mask the whole thing
        cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)


    # 5. Define the center for the cloning operation
    center = ((x1 + x2) // 2, (y1 + y2) // 2)

    # 6. Apply Seamless Cloning with the MIXED_CLONE method
    # MIXED_CLONE is often better for texture blending and can produce
    # a smoother result than NORMAL_CLONE in this scenario.
    blended_bgr = cv2.seamlessClone(
        src_bgr,
        dest_bgr,
        mask,
        center,
        cv2.MIXED_CLONE
    )

    # 7. Convert back to a PIL Image
    blended_rgb = cv2.cvtColor(blended_bgr, cv2.COLOR_BGR2RGB)
    final_image = Image.fromarray(blended_rgb)

    return final_image
