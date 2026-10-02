"""Unit tests for the PRD-frozen CLI surface (AD-14, Story 1.3).

TF-free: asserts exact flag names/defaults from PRD section 2.1, drift-name
absence, threshold shape validation at parse time (exit 2), and that every
default comes from config.py — no lifecycle/report behavior covered here.
"""
from __future__ import annotations

import pytest

from cli import build_parser
from config import (
    CONFIDENCE_THRESHOLD,
    DEFAULT_BACKEND,
    DEFAULT_FIXTURE_DIR,
    DEFAULT_INPUT_DIR,
    DEFAULT_MODEL_PATH,
    DEFAULT_OUTPUT_DIR,
    MODEL_BACKENDS,
)


class TestFrozenSurface:
    def test_positional_and_output_defaults(self) -> None:
        args = build_parser().parse_args([])
        assert args.input_dir == str(DEFAULT_INPUT_DIR)
        assert args.output == str(DEFAULT_OUTPUT_DIR)
        assert args.recursive is False

    def test_backend_threshold_and_new_flags(self) -> None:
        args = build_parser().parse_args([])
        assert args.backend == DEFAULT_BACKEND == "mobilenet"
        assert args.threshold == CONFIDENCE_THRESHOLD == 0.45
        assert args.dry_run is False
        assert args.fixture == str(DEFAULT_FIXTURE_DIR)
        assert args.train is None
        assert args.model_path == str(DEFAULT_MODEL_PATH)
        assert args.verbose is False

    def test_explicit_flags_parse(self) -> None:
        args = build_parser().parse_args(
            ["inbox", "-o", "out", "-r", "-b", "custom-cnn", "-t", "0.6",
             "--dry-run", "--fixture", "fx", "--train", "tr",
             "--model-path", "m.keras", "--verbose"]
        )
        assert (args.input_dir, args.output) == ("inbox", "out")
        assert args.recursive is True
        assert (args.backend, args.threshold) == ("custom-cnn", 0.6)
        assert args.dry_run is True
        assert (args.fixture, args.train, args.model_path) == ("fx", "tr", "m.keras")
        assert args.verbose is True

    def test_drift_names_are_gone(self) -> None:
        args = build_parser().parse_args([])
        assert not hasattr(args, "output_dir")
        assert not hasattr(args, "no_recursive")
        with pytest.raises(SystemExit):
            build_parser().parse_args(["--output-dir", "x"])
        with pytest.raises(SystemExit):
            build_parser().parse_args(["--no-recursive"])

    @pytest.mark.parametrize("bad", ["0", "-0.5", "0.0", "1.5", "2", "abc"])
    def test_threshold_rejects_out_of_range_at_parse(self, bad: str) -> None:
        with pytest.raises(SystemExit) as exc:
            build_parser().parse_args(["-t", bad])
        assert exc.value.code == 2

    @pytest.mark.parametrize("good", ["0.01", "0.45", "1", "1.0"])
    def test_threshold_accepts_boundaries(self, good: str) -> None:
        assert build_parser().parse_args(["-t", good]).threshold == float(good)

    def test_backend_choices_match_config(self) -> None:
        assert MODEL_BACKENDS == ("mobilenet", "custom-cnn")
        with pytest.raises(SystemExit):
            build_parser().parse_args(["-b", "yolo"])
