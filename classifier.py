"""Classification backends for the Meme & Reaction Image Organizer (FR-A2, FR-A3).

Two backends from the lab reference sheet share one ABC contract:

* ``mobilenet``    — MobileNetV2 pre-trained on ImageNet + label->category
                     mapping (zero-shot default, needs no training data).
* ``custom-cnn``   — hand-built CNN (Conv2D -> MaxPooling2D -> Flatten ->
                     Dense, categorical cross-entropy) trained on labelled
                     folders.

``mobilenet`` is implemented (ImageNet inference + label mapping); the
``custom-cnn`` body loads a Story 4.1 ``.keras`` artifact and predicts a
five-element distribution over ``config.CATEGORIES``.
"""
from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from config import (
    CATEGORIES,
    CONFIDENCE_THRESHOLD,
    DEFAULT_MODEL_PATH,
    IMAGE_EXTENSIONS,
    IMAGENET_LABEL_TO_CATEGORY,
    MODEL_BACKENDS,
)

logger = logging.getLogger(__name__)


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
    trained with categorical cross-entropy on labelled category folders
    (Story 4.1 ``train_labeled_model``). Inference mirrors training
    preprocessing (64px RGB, /255) and returns the five-element softmax
    distribution over ``config.CATEGORIES``; the shared ``route()`` policy
    applies threshold handling exactly like the mobilenet backend.
    """

    name = "custom-cnn"

    def __init__(
        self, model_path: Path | str | None = None, threshold: float = CONFIDENCE_THRESHOLD
    ) -> None:
        super().__init__(threshold=threshold)
        # AD-11: the default resolves to the single config literal; an
        # explicit --model-path always wins (threaded via get_classifier).
        self.model_path = (
            Path(model_path) if model_path is not None else Path(DEFAULT_MODEL_PATH)
        )
        self._model = None

    def load(self) -> "CustomCNNClassifier":
        """Load a Story 4.1 ``.keras`` artifact (AD-10).

        Missing files and artifacts whose output is not five-wide (e.g.
        binary heads) are rejected as unavailable — cli maps that to exit 2
        (or the dry-run unsorted fallback), never a traceback.
        """
        # Missing-file check first (stdlib): precise "artifact not found"
        # with or without TensorFlow installed.
        if not self.model_path.is_file():
            raise BackendUnavailable(
                f"custom-cnn artifact not found: {self.model_path}"
            )
        try:
            from tensorflow import keras
        except Exception as exc:
            raise BackendUnavailable(f"TensorFlow unavailable: {exc}") from exc
        try:
            self._model = keras.models.load_model(str(self.model_path))
        except Exception as exc:
            raise BackendUnavailable(
                f"custom-cnn load failed for {self.model_path}: {exc}"
            ) from exc
        width = self._model.output_shape[-1]
        if width != len(CATEGORIES):
            self._model = None
            raise BackendUnavailable(
                f"custom-cnn artifact has {width} outputs, "
                f"expected {len(CATEGORIES)} ({', '.join(CATEGORIES)})"
            )
        return self

    def predict(self, image_path: Path) -> ClassificationResult:
        """Preprocess (mirror of training) → predict → top-1 → shared routing."""
        path = Path(image_path)
        if self._model is None:
            raise PredictFailed("custom-cnn backend not loaded (call load() first)")
        try:
            import numpy as np
            from PIL import Image
        except Exception as exc:
            raise PredictFailed(f"image dependencies unavailable: {exc}") from exc
        try:
            with Image.open(path) as img:
                arr = np.asarray(
                    img.convert("RGB").resize(
                        (_TRAIN_IMAGE_SIZE, _TRAIN_IMAGE_SIZE)
                    ),
                    dtype=np.float32,
                )
        except Exception as exc:
            raise PredictFailed(f"unreadable image {path.name}: {exc}") from exc
        try:
            probs = self._model.predict(
                np.expand_dims(arr / 255.0, 0), verbose=0
            )[0]
            distribution = tuple(float(p) for p in probs)
            top = int(np.argmax(probs))
            raw_label = CATEGORIES[top]
            confidence = distribution[top]
        except Exception as exc:
            raise PredictFailed(f"inference failed for {path.name}: {exc}") from exc

        final, reason = self.route(raw_label, confidence, raw_label=raw_label)
        return ClassificationResult(
            image_path=path,
            category=final,
            confidence=confidence,
            backend=self.name,
            raw_label=raw_label,
            reason=reason,
            probabilities=distribution,
        )


_BACKENDS: dict[str, type[BaseClassifier]] = {
    MobileNetV2Classifier.name: MobileNetV2Classifier,
    CustomCNNClassifier.name: CustomCNNClassifier,
}


# --- Training hyperparameters (Story 4.1, FR-A9) ----------------------------
# Small-CPU values picked by this story — deliberately NOT CLI flags (spec).
# Recorded here and echoed in the cli train summary.
_TRAIN_IMAGE_SIZE = 64  # matches the tests/fixtures scale (64x64)
_TRAIN_EPOCHS = 5
_TRAIN_BATCH_SIZE = 16
_TRAIN_CONV_FILTERS = 32


def train_labeled_model(
    root: Path | str, model_path: Path | str
) -> dict[str, object]:
    """Fit the AD-10 lab CNN on ``<root>/<category>/*.jpg`` and save ``.keras``.

    Architecture (lab sheet, AD-10): Conv2D -> MaxPooling2D -> Flatten ->
    Dense(softmax) with categorical cross-entropy, ``adam`` optimizer. Labels
    follow ``config.CATEGORIES`` order. This is the ONLY training entry point
    (ML firewall: TensorFlow/Pillow/NumPy are imported function-local so the
    module stays importable — and cli stays runnable — without them).

    Hyperparameters: image 64x64, 5 epochs, batch 16, Conv2D(32, 3x3, relu).

    Returns a summary dict with ``samples``, ``epochs``, ``batch_size``,
    ``image_size``, ``per_category`` (``{category: count}``) and
    ``model_path`` (resolved ``Path``) for the cli train summary.

    Raises:
        FileNotFoundError: *root* is not a directory (cli maps to exit 1).
        ValueError: no (readable) training images under *root* (exit 1).
        BackendUnavailable: TF/PIL/numpy missing or fit/save failed (exit 2).
    """
    root_path = Path(root)
    if not root_path.is_dir():
        raise FileNotFoundError(f"Training root does not exist: {root_path}")

    # Stdlib-only collection first, so BAD_ROOT stays TF-free (exit 1 even
    # where TensorFlow is absent).
    buckets: dict[str, list[Path]] = {}
    for category in CATEGORIES:
        subdir = root_path / category
        if not subdir.is_dir():
            continue
        try:
            files = sorted(
                p
                for p in subdir.iterdir()
                if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
            )
        except OSError as exc:
            # An unreadable subdir contributes nothing (exit 1 via the
            # no-images ValueError below, never the TF-failure bucket).
            logger.warning("Skipping unreadable training subdir %s (%s)", subdir, exc)
            continue
        if files:
            buckets[category] = files
    if not buckets:
        raise ValueError(f"No training images found under {root_path}")

    try:
        import numpy as np
        from PIL import Image
        from tensorflow import keras
    except Exception as exc:
        raise BackendUnavailable(
            f"Training dependencies unavailable: {exc}"
        ) from exc

    try:
        images: list = []
        labels: list[int] = []
        for index, category in enumerate(CATEGORIES):
            for path in buckets.get(category, []):
                try:
                    with Image.open(path) as img:
                        arr = np.asarray(
                            img.convert("RGB").resize(
                                (_TRAIN_IMAGE_SIZE, _TRAIN_IMAGE_SIZE)
                            ),
                            dtype=np.float32,
                        )
                except Exception as exc:
                    # AC-A4 spirit: a corrupt file never aborts the batch.
                    logger.warning("Skipping unreadable training image %s (%s)", path, exc)
                    continue
                images.append(arr / 255.0)
                labels.append(index)
        if not images:
            raise ValueError(f"No readable training images under {root_path}")
        X = np.stack(images).astype(np.float32)
        y = np.eye(len(CATEGORIES), dtype=np.float32)[np.asarray(labels)]

        model = keras.Sequential(
            [
                keras.layers.Input(
                    shape=(_TRAIN_IMAGE_SIZE, _TRAIN_IMAGE_SIZE, 3)
                ),
                keras.layers.Conv2D(
                    _TRAIN_CONV_FILTERS, (3, 3), activation="relu"
                ),
                keras.layers.MaxPooling2D((2, 2)),
                keras.layers.Flatten(),
                keras.layers.Dense(len(CATEGORIES), activation="softmax"),
            ]
        )
        model.compile(
            optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"]
        )
        model.fit(
            X, y, epochs=_TRAIN_EPOCHS, batch_size=_TRAIN_BATCH_SIZE, verbose=0
        )

        out_path = Path(model_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write: save to a temp sibling (same dir => same filesystem)
        # and os.replace onto the target, so a failed save can neither leave
        # a fresh partial nor truncate a pre-existing artifact.
        tmp_path = out_path.parent / (out_path.stem + ".tmp.keras")
        try:
            model.save(str(tmp_path))
            os.replace(tmp_path, out_path)
        except Exception:
            try:
                if tmp_path.is_file():
                    tmp_path.unlink()
            except OSError:
                pass
            raise
    except ValueError:
        raise
    except BackendUnavailable:
        raise
    except Exception as exc:
        raise BackendUnavailable(f"Training failed: {exc}") from exc

    per_category: dict[str, int] = {}
    for label in labels:
        name = CATEGORIES[label]
        per_category[name] = per_category.get(name, 0) + 1
    return {
        "samples": int(len(images)),
        "epochs": _TRAIN_EPOCHS,
        "batch_size": _TRAIN_BATCH_SIZE,
        "image_size": _TRAIN_IMAGE_SIZE,
        "per_category": per_category,
        "model_path": out_path.resolve(),
    }


def get_classifier(
    backend: str,
    threshold: float = CONFIDENCE_THRESHOLD,
    model_path: Path | str | None = None,
) -> BaseClassifier:
    """Factory validated against config.MODEL_BACKENDS (FR-A2).

    *threshold* flows into the backend so routing stays in one place (AD-10).
    *model_path* flows into the custom-cnn backend only (FR-A2, NFR-A4);
    other backends ignore it. Names outside the config allow-list raise
    BackendUnavailable, which the CLI maps to exit 2 instead of a traceback.
    """
    if backend not in MODEL_BACKENDS or backend not in _BACKENDS:
        raise BackendUnavailable(
            f"Unknown backend {backend!r}. Choose from: {sorted(_BACKENDS)}"
        )
    logger.debug("Selected backend: %s", backend)
    if backend == CustomCNNClassifier.name:
        return CustomCNNClassifier(model_path=model_path, threshold=threshold)
    return _BACKENDS[backend](threshold=threshold)
