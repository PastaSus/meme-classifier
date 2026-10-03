"""Unit tests for inbox validation and scan wiring in cli.run (Story 1.4, FR-A1).

TF-free: no classifier is constructed here. The scan call is stubbed to assert
flag wiring, so this suite passes with TensorFlow absent (NFR-A1).
"""
from __future__ import annotations

from pathlib import Path

import cli as cli_mod
from classifier import ClassificationResult, PredictFailed, get_classifier
from cli import build_parser, run
from organizer import OrganizeReport


def _args(**overrides):
    """Parser defaults (from config.py) with targeted overrides."""
    args = build_parser().parse_args([])
    for key, value in overrides.items():
        setattr(args, key, value)
    return args


class TestPathValidation:
    def test_missing_input_dir_exits_1_without_side_effects(
        self, tmp_path: Path, capsys
    ) -> None:
        missing = tmp_path / "nope"
        out = tmp_path / "out"

        assert run(_args(input_dir=str(missing), output=str(out))) == 1

        assert not missing.exists()
        assert not out.exists()  # exit before the output tree is created

    def test_output_path_that_is_a_file_exits_1(self, tmp_path: Path) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        blocker = tmp_path / "out"
        blocker.write_bytes(b"not-a-folder")

        assert run(_args(input_dir=str(inbox), output=str(blocker))) == 1

    def test_empty_inbox_exits_0(self, tmp_path: Path, capsys) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir()

        assert run(_args(input_dir=str(inbox), output=str(tmp_path / "out"))) == 0

        assert "No images found" in capsys.readouterr().out
        assert not (tmp_path / "out").exists()


class TestScanWiring:
    def test_recursive_flag_forwarded_to_scan(self, tmp_path: Path, monkeypatch) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        out = tmp_path / "out"
        captured: dict = {}

        def fake_scan(input_dir, recursive=False, exclude=None):
            captured.update(input_dir=input_dir, recursive=recursive, exclude=exclude)
            return []

        monkeypatch.setattr(cli_mod, "scan_images", fake_scan)

        assert run(_args(input_dir=str(inbox), output=str(out), recursive=True)) == 0
        assert captured["recursive"] is True
        assert captured["input_dir"] == Path(inbox)
        assert captured["exclude"] == Path(out)

    def test_recursive_defaults_to_off(self, tmp_path: Path, monkeypatch) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        captured: dict = {}

        def fake_scan(input_dir, recursive=True, exclude=None):
            captured["recursive"] = recursive
            return []

        monkeypatch.setattr(cli_mod, "scan_images", fake_scan)

        assert run(_args(input_dir=str(inbox), output=str(tmp_path / "out"))) == 0
        assert captured["recursive"] is False  # PRD 2.1 default


class TestThresholdWiring:
    """Story 2.3 (AR-4): --threshold flows through the factory; cli trusts
    result.category and never re-routes."""

    def _run_with_stub(
        self, tmp_path: Path, monkeypatch, predict, threshold: float = 0.6
    ):
        """Run cli.run with a stubbed scan/factory/organize; return factory args and jobs."""
        captured: dict = {}

        class StubBackend:
            def load(self):
                return self

            def predict(self, path):
                return predict(path)

        def fake_factory(backend, threshold=0.45):
            captured.update(backend=backend, threshold=threshold)
            return StubBackend()

        def fake_scan(input_dir, recursive=False, exclude=None):
            return [tmp_path / "meme.jpg"]

        jobs: dict = {}

        def fake_organize(job_list, output, dry_run=False):
            jobs["list"] = list(job_list)
            return OrganizeReport(records=[])

        monkeypatch.setattr(cli_mod, "get_classifier", fake_factory)
        monkeypatch.setattr(cli_mod, "scan_images", fake_scan)
        monkeypatch.setattr(cli_mod, "organize", fake_organize)

        inbox = tmp_path / "inbox"
        inbox.mkdir()
        args = _args(
            input_dir=str(inbox), output=str(tmp_path / "out"), threshold=threshold
        )
        assert run(args) == 0
        return captured, jobs["list"]

    def test_threshold_reaches_the_factory(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        def predict(path):
            return ClassificationResult(
                image_path=path, category="cat-memes", confidence=0.99, backend="stub"
            )

        captured, filed = self._run_with_stub(tmp_path, monkeypatch, predict)
        assert captured == {"backend": "mobilenet", "threshold": 0.6}
        assert [j.category for j in filed] == ["cat-memes"]

    def test_cli_trusts_layer_category_without_rerouting(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # A raw low-confidence member category bypassing route(): cli must file
        # it as-is — the threshold rule lives in the layer, not here.
        def predict(path):
            return ClassificationResult(
                image_path=path, category="cat-memes", confidence=0.10, backend="stub"
            )

        _, filed = self._run_with_stub(tmp_path, monkeypatch, predict)
        assert [j.category for j in filed] == ["cat-memes"]

    def test_layer_routed_unsorted_is_filed_unsorted(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        layer = get_classifier("mobilenet")  # real factory, TF-free construction

        def predict(path):
            final, _ = layer.route("cat-memes", 0.10)
            return ClassificationResult(
                image_path=path, category=final, confidence=0.10, backend="mobilenet"
            )

        _, filed = self._run_with_stub(tmp_path, monkeypatch, predict)
        assert [j.category for j in filed] == ["unsorted"]


class TestReportWiring:
    """Story 3.2 (AD-7/AC-A4/AR-7): failures become reason-carrying unsorted
    jobs; the empty inbox renders the organizer-owned empty report."""

    def test_corrupt_image_becomes_reason_carrying_unsorted_job(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        bad = inbox / "bad.jpg"
        bad.write_bytes(b"not an image")
        good = inbox / "good.jpg"
        good.write_bytes(b"fake-image-bytes")

        class StubBackend:
            def load(self):
                return self

            def predict(self, path):
                if path.name == "bad.jpg":
                    raise PredictFailed("unreadable image bad.jpg: cannot identify")
                return ClassificationResult(
                    image_path=path, category="cat-memes", confidence=0.99,
                    backend="stub",
                )

        monkeypatch.setattr(
            cli_mod, "get_classifier", lambda backend, threshold=0.45: StubBackend()
        )

        args = _args(input_dir=str(inbox), output=str(tmp_path / "out"), dry_run=True)
        assert run(args) == 0  # run continues past the failure

        out = capsys.readouterr().out  # stdout only: log lines go to stderr
        assert "unreadable image bad.jpg" in out  # in the report, never only the log
        assert "cat-memes" in out
        assert bad.is_file() and good.is_file()  # dry-run touches nothing

    def test_empty_inbox_renders_empty_report(
        self, tmp_path: Path, capsys
    ) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir()

        assert run(_args(input_dir=str(inbox), output=str(tmp_path / "out"))) == 0

        out = capsys.readouterr().out
        assert "No images found" in out
        assert "Nothing to organize." in out
        assert "planned: 0 | moved: 0 | skipped: 0 | refused: 0 | failed: 0" in out