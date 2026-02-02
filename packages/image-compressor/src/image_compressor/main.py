"""
Image Compressor Utility

This script scans the user's Downloads folder for PNG, JPG, and JPEG images.
It compresses them to a target size of approximately 200 KB, saving them as
new JPG files with a unique name. If an image's name contains "Gemini", a
special patch is applied before compression. The original file is deleted
upon successful compression.

----------------
HOW TO USE:
----------------
1. Make sure the virtual environment is active:
   source .venv/bin/activate

2. Run the script from the project's root directory:
   python -m image_compressor.main
"""
import os
import uuid
from pathlib import Path
from PIL import Image
import io
import re

from .patch import apply_smart_patch
from .advanced_patch import apply_advanced_patch
from .dl_patch import apply_dl_patch
from .config import PatchConfig, GEMINI_IMG_CONFIG, GROQ_IMG_CONFIG
from .blending import apply_seamless_blending

# --- Configuration ---
TARGET_SIZE_KB = 200
DOWNLOADS_DIR = Path.home() / "Downloads"
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg"}

PATCH_CONFIGS = [
    {
        "name": "gemini_patch",
        "pattern": re.compile(r"Gemini"),
        "function": apply_dl_patch,
        "config": GEMINI_IMG_CONFIG,
    },
    {
        "name": "groq_patch",
        "pattern": re.compile(r"TEMPORARY DISABLED AABBEERR^image(\s\(\d+\))?\.jpg$"),
        "function": apply_dl_patch,
        "config": GROQ_IMG_CONFIG,
    },
]
# ---------------------

def compress_and_save(image: Image.Image, output_path: Path, target_bytes: int):
    """
    Iteratively compresses a PIL image to be under a target size.
    Saves the image to the specified output path.
    """
    # Handle PNG transparency by converting to RGB
    if image.mode == 'RGBA':
        image = image.convert('RGB')

    # Iteratively reduce quality to meet target size
    quality = 95
    while quality > 10:
        # Save to an in-memory buffer to check size before writing to disk
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
        size_bytes = buffer.tell()

        if size_bytes <= target_bytes:
            # Found a good quality setting, write the buffer to the file
            with open(output_path, "wb") as f:
                f.write(buffer.getvalue())
            return True, size_bytes

        quality -= 5 # Decrease quality and try again

    return False, 0 # Could not meet the target size

def process_images():
    """Main function to scan and process images."""
    if not DOWNLOADS_DIR.exists():
        print(f"Error: Downloads directory not found at '{DOWNLOADS_DIR}'")
        return

    print(f"Scanning '{DOWNLOADS_DIR}' for images...")
    target_bytes = TARGET_SIZE_KB * 1024
    processed_count = 0
    
    for file_path in DOWNLOADS_DIR.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            print(f"\nProcessing '{file_path.name}'...")
            try:
                with Image.open(file_path) as img:
                    patched = False
                    for patch_config in PATCH_CONFIGS:
                        if patch_config["pattern"].search(file_path.name):
                            print(f"  -> '{patch_config['name']}' detected. Applying inpainting...")
                            inpainted_img = patch_config["function"](img, patch_config["config"])
                            print("  -> Applying edge blending...")
                            original_img = img.copy()
                            img = apply_seamless_blending(original_img, inpainted_img, patch_config["config"])
                            patched = True
                            break # Stop after first match

                    new_filename = f"{uuid.uuid4().hex[:8]}.jpg"
                    output_path = file_path.parent / new_filename

                    success, final_size_bytes = compress_and_save(img, output_path, target_bytes)

                    if success:
                        print(f"  -> Compressed to '{output_path.name}' ({final_size_bytes / 1024:.1f} KB)")
                        # On successful creation, delete the original file
                        file_path.unlink()
                        print(f"  -> Deleted original: '{file_path.name}'")
                        processed_count += 1
                    else:
                        print(f"  -> Failed: Could not compress '{file_path.name}' to under {TARGET_SIZE_KB} KB.")

            except Exception as e:
                print(f"  -> Error processing '{file_path.name}': {e}")

    print(f"\nFinished. Processed {processed_count} images.")

if __name__ == "__main__":
    process_images()
