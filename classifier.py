"""Classification backends for the Meme & Reaction Image Organizer (FR-A2, FR-A3).

Two backends from the lab reference sheet share one ABC contract:

* ``mobilenet``    — MobileNetV2 pre-trained on ImageNet + label->category
                     mapping (zero-shot default, needs no training data).
* ``custom-cnn``   — hand-built CNN (Conv2D -> MaxPooling2D -> Flatten ->
                     Dense, categorical cross-entropy) trained on labelled
                     folders.

``mobilenet`` is implemented (ImageNet inference + label mapping); the
``custom-cnn`` body is intentionally left to the Dev Agent (BMAD Phase 4) and
raises NotImplementedError with an explicit marker.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from config import (
    CATEGORIES,
    CONFIDENCE_THRESHOLD,
    IMAGENET_LABEL_TO_CATEGORY,
    MODEL_BACKENDS,
)

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

    def route(
        self, category: str | None, confidence: float, raw_label: str | None = None
    ) -> tuple[str, str | None]:
        """Single routing policy for every backend (AR-9, AD-10, FR-A2, FR-A3).

        Backends resolve their native label first, then pass the mapped
        category (or None when unmapped) through here. Returns
        ``(final_category, reason)``: unmapped labels route to ``unsorted``
        regardless of confidence; below-threshold confidences route to
        ``unsorted`` with a ``confidence X < Y`` reason; categories outside
        ``config.CATEGORIES`` are normalized to ``unsorted``.
        """
        if category is None:
            return "unsorted", f"unmapped label {raw_label!r}"
        if confidence < self.threshold:
            return "unsorted", f"confidence {confidence:.2f} < {self.threshold:.2f}"
        if category not in CATEGORIES:
            return "unsorted", f"unknown category {category!r}"
        return category, None


# --- Label mapping for the ImageNet backend ---------------------------------
# Home: `config.IMAGENET_LABEL_TO_CATEGORY` (AD-3 single source of truth).
# Re-exported here so existing `classifier.IMAGENET_LABEL_TO_CATEGORY` imports
# keep working; the table itself is declared once, in `config.py`.
IMAGENET_LABEL_TO_CATEGORY = IMAGENET_LABEL_TO_CATEGORY


class MobileNetV2Classifier(BaseClassifier):
    """Lab reference: MobileNetV2 pre-trained on ImageNet.

    Strategy: run ImageNet inference, map the top label through
    IMAGENET_LABEL_TO_CATEGORY, then apply the shared ``BaseClassifier.route``
    policy (unmapped/threshold/membership → "unsorted" with a reason).
    """

    name = "mobilenet"

    def __init__(
        self, weights: str = "imagenet", threshold: float = CONFIDENCE_THRESHOLD
    ) -> None:
        super().__init__(threshold=threshold)
        self.weights = weights
        self._model = None
        self._decode = None
        self._preprocess = None

    def load(self) -> "MobileNetV2Classifier":
        """Load MobileNetV2/ImageNet weights — the ONLY place that fetches (AD-8)."""
        try:
            from tensorflow import keras
        except Exception as exc:
            raise BackendUnavailable(f"TensorFlow unavailable: {exc}") from exc
        try:
            self._model = keras.applications.MobileNetV2(weights=self.weights)
            self._preprocess = keras.applications.mobilenet_v2.preprocess_input
            self._decode = keras.applications.mobilenet_v2.decode_predictions
        except Exception as exc:
            raise BackendUnavailable(f"MobileNetV2 load failed: {exc}") from exc
        return self

    def predict(self, image_path: Path) -> ClassificationResult:
        """Preprocess → model.predict → top-1 → mapping → shared routing."""
        path = Path(image_path)
        if self._model is None or self._preprocess is None or self._decode is None:
            raise PredictFailed("mobilenet backend not loaded (call load() first)")
        try:
            import numpy as np
            from PIL import Image
        except Exception as exc:
            raise PredictFailed(f"image dependencies unavailable: {exc}") from exc
        try:
            with Image.open(path) as img:
                arr = np.asarray(
                    img.convert("RGB").resize((224, 224)), dtype=np.float32
                )
        except Exception as exc:
            raise PredictFailed(f"unreadable image {path.name}: {exc}") from exc
        try:
            batch = self._preprocess(np.expand_dims(arr, 0))
            preds = self._model.predict(batch, verbose=0)
            decoded = self._decode(preds, top=1)[0][0]
            raw_label = str(decoded[1]).lower()
            confidence = float(decoded[2])
        except Exception as exc:
            raise PredictFailed(f"inference failed for {path.name}: {exc}") from exc

        category = IMAGENET_LABEL_TO_CATEGORY.get(raw_label)
        final, reason = self.route(category, confidence, raw_label=raw_label)
        return ClassificationResult(
            image_path=path,
            category=final,
            confidence=confidence,
            backend=self.name,
            raw_label=raw_label,
            reason=reason,
            probabilities=tuple(1.0 if c == final else 0.0 for c in CATEGORIES),
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
        #                   argmax over class indices -> category + confidence,
        #                   then pass the mapped category through
        #                   BaseClassifier.route (Story 2.3) so threshold and
        #                   normalization stay in one place for every backend.
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
