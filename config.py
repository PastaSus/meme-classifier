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
