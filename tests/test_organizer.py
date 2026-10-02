"""Unit tests for the organizer module (stdlib-only, no TensorFlow required)."""
from __future__ import annotations

from pathlib import Path

import pytest

from config import CATEGORIES
from organizer import (
    STATUS_MOVED,
    STATUS_PLANNED,
    STATUS_SKIPPED,
    OrganizeJob,
    organize,
    sanitize_category,
    scan_images,
    unique_destination,
)


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake-image-bytes")
    return path


class TestScanImages:
    def test_filters_non_images_and_hidden(self, tmp_path: Path) -> None:
        _touch(tmp_path / "a.jpg")
        _touch(tmp_path / "b.PNG")
        _touch(tmp_path / "notes.txt")
        _touch(tmp_path / ".hidden" / "secret.jpg")
        _touch(tmp_path / ".DS_Store")

        found = scan_images(tmp_path)

        assert [p.name for p in found] == ["a.jpg", "b.PNG"]

    def test_recursion_is_off_by_default(self, tmp_path: Path) -> None:
        inbox = tmp_path / "inbox"
        _touch(inbox / "top.jpg")
        _touch(inbox / "nested" / "deep.jpg")

        flat = scan_images(inbox)
        recursive = scan_images(inbox, recursive=True)

        # PRD 2.1: `-r` opts into subfolders, plain scan stays top-level.
        assert [p.name for p in flat] == ["top.jpg"]
        assert len(recursive) == 2

    def test_exclude_skips_output_tree(self, tmp_path: Path) -> None:
        inbox = tmp_path / "inbox"
        out = inbox / "organized"
        _touch(inbox / "top.jpg")
        _touch(out / "cat-memes" / "already.jpg")

        found = scan_images(inbox, recursive=True, exclude=out)

        assert [p.name for p in found] == ["top.jpg"]

    def test_missing_directory_raises(self, tmp_path: Path) -> None:
        with pytest.raises(NotADirectoryError):
            scan_images(tmp_path / "does-not-exist")


class TestSanitizeCategory:
    def test_normalizes_allowed_labels(self) -> None:
        assert sanitize_category("Cat Memes") == "cat-memes"
        assert sanitize_category("CHAOTIC_SCREENSHOTS") == "chaotic-screenshots"

    @pytest.mark.parametrize("bad", ["../etc", "", "..", "not-a-category", "a/b"])
    def test_rejects_disallowed(self, bad: str) -> None:
        with pytest.raises(ValueError):
            sanitize_category(bad)


class TestUniqueDestination:
    def test_appends_numeric_suffix_on_collision(self, tmp_path: Path) -> None:
        _touch(tmp_path / "meme.jpg")

        assert unique_destination(tmp_path, "meme.jpg") == tmp_path / "meme-1.jpg"
        _touch(tmp_path / "meme-1.jpg")
        assert unique_destination(tmp_path, "meme.jpg") == tmp_path / "meme-2.jpg"

    def test_no_collision_returns_original(self, tmp_path: Path) -> None:
        assert unique_destination(tmp_path, "fresh.jpg") == tmp_path / "fresh.jpg"


class TestOrganize:
    def test_moves_into_labelled_subfolder(self, tmp_path: Path) -> None:
        src = _touch(tmp_path / "inbox" / "cat.jpg")
        out = tmp_path / "organized"

        report = organize(
            [OrganizeJob(src, "cat-memes", 0.9)], out, allowed=CATEGORIES
        )

        assert report.moved == 1
        assert (out / "cat-memes" / "cat.jpg").is_file()
        assert not src.exists()
        assert report.records[0].status == STATUS_MOVED

    def test_dry_run_touches_nothing(self, tmp_path: Path) -> None:
        src = _touch(tmp_path / "inbox" / "gym.jpg")
        out = tmp_path / "organized"

        report = organize(
            [OrganizeJob(src, "gym-memes", 0.8)], out, dry_run=True, allowed=CATEGORIES
        )

        assert report.planned == 1
        assert report.moved == 0
        assert src.is_file()
        assert not out.exists()

    def test_collision_between_runs_is_renamed(self, tmp_path: Path) -> None:
        out = tmp_path / "organized"
        first = _touch(tmp_path / "inbox" / "one" / "cat.jpg")
        second = _touch(tmp_path / "inbox" / "two" / "cat.jpg")

        organize([OrganizeJob(first, "cat-memes")], out, allowed=CATEGORIES)
        organize([OrganizeJob(second, "cat-memes")], out, allowed=CATEGORIES)

        assert (out / "cat-memes" / "cat.jpg").is_file()
        assert (out / "cat-memes" / "cat-1.jpg").is_file()

    def test_disallowed_category_is_skipped_not_fatal(self, tmp_path: Path) -> None:
        src = _touch(tmp_path / "inbox" / "x.jpg")

        report = organize(
            [OrganizeJob(src, "../../evil", 0.5)], tmp_path / "out", allowed=CATEGORIES
        )

        assert report.skipped == 1
        assert report.records[0].status == STATUS_SKIPPED
        assert src.is_file()
        assert not (tmp_path / "out").exists()

    def test_missing_source_is_skipped(self, tmp_path: Path) -> None:
        ghost = tmp_path / "inbox" / "ghost.jpg"

        report = organize(
            [OrganizeJob(ghost, "unsorted", 0.1)], tmp_path / "out", allowed=CATEGORIES
        )

        assert report.skipped == 1
        assert "not found" in report.records[0].detail

    def test_report_counts_by_category(self, tmp_path: Path) -> None:
        out = tmp_path / "organized"
        jobs = [
            OrganizeJob(_touch(tmp_path / "inbox" / "a.jpg"), "cat-memes", 0.9),
            OrganizeJob(_touch(tmp_path / "inbox" / "b.jpg"), "cat-memes", 0.7),
            OrganizeJob(_touch(tmp_path / "inbox" / "c.jpg"), "gym-memes", 0.6),
        ]

        report = organize(jobs, out, allowed=CATEGORIES)

        assert report.counts_by_category() == {"cat-memes": 2, "gym-memes": 1}
