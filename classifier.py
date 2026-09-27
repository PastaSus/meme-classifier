"""Classification backends for the Meme & Reaction Image Organizer (FR-A2, FR-A3).

Two backends from the lab reference sheet share one ABC contract:

* ``mobilenet``    — MobileNetV2 pre-trained on ImageNet + label->category
                     mapping (zero-shot default, needs no training data).
* ``custom-cnn``   — hand-built CNN (Conv2D -> MaxPooling2D -> Flatten ->
                     Dense, categorical cross-entropy) trained on labelled
                     folders.

Implementation bodies are intentionally left to the Dev Agent (BMAD Phase 4)
and raise NotImplementedError with an explicit marker.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

DEV_TODO = "[DEV Agent TODO — BMAD Phase 4]"


@dataclass(frozen=True)
class ClassificationResult:
    """Outcome of classifying a single image."""

    image_path: Path
    category: str
    confidence: float  # 0.0 - 1.0
    backend: str
    raw_label: str | None = None  # backend-native label before mapping


class BaseClassifier(ABC):
    """Common contract for every classification backend."""

    name: str = "base"

    @abstractmethod
    def load(self) -> "BaseClassifier":
        """Load weights/model into memory. Returns self for chaining."""

    @abstractmethod
    def predict(self, image_path: Path) -> ClassificationResult:
        """Classify one image file and return category + confidence."""


# --- Label mapping for the ImageNet backend ---------------------------------
# ImageNet class name (lowercase) -> project category (kebab-case, FR-A2).
# Extend this table during the Dev phase; unmapped labels below still route to
# "unsorted" via the confidence threshold in cli.py (FR-A3).
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


class MobileNetV2Classifier(BaseClassifier):
    """Lab reference: MobileNetV2 pre-trained on ImageNet.

    Strategy: run ImageNet inference, map the top label through
    IMAGENET_LABEL_TO_CATEGORY, and fall back to "unsorted" when unmapped or
    low-confidence (the threshold is applied later, in cli.py).
    """

    name = "mobilenet"

    def __init__(self, weights: str = "imagenet") -> None:
        self.weights = weights
        self._model = None
        self._decode = None

    def load(self) -> "MobileNetV2Classifier":
        # TODO(Dev Agent): tf.keras.applications.MobileNetV2(weights=self.weights)
        #                   + tf.keras.applications.mobilenet_v2.preprocess_input
        #                   + decode_predictions helper.
        raise NotImplementedError(
            f"{DEV_TODO} Load MobileNetV2 in MobileNetV2Classifier.load(). "
            "See docs/system-architecture.md section 2.3."
        )

    def predict(self, image_path: Path) -> ClassificationResult:
        # TODO(Dev Agent): preprocess image -> model.predict -> decode top-1 label
        #                   -> map via IMAGENET_LABEL_TO_CATEGORY -> confidence.
        raise NotImplementedError(
            f"{DEV_TODO} Implement inference in MobileNetV2Classifier.predict()."
        )


class CustomCNNClassifier(BaseClassifier):
    """Lab reference: custom CNN built with TensorFlow/Keras.

    Architecture (per lab sheet): Conv2D -> MaxPooling2D -> Flatten -> Dense,
    trained with categorical cross-entropy on labelled category folders.
    """

    name = "custom-cnn"

    def __init__(self, model_path: Path | None = None) -> None:
        self.model_path = model_path
        self._model = None

    def load(self) -> "CustomCNNClassifier":
        # TODO(Dev Agent): build/compile the CNN (or load a saved model from
        #                   self.model_path) with categorical cross-entropy.
        raise NotImplementedError(
            f"{DEV_TODO} Build the CNN in CustomCNNClassifier.load(). "
            "See docs/system-architecture.md section 2.3."
        )

    def predict(self, image_path: Path) -> ClassificationResult:
        # TODO(Dev Agent): resize/normalize image -> model.predict ->
        #                   argmax over class indices -> category + confidence.
        raise NotImplementedError(
            f"{DEV_TODO} Implement inference in CustomCNNClassifier.predict()."
        )


_BACKENDS: dict[str, type[BaseClassifier]] = {
    MobileNetV2Classifier.name: MobileNetV2Classifier,
    CustomCNNClassifier.name: CustomCNNClassifier,
}


def get_classifier(backend: str) -> BaseClassifier:
    """Factory validated against config.MODEL_BACKENDS (FR-A2)."""
    try:
        cls = _BACKENDS[backend]
    except KeyError:
        raise ValueError(
            f"Unknown backend {backend!r}. Choose from: {sorted(_BACKENDS)}"
        ) from None
    logger.debug("Selected backend: %s", backend)
    return cls()
