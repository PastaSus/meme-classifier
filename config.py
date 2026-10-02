"""Central configuration for the Meme & Reaction Image Organizer.

All tunables live here so CLI flags, tests, and future backends share one source
of truth (architecture decision AD-3).
"""
from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Default I/O locations (overridable via CLI flags) ---------------------------
DEFAULT_INPUT_DIR = BASE_DIR / "data" / "inbox"
DEFAULT_OUTPUT_DIR = BASE_DIR / "data" / "organized"

# Classification contract -----------------------------------------------------
# Kebab-case category IDs double as output subfolder names (professor's
# kebab-case folder convention). "unsorted" is the low-confidence safety net.
CATEGORIES: tuple[str, ...] = (
    "gym-memes",
    "cat-memes",
    "chaotic-screenshots",
    "wholesome-posts",
    "unsorted",
)

# Files considered for scanning (FR-A1).
IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
)

# Backends described by the lab reference sheet (FR-A2).
MODEL_BACKENDS: tuple[str, ...] = ("mobilenet", "custom-cnn")
DEFAULT_BACKEND = "mobilenet"

# Predictions below this confidence (0.0-1.0) are filed under "unsorted" (FR-A3).
CONFIDENCE_THRESHOLD = 0.45

# Collision-safety cap for duplicate filenames (FR-A5).
MAX_COLLISION_SUFFIX = 1000

# Training artifact default (AD-11): the only literal model path in the repo.
# `classifier` receives it as a constructor argument; no other module declares it.
DEFAULT_MODEL_PATH = BASE_DIR / "models" / "custom-cnn.keras"

# Labelled-fixture default for AC-A6/AC-A7 accuracy checks (AD-12).
DEFAULT_FIXTURE_DIR = BASE_DIR / "tests" / "fixtures" / "labeled"

# Placement-accuracy floors (OQ-1 first-pass values; Tech Lead calibrates later).
# AC-A6: accuracy on a labelled fixture must be >= ACCURACY_FLOOR.
# AC-A7 (counter-metric): unsorted share must be <= UNSORTED_SHARE_FLOOR.
ACCURACY_FLOOR = 0.6
UNSORTED_SHARE_FLOOR = 0.8

# --- Label mapping for the ImageNet backend -----------------------------------
# ImageNet class name (lowercase) -> project category (kebab-case, FR-A2).
# Single home for the mapping (AD-3): `classifier` imports it, never re-declares
# it; no on-disk mapping file exists. Unmapped labels route to "unsorted".
IMAGENET_LABEL_TO_CATEGORY: dict[str, str] = {
    # gym-memes
    "barbell": "gym-memes",
    "dumbbell": "gym-memes",
    # cat-memes
    "tabby": "cat-memes",
    "tiger_cat": "cat-memes",
    "persian_cat": "cat-memes",
    "siamese_cat": "cat-memes",
    "egyptian_cat": "cat-memes",
    "lynx": "cat-memes",
    # chaotic-screenshots (desktop/screen imagery — extend in Dev phase)
    "desktop_computer": "chaotic-screenshots",
    "monitor": "chaotic-screenshots",
    # wholesome-posts (warm/cozy imagery — extend in Dev phase)
    "teddy": "wholesome-posts",
    "toyshop": "wholesome-posts",
    "seashore": "wholesome-posts",
}
