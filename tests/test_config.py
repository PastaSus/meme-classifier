"""Unit tests for the config single source of truth (AD-3, Story 1.2).

TF-free: asserts the exact category/extension sets from PRD section 2.2/FR-A1
and the key defaults later stories import (threshold, backends, paths, floors,
mapping structure). Catches drift before Story 1.3/1.4 build on these values.
"""
from __future__ import annotations

from config import (
    ACCURACY_FLOOR,
    CATEGORIES,
    CONFIDENCE_THRESHOLD,
    DEFAULT_BACKEND,
    DEFAULT_FIXTURE_DIR,
    DEFAULT_MODEL_PATH,
    DEFAULT_OUTPUT_DIR,
    IMAGE_EXTENSIONS,
    IMAGENET_LABEL_TO_CATEGORY,
    MODEL_BACKENDS,
    UNSORTED_SHARE_FLOOR,
)


class TestConfigAuthority:
    def test_categories_match_prd(self) -> None:
        assert CATEGORIES == (
            "gym-memes",
            "cat-memes",
            "chaotic-screenshots",
            "wholesome-posts",
            "unsorted",
        )

    def test_image_extensions_match_prd(self) -> None:
        assert IMAGE_EXTENSIONS == frozenset(
            {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
        )

    def test_threshold_and_backends(self) -> None:
        assert CONFIDENCE_THRESHOLD == 0.45
        assert MODEL_BACKENDS == ("mobilenet", "custom-cnn")
        assert DEFAULT_BACKEND == "mobilenet"

    def test_paths_have_single_home(self) -> None:
        assert DEFAULT_OUTPUT_DIR.name == "organized"
        assert DEFAULT_MODEL_PATH.name == "custom-cnn.keras"
        assert DEFAULT_FIXTURE_DIR.name == "labeled"

    def test_floors_are_oq1_first_pass(self) -> None:
        assert ACCURACY_FLOOR == 0.6
        assert UNSORTED_SHARE_FLOOR == 0.8

    def test_mapping_covers_categories(self) -> None:
        assert set(IMAGENET_LABEL_TO_CATEGORY.values()) <= set(CATEGORIES)
        assert "unsorted" not in set(IMAGENET_LABEL_TO_CATEGORY.values())
        assert IMAGENET_LABEL_TO_CATEGORY["barbell"] == "gym-memes"
        assert IMAGENET_LABEL_TO_CATEGORY["tabby"] == "cat-memes"

    def test_classifier_reexports_same_mapping(self) -> None:
        from classifier import IMAGENET_LABEL_TO_CATEGORY as reexported

        assert reexported is IMAGENET_LABEL_TO_CATEGORY