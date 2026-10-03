"""Unit tests for the classifier contract, backend selection (Story 2.1), the
MobileNetV2 body (Story 2.2), and the shared routing policy (Story 2.3).

TF-free by default: contract/factory tests and the AD-7 failure paths never
import TensorFlow, so this module runs with TF absent (NFR-A1). The tests that
need real inference/graphics are gathered in `TestMobileNetV2TF` behind a
`needs_tf` skip. The custom-CNN body tests arrive with Story 4.2.
"""
from __future__ import annotations

import importlib.util
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
from config import CATEGORIES, CONFIDENCE_THRESHOLD, MODEL_BACKENDS

needs_tf = pytest.mark.skipif(
    importlib.util.find_spec("tensorflow") is None,
    reason="TensorFlow not installed (NFR-A1: QA must run without it)",
)


def _image(path: Path, colour: tuple[int, int, int]) -> Path:
    """Write a small solid-colour RGB image (needs Pillow only)."""
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 64), colour).save(path)
    return path


def _touch(path: Path) -> Path:
    """Write a file that is not a decodable image."""
    path.write_bytes(b"not an image")
    return path


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

    def test_custom_cnn_body_is_still_a_stub(self) -> None:
        # Story 2.1 owned the contract; the custom-CNN body lands in 4.2.
        with pytest.raises(NotImplementedError):
            CustomCNNClassifier().load()

    def test_exceptions_are_distinct_and_catchable(self) -> None:
        assert issubclass(BackendUnavailable, Exception)
        assert issubclass(PredictFailed, Exception)
        assert not issubclass(PredictFailed, BackendUnavailable)


class TestMobileNetFailurePaths:
    """TF-free: AD-7 stable failures must be raised, never leak as crashes."""

    def test_unloaded_predict_raises_stable_failure(self) -> None:
        with pytest.raises(PredictFailed, match="not loaded"):
            MobileNetV2Classifier().predict(Path("x.jpg"))

    def test_unloaded_failure_names_the_backend(self) -> None:
        with pytest.raises(PredictFailed, match="mobilenet"):
            MobileNetV2Classifier().predict(Path("x.jpg"))

    def test_factory_built_backend_is_still_unloaded(self) -> None:
        # AD-8: the factory must not fetch weights; only load() does.
        with pytest.raises(PredictFailed):
            get_classifier("mobilenet").predict(Path("x.jpg"))


@pytest.fixture(scope="module")
def mobilenet() -> MobileNetV2Classifier:
    """One real MobileNetV2 load per module (weights cached after first run)."""
    return MobileNetV2Classifier().load()


@needs_tf
class TestMobileNetV2TF:
    """Real inference; ImageNet weights are cached after the first run (AD-8)."""

    def test_load_returns_self_and_builds_model(
        self, mobilenet: MobileNetV2Classifier
    ) -> None:
        assert isinstance(mobilenet, MobileNetV2Classifier)
        assert mobilenet._model is not None

    def test_predict_returns_result_over_five_categories(
        self, mobilenet: MobileNetV2Classifier, tmp_path: Path
    ) -> None:
        path = _image(tmp_path / "cat.png", (200, 150, 100))
        result = mobilenet.predict(path)
        assert result.category in {*CATEGORIES, "unsorted"}
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.probabilities) == len(CATEGORIES)
        assert result.backend == "mobilenet"
        assert result.image_path == path
        assert result.raw_label

    def test_unmapped_label_is_unsorted_with_reason(
        self, mobilenet: MobileNetV2Classifier, tmp_path: Path
    ) -> None:
        result = mobilenet.predict(_image(tmp_path / "blob.png", (12, 34, 56)))
        if result.category == "unsorted":
            assert result.reason is not None and "unmapped label" in result.reason
        else:
            assert result.reason is None

    def test_corrupt_file_raises_stable_failure(
        self, mobilenet: MobileNetV2Classifier, tmp_path: Path
    ) -> None:
        with pytest.raises(PredictFailed, match="unreadable image"):
            mobilenet.predict(_touch(tmp_path / "bad.jpg"))

    def test_missing_file_raises_stable_failure(
        self, mobilenet: MobileNetV2Classifier, tmp_path: Path
    ) -> None:
        with pytest.raises(PredictFailed):
            mobilenet.predict(tmp_path / "gone.jpg")


class TestThresholdRouting:
    """Story 2.3: the single routing policy lives in the classifier layer.

    TF-free: `route()` needs no model, so every path is asserted without
    TensorFlow (NFR-A1).
    """

    def test_below_threshold_routes_to_unsorted_with_exact_reason(self) -> None:
        assert _StubBackend().route("cat-memes", 0.40) == (
            "unsorted",
            "confidence 0.40 < 0.45",
        )

    def test_threshold_boundary_is_inclusive(self) -> None:
        assert _StubBackend().route("cat-memes", 0.45) == ("cat-memes", None)

    def test_unmapped_routes_to_unsorted_regardless_of_confidence(self) -> None:
        for confidence in (0.10, 0.99):
            final, reason = _StubBackend().route(
                None, confidence, raw_label="toaster"
            )
            assert final == "unsorted"
            assert reason == "unmapped label 'toaster'"

    def test_unknown_category_is_normalized_with_reason(self) -> None:
        final, reason = _StubBackend().route("dank-memes", 0.99)
        assert final == "unsorted"
        assert reason is not None and "dank-memes" in reason

    def test_member_above_threshold_passes_through(self) -> None:
        assert _StubBackend().route("cat-memes", 0.99) == ("cat-memes", None)

    def test_custom_threshold_changes_the_cutoff(self) -> None:
        assert _StubBackend(threshold=0.9).route("cat-memes", 0.85)[0] == "unsorted"
        assert _StubBackend(threshold=0.9).route("cat-memes", 0.95)[0] == "cat-memes"

    def test_below_threshold_wins_over_unknown_category(self) -> None:
        # Order is pinned: unmapped → threshold → membership. Both rules agree
        # on `unsorted`; the confidence reason is reported.
        assert _StubBackend().route("dank-memes", 0.10) == (
            "unsorted",
            "confidence 0.10 < 0.45",
        )
