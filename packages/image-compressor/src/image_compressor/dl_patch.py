import torch
from PIL import Image
import math
from diffusers import StableDiffusionInpaintPipeline

# --- Model Configuration ---
_pipeline = None


def _get_crop_box(x1, y1, x2, y2, img_width, img_height, crop_size=512):
    """Calculates a centered crop box of crop_size, ensuring it stays within image bounds."""
    center_x = (x1 + x2) // 2
    center_y = (y1 + y2) // 2

    # Calculate initial crop box, centered on the mask
    crop_x1 = center_x - crop_size // 2
    crop_y1 = center_y - crop_size // 2
    crop_x2 = crop_x1 + crop_size
    crop_y2 = crop_y1 + crop_size

    # Adjust box to stay within image boundaries
    if crop_x1 < 0:
        crop_x2 -= crop_x1
        crop_x1 = 0
    if crop_y1 < 0:
        crop_y2 -= crop_y1
        crop_y1 = 0
    if crop_x2 > img_width:
        crop_x1 -= (crop_x2 - img_width)
        crop_x2 = img_width
    if crop_y2 > img_height:
        crop_y1 -= (crop_y2 - img_height)
        crop_y2 = img_height

    return (int(crop_x1), int(crop_y1), int(crop_x2), int(crop_y2))


def _load_pipeline():
    """Loads the Stable Diffusion Inpaint model pipeline, keeping it in memory."""
    global _pipeline
    if _pipeline is None:
        if torch.backends.mps.is_available():
            device = "mps"
        elif torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"

        print(f"Loading Stable Diffusion Inpainting model ('runwayml/stable-diffusion-inpainting')...")
        print("This is a one-time download and may take several minutes.")
        try:
            pipeline_cpu = StableDiffusionInpaintPipeline.from_pretrained(
                "runwayml/stable-diffusion-inpainting",
                torch_dtype=torch.float16 if device == "mps" else torch.float32
            )
            print(f"Moving model to '{device}' device...")
            _pipeline = pipeline_cpu.to(device)
            print("Model loaded successfully.")
        except Exception as e:
            print(f"--- FATAL ERROR ---")
            print(f"Failed to load the model. This could be due to:")
            print(f"1. No internet connection or a firewall blocking downloads.")
            print(f"2. Insufficient RAM. 16GB is recommended, but might fail if other memory-intensive applications are running.")
            print(f"3. A corrupted cache. Try clearing it at ~/.cache/huggingface/hub/")
            print(f"\nOriginal Error: {e}")
            _pipeline = None
            raise e
    return _pipeline


from .config import PatchConfig

def apply_dl_patch(image: Image.Image, config: PatchConfig) -> Image.Image:
    """
    Applies Stable Diffusion inpainting on a cropped 512x512 region to preserve
    the original image resolution, then pastes only the repaired patch back.
    """
    pipeline = _load_pipeline()
    image = image.convert("RGB")

    # 1. Define mask region
    height, width = image.height, image.width
    rect_width, rect_height = config.rect_width, config.rect_height
    bottom_margin, right_margin = config.bottom_margin, config.right_margin
    x1 = width - right_margin - rect_width
    y1 = height - bottom_margin - rect_height
    x2 = width - right_margin
    y2 = height - bottom_margin

    # 2. Create a 512x512 crop box for optimal model performance
    crop_box = _get_crop_box(x1, y1, x2, y2, width, height, crop_size=512)
    image_crop = image.crop(crop_box)

    # 3. Create a mask for the cropped area
    full_mask = Image.new("L", (width, height), 0)
    for x in range(x1, x2):
        for y in range(y1, y2):
            full_mask.putpixel((x, y), 255)
    mask_crop = full_mask.crop(crop_box)

    # 4. Run Inference on the 512x512 crop
    prompt = ""  # Empty prompt for context-aware fill
    with torch.no_grad():
        inpainted_crop = pipeline(
            prompt=prompt,
            image=image_crop,
            mask_image=mask_crop
        ).images[0]

    # 5. Extract only the repaired 48x48 patch and paste it back
    local_x1 = x1 - crop_box[0]
    local_y1 = y1 - crop_box[1]
    local_x2 = local_x1 + rect_width
    local_y2 = local_y1 + rect_height
    repaired_patch = inpainted_crop.crop((local_x1, local_y1, local_x2, local_y2))

    final_image = image.copy()
    final_image.paste(repaired_patch, (x1, y1))

    return final_image
