from dataclasses import dataclass

@dataclass
class PatchConfig:
    """Dataclass to hold inpainting configurations."""
    rect_width: int
    rect_height: int
    bottom_margin: int
    right_margin: int

GEMINI_IMG_CONFIG = PatchConfig(
    rect_width=52,
    rect_height=52,
    # bottom_margin=30,
    # right_margin=30,
    bottom_margin=94,
    right_margin=94,
)
# 672 bottom
# 768 end
# 1312 right
# 1408 end


GROQ_IMG_CONFIG = PatchConfig(
    rect_width=67,
    rect_height=25,
    bottom_margin=10,
    right_margin=11,
)

