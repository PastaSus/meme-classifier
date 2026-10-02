"""Unit tests for the classifier contract and backend selection (Story 2.1).

TF-free: constructing a backend and calling the factory never imports
TensorFlow, so this module runs with TF absent (NFR-A1). Backend-body tests
arrive with the MobileNet (2.2) and custom-CNN (4.2) stories.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from classifier import (
    BackendUnavailable,
    BaseClassifier,
    ClassificationResult,
    CustomCNNClassifier,
    MobileNetV2Classifier,
    PredictFailed,
    get_classifier,
)
from config import CONFIDENCE_THRESHOLD, MODEL_BACKENDS


class _StubBackend(BaseClassifier):
    """Minimal concrete backend: proves the ABC contract is implementable."""

    name = "stub"

    def load(self) -> "_StubBackend":
        return self

    def predict(self, image_path: Path) -> ClassificationResult:
        return ClassificationResult(
            image_path=Path(image_path),
            category="cat-memes",
            confidence=0.9,
            backend=self.name,
        )


class TestContract:
    def test_result_defaults_are_optional(self) -> None:
        result = _StubBackend().predict(Path("x.jpg"))
        assert result.reason is None
        assert result.probabilities == ()
        assert result.raw_label is None

    def test_result_carries_reason_and_probabilities(self) -> None:
        result = ClassificationResult(
            image_path=Path("x.jpg"),
            category="unsorted",
            confidence=0.2,
            backend="stub",
            raw_label="grumpy_cat",
            reason="confidence 0.20 < 0.45",
            probabilities=(0.0, 0.0, 0.0, 0.0, 1.0),
        )
        assert result.reason == "confidence 0.20 < 0.45"
        assert len(result.probabilities) == 5

    def test_stub_follows_abc(self) -> None:
        assert isinstance(_StubBackend(), BaseClassifier)


class TestBackendSelection:
    def test_factory_returns_requested_backend_with_threshold(self) -> None:
        clf = get_classifier("mobilenet", threshold=0.7)
        assert isinstance(clf, MobileNetV2Classifier)
        assert clf.threshold == 0.7

    def test_factory_threshold_defaults_to_config(self) -> None:
        assert get_classifier("mobilenet").threshold == CONFIDENCE_THRESHOLD
        assert get_classifier("custom-cnn").threshold == CONFIDENCE_THRESHOLD

    def test_factory_passes_threshold_to_custom_cnn(self) -> None:
        clf = get_classifier("custom-cnn", threshold=0.99)
        assert isinstance(clf, CustomCNNClassifier)
        assert clf.threshold == 0.99

    @pytest.mark.parametrize("unknown", ["yolo", "", "MOBILENET", "resnet50"])
    def test_factory_rejects_names_outside_config(self, unknown: str) -> None:
        with pytest.raises(BackendUnavailable):
            get_classifier(unknown)

    def test_known_backends_exactly_match_config(self) -> None:
        assert set(MODEL_BACKENDS) == {"mobilenet", "custom-cnn"}
        for backend in MODEL_BACKENDS:
            assert get_classifier(backend).name == backend

    def test_backend_bodies_are_still_stubs(self) -> None:
        # Story 2.1 owns the contract only; bodies land in 2.2/4.2.
        with pytest.raises(NotImplementedError):
            MobileNetV2Classifier().load()
        with pytest.raises(NotImplementedError):
            CustomCNNClassifier().load()

    def test_exceptions_are_distinct_and_catchable(self) -> None:
        assert issubclass(BackendUnavailable, Exception)
        assert issubclass(PredictFailed, Exception)
        assert not issubclass(PredictFailed, BackendUnavailable)
