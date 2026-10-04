"""Training lifecycle tests (Story 4.1, FR-A9).

TF-gated real fit (mirroring test_backends.py `needs_tf`): a generated
5-category tree must produce a loadable `.keras` artifact. Root validation
(missing root / no images) runs TF-free — it fails before any TensorFlow
import — so those tests pass with TF absent (NFR-A1).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from classifier import BackendUnavailable, train_labeled_model
from config import CATEGORIES

needs_tf = pytest.mark.skipif(
    importlib.util.find_spec("tensorflow") is None,
    reason="TensorFlow not installed (NFR-A1: QA must run without it)",
)


def _image(path: Path, colour: tuple[int, int, int]) -> Path:
    """Write a small solid-colour RGB JPEG (needs Pillow only)."""
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 64), colour).save(path, format="JPEG")
    return path


def _make_tree(root: Path, per_category: int = 2) -> list[Path]:
    """Build a labelled tree `<root>/<category>/*.jpg` for every category."""
    colours = [
        (200, 40, 40),
        (40, 140, 240),
        (120, 40, 180),
        (40, 180, 90),
        (130, 130, 130),
    ]
    paths: list[Path] = []
    for index, category in enumerate(CATEGORIES):
        for slot in range(per_category):
            paths.append(
                _image(root / category / f"{category}-{slot}.jpg", colours[index])
            )
    return paths


class TestTrainRootValidation:
    """TF-free: bad roots fail before any TensorFlow import."""

    def test_missing_root_raises_before_side_effects(self, tmp_path: Path) -> None:
        model_path = tmp_path / "custom-cnn.keras"
        with pytest.raises((FileNotFoundError, NotADirectoryError)):
            train_labeled_model(tmp_path / "nope", model_path)
        assert not model_path.exists()

    def test_root_without_images_raises_and_writes_nothing(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "labeled"
        root.mkdir()
        model_path = tmp_path / "custom-cnn.keras"
        with pytest.raises(ValueError, match="No training images"):
            train_labeled_model(root, model_path)
        assert not model_path.exists()

    def test_root_with_only_unknown_subfolders_raises(self, tmp_path: Path) -> None:
        root = tmp_path / "labeled"
        _image(root / "dank-memes" / "x.jpg", (1, 2, 3))
        with pytest.raises(ValueError, match="No training images"):
            train_labeled_model(root, tmp_path / "custom-cnn.keras")


def test_missing_tensorflow_maps_to_backend_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    """A broken TF import surfaces as BackendUnavailable (cli exit 2).

    TF-free by construction (the import itself is monkeypatched), so this
    runs even where TensorFlow is absent — exactly when it matters most.
    """
    import builtins

    root = tmp_path / "labeled"
    _make_tree(root, per_category=1)

    real_import = builtins.__import__

    def boom(name, *args, **kwargs):
        if name == "tensorflow":
            raise ImportError("No module named 'tensorflow'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", boom)
    with pytest.raises(BackendUnavailable, match="unavailable"):
        train_labeled_model(root, tmp_path / "custom-cnn.keras")


@needs_tf
class TestRealFit:
    """Real few-epoch CPU fit on a generated 5-category tree."""

    def test_fit_saves_loadable_artifact(self, tmp_path: Path) -> None:
        from tensorflow import keras

        root = tmp_path / "labeled"
        _make_tree(root, per_category=2)
        model_path = tmp_path / "models" / "custom-cnn.keras"

        info = train_labeled_model(root, model_path)

        assert info["samples"] == 10
        assert info["epochs"] == 5
        assert info["batch_size"] == 16
        assert info["image_size"] == 64
        assert info["per_category"] == {category: 2 for category in CATEGORIES}
        assert Path(str(info["model_path"])) == model_path.resolve()
        assert model_path.is_file()

        reloaded = keras.models.load_model(str(model_path))
        assert reloaded.output_shape[-1] == len(CATEGORIES)
        assert reloaded.input_shape[1:4] == (64, 64, 3)

    def test_fit_counts_only_known_categories(self, tmp_path: Path) -> None:
        root = tmp_path / "labeled"
        _make_tree(root, per_category=1)
        _image(root / "dank-memes" / "stray.jpg", (9, 9, 9))
        model_path = tmp_path / "custom-cnn.keras"

        info = train_labeled_model(root, model_path)

        assert info["samples"] == len(CATEGORIES)
        assert set(info["per_category"]) == set(CATEGORIES)
        assert model_path.is_file()

    def test_mixed_valid_and_corrupt_counts_only_decoded(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "labeled"
        _make_tree(root, per_category=1)
        (root / "cat-memes" / "corrupt.jpg").write_bytes(b"not an image")
        model_path = tmp_path / "custom-cnn.keras"

        info = train_labeled_model(root, model_path)

        assert info["samples"] == len(CATEGORIES)
        assert info["per_category"] == {category: 1 for category in CATEGORIES}
        assert sum(info["per_category"].values()) == info["samples"]
        assert model_path.is_file()

    def test_all_corrupt_raises_value_error(self, tmp_path: Path) -> None:
        root = tmp_path / "labeled"
        for category in CATEGORIES:
            subdir = root / category
            subdir.mkdir(parents=True, exist_ok=True)
            (subdir / "bad.jpg").write_bytes(b"not an image")
        model_path = tmp_path / "custom-cnn.keras"

        with pytest.raises(ValueError, match="No readable training images"):
            train_labeled_model(root, model_path)
        assert not model_path.exists()

    def test_save_failure_leaves_no_fresh_file(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        from tensorflow import keras

        root = tmp_path / "labeled"
        _make_tree(root, per_category=1)
        model_path = tmp_path / "custom-cnn.keras"
        tmp_sibling = tmp_path / "custom-cnn.tmp.keras"

        def partial(self, filepath, *args, **kwargs):
            Path(filepath).write_bytes(b"partial")
            raise OSError("disk gone")

        monkeypatch.setattr(keras.Model, "save", partial)
        with pytest.raises(BackendUnavailable, match="Training failed"):
            train_labeled_model(root, model_path)
        assert not model_path.exists()
        assert not tmp_sibling.exists()

    def test_save_failure_preserves_preexisting_artifact(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        from tensorflow import keras

        root = tmp_path / "labeled"
        _make_tree(root, per_category=1)
        model_path = tmp_path / "custom-cnn.keras"
        model_path.write_bytes(b"pre-existing-artifact")

        def boom(self, *args, **kwargs):
            raise OSError("disk gone")

        monkeypatch.setattr(keras.Model, "save", boom)
        with pytest.raises(BackendUnavailable, match="Training failed"):
            train_labeled_model(root, model_path)
        assert model_path.read_bytes() == b"pre-existing-artifact"
