"""Generate the labelled AC-A6 fixture: 10 Pillow images, 2 per category.

Outputs under ``tests/fixtures/labeled/<category>/`` (committed to the repo).
Pillow lives only here and in tests (AD-4 amendment); production code stays
stdlib-only. Idempotent — re-running overwrites the same 10 files.

Usage:
    uv run python tests/fixtures/make_labeled.py
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import CATEGORIES  # noqa: E402

FIXTURE_ROOT = PROJECT_ROOT / "tests" / "fixtures" / "labeled"

# Distinct solid colour per category so a human can eyeball the tree.
CATEGORY_COLOURS: dict[str, tuple[int, int, int]] = {
    "gym-memes": (200, 40, 40),
    "cat-memes": (40, 140, 240),
    "chaotic-screenshots": (120, 40, 180),
    "wholesome-posts": (40, 180, 90),
    "unsorted": (130, 130, 130),
}

IMAGES_PER_CATEGORY = 2
IMAGE_SIZE = (64, 64)


def main() -> int:
    from PIL import Image

    for category in CATEGORIES:
        colour = CATEGORY_COLOURS.get(category, (200, 200, 200))
        for index in range(1, IMAGES_PER_CATEGORY + 1):
            out = FIXTURE_ROOT / category / f"{category}-{index}.jpg"
            out.parent.mkdir(parents=True, exist_ok=True)
            shade = max(0, min(255, colour[0] + (index - 1) * 15))
            fill = (shade, colour[1], colour[2])
            Image.new("RGB", IMAGE_SIZE, fill).save(out, format="JPEG")
            print(f"wrote {out.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
