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
    bottom_margin=30,
    right_margin=30,
)

GROQ_IMG_CONFIG = PatchConfig(
    rect_width=67,
    rect_height=25,
    bottom_margin=10,
    right_margin=11,
)
