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

from config import CONFIDENCE_THRESHOLD, IMAGENET_LABEL_TO_CATEGORY, MODEL_BACKENDS

logger = logging.getLogger(__name__)

DEV_TODO = "[DEV Agent TODO — BMAD Phase 4]"


class BackendUnavailable(Exception):
    """Raised when a backend cannot serve (unknown name, TF missing, load fail)."""


class PredictFailed(Exception):
    """Stable predict-stage failure (AD-7): cli converts to unsorted + reason."""


@dataclass(frozen=True)
class ClassificationResult:
    """Outcome of classifying a single image."""

    image_path: Path
    category: str
    confidence: float  # 0.0 - 1.0
    backend: str
    raw_label: str | None = None  # backend-native label before mapping
    reason: str | None = None  # why unsorted (low confidence / unmapped / failure)
    probabilities: tuple[float, ...] = ()  # distribution over config.CATEGORIES


class BaseClassifier(ABC):
    """Common contract for every classification backend."""

    name: str = "base"

    def __init__(self, threshold: float = CONFIDENCE_THRESHOLD) -> None:
        """*threshold* is the below-which probability that means `unsorted` (FR-A3)."""
        self.threshold = threshold

    @abstractmethod
    def load(self) -> "BaseClassifier":
        """Load weights/model into memory. Returns self for chaining."""

    @abstractmethod
    def predict(self, image_path: Path) -> ClassificationResult:
        """Classify one image file and return category + confidence."""


# --- Label mapping for the ImageNet backend ---------------------------------
# Home: `config.IMAGENET_LABEL_TO_CATEGORY` (AD-3 single source of truth).
# Re-exported here so existing `classifier.IMAGENET_LABEL_TO_CATEGORY` imports
# keep working; the table itself is declared once, in `config.py`.
IMAGENET_LABEL_TO_CATEGORY = IMAGENET_LABEL_TO_CATEGORY


class MobileNetV2Classifier(BaseClassifier):
    """Lab reference: MobileNetV2 pre-trained on ImageNet.

    Strategy: run ImageNet inference, map the top label through
    IMAGENET_LABEL_TO_CATEGORY, and fall back to "unsorted" when unmapped or
    low-confidence (the threshold is applied later, in cli.py).
    """

    name = "mobilenet"

    def __init__(
        self, weights: str = "imagenet", threshold: float = CONFIDENCE_THRESHOLD
    ) -> None:
        super().__init__(threshold=threshold)
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

    def __init__(
        self, model_path: Path | None = None, threshold: float = CONFIDENCE_THRESHOLD
    ) -> None:
        super().__init__(threshold=threshold)
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


def get_classifier(
    backend: str, threshold: float = CONFIDENCE_THRESHOLD
) -> BaseClassifier:
    """Factory validated against config.MODEL_BACKENDS (FR-A2).

    *threshold* flows into the backend so routing stays in one place (AD-10).
    Names outside the config allow-list raise BackendUnavailable, which the CLI
    maps to exit 2 instead of a traceback.
    """
    if backend not in MODEL_BACKENDS or backend not in _BACKENDS:
        raise BackendUnavailable(
            f"Unknown backend {backend!r}. Choose from: {sorted(_BACKENDS)}"
        )
    logger.debug("Selected backend: %s", backend)
    return _BACKENDS[backend](threshold=threshold)
