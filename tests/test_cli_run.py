"""Unit tests for inbox validation and scan wiring in cli.run (Story 1.4, FR-A1).

TF-free: no classifier is constructed here. The scan call is stubbed to assert
flag wiring, so this suite passes with TensorFlow absent (NFR-A1).
"""
from __future__ import annotations

from pathlib import Path

import cli as cli_mod
from cli import build_parser, run


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