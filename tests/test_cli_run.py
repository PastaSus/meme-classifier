"""Unit tests for inbox validation and scan wiring in cli.run (Story 1.4, FR-A1).

TF-free: no classifier is constructed here. The scan call is stubbed to assert
flag wiring, so this suite passes with TensorFlow absent (NFR-A1).
"""
from __future__ import annotations

from pathlib import Path

import pytest

import cli as cli_mod
from classifier import (
    BackendUnavailable,
    ClassificationResult,
    PredictFailed,
    get_classifier,
)
from cli import build_parser, run
from organizer import MoveRecord, OrganizeReport


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

        def fake_organize(job_list, output, dry_run=False, fixture_root=None):
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


class TestLifecycleAndExitCodes:
    """Story 3.3 (FR-A8/AD-13): fixed lifecycle order, deterministic exits,
    and a report printed before every return."""

    def test_lifecycle_order_scan_load_organize_render(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        calls: list[str] = []
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        probe = inbox / "meme.jpg"
        probe.write_bytes(b"fake-image-bytes")

        def fake_scan(input_dir, recursive=False, exclude=None):
            calls.append("scan")
            return [probe]

        class StubBackend:
            def load(self):
                calls.append("load")
                return self

            def predict(self, path):
                return ClassificationResult(
                    image_path=path, category="cat-memes", confidence=0.9,
                    backend="stub",
                )

        def fake_organize(job_list, output, dry_run=False, fixture_root=None):
            calls.append("organize")
            return OrganizeReport(records=[])

        def fake_print(report, dry_run):
            calls.append("render")

        monkeypatch.setattr(cli_mod, "scan_images", fake_scan)
        monkeypatch.setattr(
            cli_mod, "get_classifier", lambda backend, threshold=0.45: StubBackend()
        )
        monkeypatch.setattr(cli_mod, "organize", fake_organize)
        monkeypatch.setattr(cli_mod, "_print_report", fake_print)

        assert run(_args(input_dir=str(inbox), output=str(tmp_path / "out"))) == 0
        assert calls == ["scan", "load", "organize", "render"]

    def test_empty_inbox_skips_load_and_organize(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        calls: list[str] = []
        inbox = tmp_path / "inbox"
        inbox.mkdir()

        def fake_scan(input_dir, recursive=False, exclude=None):
            calls.append("scan")
            return []

        def boom(*args, **kwargs):
            raise AssertionError("must not be called on the empty path")

        monkeypatch.setattr(cli_mod, "scan_images", fake_scan)
        monkeypatch.setattr(cli_mod, "get_classifier", boom)
        monkeypatch.setattr(cli_mod, "organize", boom)
        monkeypatch.setattr(
            cli_mod, "_print_report", lambda report, dry_run: calls.append("render")
        )

        assert run(_args(input_dir=str(inbox), output=str(tmp_path / "out"))) == 0
        assert calls == ["scan", "render"]

    def test_missing_input_dir_exits_1_with_report(
        self, tmp_path: Path, capsys
    ) -> None:
        missing = tmp_path / "nope"
        out = tmp_path / "out"

        assert run(_args(input_dir=str(missing), output=str(out))) == 1

        stdout = capsys.readouterr().out
        assert "Nothing to organize." in stdout
        assert "planned: 0 | moved: 0 | skipped: 0 | refused: 0 | failed: 0" in stdout
        assert not out.exists()

    def test_output_is_file_exits_1_with_report(self, tmp_path: Path, capsys) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        blocker = tmp_path / "out"
        blocker.write_bytes(b"not-a-folder")

        assert run(_args(input_dir=str(inbox), output=str(blocker))) == 1

        stdout = capsys.readouterr().out
        assert "Nothing to organize." in stdout
        assert "planned: 0 | moved: 0 | skipped: 0 | refused: 0 | failed: 0" in stdout
        assert blocker.read_bytes() == b"not-a-folder"  # exit before side effects
        assert sorted(p.name for p in tmp_path.iterdir()) == ["inbox", "out"]

    def test_input_path_that_is_a_file_exits_1_with_report(
        self, tmp_path: Path, capsys
    ) -> None:
        not_a_dir = tmp_path / "inbox"
        not_a_dir.write_bytes(b"not-a-folder")
        out = tmp_path / "out"

        assert run(_args(input_dir=str(not_a_dir), output=str(out))) == 1

        stdout = capsys.readouterr().out
        assert "Nothing to organize." in stdout
        assert "planned: 0 | moved: 0 | skipped: 0 | refused: 0 | failed: 0" in stdout
        assert not out.exists()

    @pytest.mark.parametrize(
        "error", [NotADirectoryError("gone"), OSError("disk gone")]
    )
    def test_main_filesystem_error_exits_1_with_report(
        self, tmp_path: Path, monkeypatch, capsys, error: Exception
    ) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir()

        def boom(args):
            raise error

        monkeypatch.setattr(cli_mod, "run", boom)

        assert cli_mod.main([str(inbox)]) == 1

        stdout = capsys.readouterr().out
        assert "Nothing to organize." in stdout
        assert "planned: 0 | moved: 0 | skipped: 0 | refused: 0 | failed: 0" in stdout

    @pytest.mark.parametrize(
        "error",
        [BackendUnavailable("TensorFlow unavailable"), NotImplementedError("todo")],
    )
    def test_backend_down_non_dry_exits_2_with_report_and_no_moves(
        self, tmp_path: Path, monkeypatch, capsys, error: Exception
    ) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        probe = inbox / "meme.jpg"
        probe.write_bytes(b"fake-image-bytes")
        out = tmp_path / "out"

        def fake_factory(backend, threshold=0.45):
            raise error

        def fail_on_move(*args, **kwargs):
            raise AssertionError("organize must not run when load() fails")

        monkeypatch.setattr(cli_mod, "get_classifier", fake_factory)
        monkeypatch.setattr(cli_mod, "organize", fail_on_move)

        assert run(_args(input_dir=str(inbox), output=str(out))) == 2

        stdout = capsys.readouterr().out
        assert "Nothing to organize." in stdout
        assert "planned: 0 | moved: 0 | skipped: 0 | refused: 0 | failed: 0" in stdout
        assert probe.is_file()  # no partial moves
        assert not out.exists()

    @pytest.mark.parametrize(
        "error",
        [BackendUnavailable("TensorFlow unavailable"), NotImplementedError("todo")],
    )
    def test_backend_down_dry_run_plans_unsorted_and_exits_0(
        self, tmp_path: Path, monkeypatch, capsys, error: Exception
    ) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        probe = inbox / "meme.jpg"
        probe.write_bytes(b"fake-image-bytes")
        out = tmp_path / "out"

        def fake_factory(backend, threshold=0.45):
            raise error

        monkeypatch.setattr(cli_mod, "get_classifier", fake_factory)

        assert run(_args(input_dir=str(inbox), output=str(out), dry_run=True)) == 0

        stdout = capsys.readouterr().out
        assert "Warning: backend 'mobilenet' unavailable" in stdout
        assert "unsorted" in stdout
        assert "planned: 1 | moved: 0 | skipped: 0 | refused: 0 | failed: 0" in stdout
        assert probe.is_file()  # dry-run touches nothing
        assert not out.exists()

    def test_backend_down_dry_run_reserves_against_files_on_disk(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        inbox = tmp_path / "inbox"
        (inbox / "one").mkdir(parents=True)
        (inbox / "two").mkdir(parents=True)
        (inbox / "one" / "cat.jpg").write_bytes(b"fake-image-bytes")
        (inbox / "two" / "cat.jpg").write_bytes(b"fake-image-bytes")
        out = tmp_path / "out"
        (out / "unsorted").mkdir(parents=True)
        (out / "unsorted" / "cat.jpg").write_bytes(b"already-filed")

        def fake_factory(backend, threshold=0.45):
            raise BackendUnavailable("TensorFlow unavailable")

        monkeypatch.setattr(cli_mod, "get_classifier", fake_factory)

        assert run(_args(input_dir=str(inbox), output=str(out), dry_run=True, recursive=True)) == 0

        stdout = capsys.readouterr().out
        assert "planned: 2 | moved: 0 | skipped: 0 | refused: 0 | failed: 0" in stdout
        assert "cat-1.jpg" in stdout and "cat-2.jpg" in stdout  # disk + virtual taken
        assert sorted(p.name for p in (out / "unsorted").iterdir()) == ["cat.jpg"]

    def test_backend_down_dry_run_with_fixture_reports_unsorted_accuracy(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        fx = tmp_path / "fx"
        _make_labelled_tree(fx, per_category=2)
        out = tmp_path / "out"

        def fake_factory(backend, threshold=0.45):
            raise BackendUnavailable("TensorFlow unavailable")

        monkeypatch.setattr(cli_mod, "get_classifier", fake_factory)

        code = run(
            _args(
                input_dir=str(fx), output=str(out), recursive=True,
                fixture=str(fx), dry_run=True,
            )
        )

        assert code == 0
        stdout = capsys.readouterr().out
        assert "Fixture accuracy: 2/10" in stdout

    @pytest.mark.parametrize("status", ["failed", "skipped", "refused"])
    def test_reported_non_moves_still_exit_0(
        self, tmp_path: Path, monkeypatch, capsys, status: str
    ) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        probe = inbox / "meme.jpg"
        probe.write_bytes(b"fake-image-bytes")

        class StubBackend:
            def load(self):
                return self

            def predict(self, path):
                return ClassificationResult(
                    image_path=path, category="cat-memes", confidence=0.9,
                    backend="stub",
                )

        def fake_organize(job_list, output, dry_run=False, fixture_root=None):
            return OrganizeReport(
                records=[
                    MoveRecord(
                        source=probe, destination=None, category="cat-memes",
                        confidence=0.9, status=status, detail="error: boom",
                    )
                ]
            )

        monkeypatch.setattr(
            cli_mod, "get_classifier", lambda backend, threshold=0.45: StubBackend()
        )
        monkeypatch.setattr(cli_mod, "organize", fake_organize)

        assert run(_args(input_dir=str(inbox), output=str(tmp_path / "out"))) == 0

        stdout = capsys.readouterr().out
        assert f"{status}: 1" in stdout
        assert "boom" in stdout


def _make_labelled_tree(root: Path, per_category: int = 2) -> list[Path]:
    """Build a labelled tree under *root* using the real CATEGORIES list."""
    from config import CATEGORIES

    paths: list[Path] = []
    for category in CATEGORIES:
        for index in range(per_category):
            p = root / category / f"{category}-{index}.jpg"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"fake-image-bytes")
            paths.append(p)
    return paths


class _ParentNameBackend:
    """Stub backend: predicts the immediate fixture subfolder name."""

    def __init__(self, fixture_root: Path):
        self.fixture_root = Path(fixture_root)

    def load(self):
        return self

    def predict(self, path):
        from classifier import ClassificationResult

        p = Path(path)
        try:
            rel = p.resolve().relative_to(self.fixture_root.resolve())
            category = rel.parts[0] if len(rel.parts) >= 2 else "unsorted"
        except ValueError:
            category = "unsorted"
        return ClassificationResult(
            image_path=p, category=category, confidence=0.99, backend="stub",
        )


class TestFixtureWiring:
    """Story 3.5 (FR-A7/AR-13): --fixture pass-through, render-only cli."""

    def test_explicit_bad_root_exits_1_before_side_effects(
        self, tmp_path: Path, capsys
    ) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        (inbox / "meme.jpg").write_bytes(b"fake-image-bytes")
        out = tmp_path / "out"
        missing = tmp_path / "no-fixture"

        code = run(_args(input_dir=str(inbox), output=str(out), fixture=str(missing)))

        assert code == 1
        stdout = capsys.readouterr().out
        assert "Nothing to organize." in stdout
        assert "planned: 0 | moved: 0 | skipped: 0 | refused: 0 | failed: 0" in stdout
        assert "Fixture accuracy" not in stdout
        assert not out.exists()

    def test_default_root_missing_is_silently_skipped(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        (inbox / "meme.jpg").write_bytes(b"fake-image-bytes")
        out = tmp_path / "out"
        missing_default = tmp_path / "default-gone"
        assert not missing_default.exists()
        monkeypatch.setattr(cli_mod, "DEFAULT_FIXTURE_DIR", missing_default)

        class StubBackend:
            def load(self):
                return self

            def predict(self, path):
                return ClassificationResult(
                    image_path=path, category="cat-memes", confidence=0.9,
                    backend="stub",
                )

        monkeypatch.setattr(
            cli_mod, "get_classifier", lambda backend, threshold=0.45: StubBackend()
        )

        code = run(
            _args(
                input_dir=str(inbox), output=str(out),
                fixture=str(missing_default),
            )
        )

        assert code == 0
        stdout = capsys.readouterr().out
        assert "Fixture accuracy" not in stdout
        assert (out / "cat-memes" / "meme.jpg").is_file()

    def test_fixture_run_reports_accuracy_and_counts(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        from config import CATEGORIES

        fx = tmp_path / "fx"
        _make_labelled_tree(fx, per_category=1)
        out = tmp_path / "out"
        monkeypatch.setattr(
            cli_mod, "get_classifier",
            lambda backend, threshold=0.45: _ParentNameBackend(fx),
        )

        code = run(
            _args(
                input_dir=str(fx), output=str(out), recursive=True,
                fixture=str(fx), dry_run=True,
            )
        )

        assert code == 0
        stdout = capsys.readouterr().out
        assert f"Fixture accuracy: {len(CATEGORIES)}/{len(CATEGORIES)}" in stdout
        for category in CATEGORIES:
            assert category in stdout

    def test_stub_backed_run_meets_both_floors(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        from config import ACCURACY_FLOOR, CATEGORIES, UNSORTED_SHARE_FLOOR

        assert ACCURACY_FLOOR == 0.6
        assert UNSORTED_SHARE_FLOOR == 0.8

        fx = tmp_path / "fx"
        _make_labelled_tree(fx, per_category=2)
        out = tmp_path / "out"
        captured: dict = {}
        real_organize = cli_mod.organize

        def spy_organize(job_list, output, dry_run=False, fixture_root=None):
            captured["fixture_root"] = fixture_root
            return real_organize(
                job_list, output, dry_run=dry_run, fixture_root=fixture_root
            )

        monkeypatch.setattr(
            cli_mod, "get_classifier",
            lambda backend, threshold=0.45: _ParentNameBackend(fx),
        )
        monkeypatch.setattr(cli_mod, "organize", spy_organize)

        code = run(
            _args(
                input_dir=str(fx), output=str(out), recursive=True,
                fixture=str(fx), dry_run=True,
            )
        )

        assert code == 0
        assert Path(captured["fixture_root"]) == fx
        stdout = capsys.readouterr().out
        assert "Fixture accuracy: 10/10" in stdout
        assert "Unsorted share: 20.0%" in stdout

        # Floors judged here in the test, never in organizer/cli logic.
        import re

        match = re.search(r"Fixture accuracy: (\d+)/(\d+)", stdout)
        assert match is not None
        correct, total = int(match.group(1)), int(match.group(2))
        assert correct / total >= ACCURACY_FLOOR
        # 10/10 correct implies zero unsorted; assert the counter-metric too.
        assert "unsorted: 2" in stdout  # per-category counts include it
        assert 2 / 10 <= UNSORTED_SHARE_FLOOR

    def test_backend_down_with_fixture_exits_2_without_accuracy(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        fx = tmp_path / "fx"
        _make_labelled_tree(fx, per_category=1)
        out = tmp_path / "out"

        def fake_factory(backend, threshold=0.45):
            raise BackendUnavailable("TensorFlow unavailable")

        def fail_on_move(*args, **kwargs):
            raise AssertionError("organize must not run when load() fails")

        monkeypatch.setattr(cli_mod, "get_classifier", fake_factory)
        monkeypatch.setattr(cli_mod, "organize", fail_on_move)

        code = run(
            _args(
                input_dir=str(fx), output=str(out), recursive=True,
                fixture=str(fx),
            )
        )

        assert code == 2
        stdout = capsys.readouterr().out
        assert "Fixture accuracy" not in stdout
        assert "Nothing to organize." in stdout

    def test_unmatched_records_excluded_from_accuracy(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        fx = tmp_path / "fx"
        _make_labelled_tree(fx, per_category=1)
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        (inbox / "stray.jpg").write_bytes(b"fake-image-bytes")
        out = tmp_path / "out"

        class StubBackend:
            def load(self):
                return self

            def predict(self, path):
                return ClassificationResult(
                    image_path=path, category="cat-memes", confidence=0.9,
                    backend="stub",
                )

        monkeypatch.setattr(
            cli_mod, "get_classifier", lambda backend, threshold=0.45: StubBackend()
        )

        code = run(
            _args(input_dir=str(inbox), output=str(out), fixture=str(fx))
        )

        assert code == 0
        assert "Fixture accuracy" not in capsys.readouterr().out

    def test_committed_fixture_has_ten_images_two_per_category(self) -> None:
        from config import CATEGORIES, DEFAULT_FIXTURE_DIR

        assert DEFAULT_FIXTURE_DIR.is_dir(), "run tests/fixtures/make_labeled.py first"
        for category in CATEGORIES:
            images = sorted((DEFAULT_FIXTURE_DIR / category).glob("*.jpg"))
            assert len(images) == 2, f"{category}: expected 2 images"


def test_cli_carries_no_floor_logic() -> None:
    """Story 3.5 boundary: cli renders only, never judges floors."""
    import ast

    tree = ast.parse(Path(cli_mod.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "config":
            imported.update(alias.name for alias in node.names)
    assert "ACCURACY_FLOOR" not in imported
    assert "UNSORTED_SHARE_FLOOR" not in imported

def _snapshot_tree(root: Path) -> dict[str, bytes]:
    """Map every file under *root* to its bytes (AC-A10 byte-identity)."""
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


class _FixedCategoryBackend:
    """Stub backend: every image goes to one category."""

    def __init__(self, category: str = "cat-memes"):
        self.category = category

    def load(self):
        return self

    def predict(self, path):
        return ClassificationResult(
            image_path=path, category=self.category, confidence=0.9,
            backend="stub",
        )


class TestIdempotency:
    """Story 3.6 (NFR-A3, AC-A10): re-runs change nothing; restores refile."""

    def test_empty_rerun_leaves_tree_byte_identical(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        for name in ("a.jpg", "b.jpg", "c.jpg"):
            (inbox / name).write_bytes(b"fake-image-bytes")
        out = tmp_path / "out"
        monkeypatch.setattr(
            cli_mod, "get_classifier",
            lambda backend, threshold=0.45: _FixedCategoryBackend(),
        )

        assert run(_args(input_dir=str(inbox), output=str(out))) == 0
        before = _snapshot_tree(out)
        assert len(before) == 3  # sanity: the first run filed something

        assert run(_args(input_dir=str(inbox), output=str(out))) == 0

        stdout = capsys.readouterr().out
        assert "No images found" in stdout
        assert _snapshot_tree(out) == before

    def test_restored_colliding_files_refile_with_suffix(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        (inbox / "cat.jpg").write_bytes(b"original-bytes")
        out = tmp_path / "out"
        monkeypatch.setattr(
            cli_mod, "get_classifier",
            lambda backend, threshold=0.45: _FixedCategoryBackend(),
        )

        assert run(_args(input_dir=str(inbox), output=str(out))) == 0
        assert (out / "cat-memes" / "cat.jpg").is_file()

        # Restore a copy of the filed image to the inbox and re-run: the
        # filed original must survive (never overwrite) via suffixing.
        (inbox / "cat.jpg").write_bytes((out / "cat-memes" / "cat.jpg").read_bytes())
        assert run(_args(input_dir=str(inbox), output=str(out))) == 0

        first = out / "cat-memes" / "cat.jpg"
        second = out / "cat-memes" / "cat-1.jpg"
        assert first.is_file() and second.is_file()
        assert first.read_bytes() == b"original-bytes"
        assert second.read_bytes() == b"original-bytes"

    def test_ten_file_dry_run_reports_ten_planned_and_touches_nothing(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        for index in range(10):
            (inbox / f"img-{index}.jpg").write_bytes(b"fake-image-bytes")
        out = tmp_path / "out"
        before = _snapshot_tree(inbox)
        monkeypatch.setattr(
            cli_mod, "get_classifier",
            lambda backend, threshold=0.45: _FixedCategoryBackend(),
        )

        assert run(_args(input_dir=str(inbox), output=str(out), dry_run=True)) == 0

        stdout = capsys.readouterr().out
        assert "planned: 10 | moved: 0" in stdout
        assert _snapshot_tree(inbox) == before
        assert not out.exists()

    def test_corrupt_image_real_run_files_unsorted_with_reason(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        (inbox / "good.jpg").write_bytes(b"fake-image-bytes")
        (inbox / "corrupt.jpg").write_bytes(b"not-an-image")
        out = tmp_path / "out"

        class FlakyBackend(_FixedCategoryBackend):
            def predict(self, path):
                if Path(path).name == "corrupt.jpg":
                    raise PredictFailed("cannot decode image")
                return super().predict(path)

        monkeypatch.setattr(
            cli_mod, "get_classifier",
            lambda backend, threshold=0.45: FlakyBackend(),
        )

        assert run(_args(input_dir=str(inbox), output=str(out))) == 0

        assert (out / "cat-memes" / "good.jpg").is_file()
        assert (out / "unsorted" / "corrupt.jpg").is_file()
        stdout = capsys.readouterr().out
        assert "cannot decode" in stdout


def test_cli_module_is_stdlib_only() -> None:
    """Story 3.6 (AC-A5/NFR-A1): cli.py imports nothing beyond stdlib.

    TensorFlow stays behind classifier.py's lazy import, so the CLI layer
    loads (and the suite passes) with TensorFlow absent.
    """
    import ast
    import sys
    from pathlib import Path

    src = Path(cli_mod.__file__).read_text(encoding="utf-8")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    third_party = (
        imported - set(sys.stdlib_module_names) - {"classifier", "config", "organizer"}
    )
    assert third_party == set(), f"non-stdlib imports: {sorted(third_party)}"
