"""Unit tests for the organizer module (stdlib-only, no TensorFlow required)."""
from __future__ import annotations

from pathlib import Path

import pytest

import organizer as organizer_mod
from config import CATEGORIES
from organizer import (
    STATUS_FAILED,
    STATUS_MOVED,
    STATUS_PLANNED,
    STATUS_REFUSED,
    STATUS_SKIPPED,
    OrganizeJob,
    empty_report,
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

    def test_suffix_preserves_multi_dot_and_missing_suffix(
        self, tmp_path: Path
    ) -> None:
        _touch(tmp_path / "archive.tar.jpg")
        assert unique_destination(tmp_path, "archive.tar.jpg") == (
            tmp_path / "archive.tar-1.jpg"
        )
        _touch(tmp_path / "README")
        assert unique_destination(tmp_path, "README") == tmp_path / "README-1"


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

    def test_dry_run_shared_basename_plans_suffixed_names(self, tmp_path: Path) -> None:
        first = _touch(tmp_path / "inbox" / "one" / "cat.jpg")
        second = _touch(tmp_path / "inbox" / "two" / "cat.jpg")
        out = tmp_path / "organized"

        report = organize(
            [
                OrganizeJob(first, "cat-memes", 0.9),
                OrganizeJob(second, "cat-memes", 0.8),
            ],
            out,
            dry_run=True,
            allowed=CATEGORIES,
        )

        assert report.planned == 2
        assert report.moved == 0
        assert [r.destination.name for r in report.records] == ["cat.jpg", "cat-1.jpg"]
        assert first.is_file() and second.is_file()
        assert not out.exists()

    def test_disallowed_category_is_refused_not_fatal(self, tmp_path: Path) -> None:
        src = _touch(tmp_path / "inbox" / "x.jpg")

        report = organize(
            [OrganizeJob(src, "../../evil", 0.5)], tmp_path / "out", allowed=CATEGORIES
        )

        assert report.refused == 1
        assert report.skipped == 0
        assert report.records[0].status == STATUS_REFUSED
        assert "Category not allowed" in report.records[0].detail
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

    def test_non_moves_excluded_from_counts_but_counted(self, tmp_path: Path) -> None:
        out = tmp_path / "organized"
        jobs = [
            OrganizeJob(_touch(tmp_path / "inbox" / "a.jpg"), "cat-memes", 0.9),
            OrganizeJob(_touch(tmp_path / "inbox" / "evil.jpg"), "../../evil", 0.5),
            OrganizeJob(tmp_path / "inbox" / "ghost.jpg", "unsorted", 0.1),
        ]

        report = organize(jobs, out, allowed=CATEGORIES)

        assert report.counts_by_category() == {"cat-memes": 1}
        assert report.moved == 1
        assert report.refused == 1
        assert report.skipped == 1
        assert report.failed == 0

    def test_move_error_is_failed(self, tmp_path: Path, monkeypatch) -> None:
        src = _touch(tmp_path / "inbox" / "a.jpg")
        out = tmp_path / "organized"

        def boom(source: str, destination: str) -> None:
            raise OSError("disk on fire")

        monkeypatch.setattr(organizer_mod.shutil, "move", boom)

        report = organize([OrganizeJob(src, "cat-memes", 0.9)], out)

        assert report.failed == 1
        assert report.moved == 0
        assert report.records[0].status == STATUS_FAILED
        assert "disk on fire" in report.records[0].detail
        assert src.is_file()

    def test_job_reason_flows_into_record_detail(self, tmp_path: Path) -> None:
        src = _touch(tmp_path / "inbox" / "weird.jpg")
        out = tmp_path / "organized"

        report = organize(
            [OrganizeJob(src, "unsorted", 0.0, reason="unreadable image weird.jpg")],
            out,
        )

        assert report.moved == 1
        assert report.records[0].detail == "unreadable image weird.jpg"

    def test_errors_view_carries_reasons(self, tmp_path: Path) -> None:
        out = tmp_path / "organized"
        jobs = [
            OrganizeJob(_touch(tmp_path / "inbox" / "ok.jpg"), "cat-memes", 0.9),
            OrganizeJob(_touch(tmp_path / "inbox" / "evil.jpg"), "../../evil", 0.5),
            OrganizeJob(tmp_path / "inbox" / "ghost.jpg", "unsorted", 0.1),
        ]

        errors = organize(jobs, out).errors

        assert [r.status for r in errors] == [STATUS_REFUSED, STATUS_SKIPPED]
        assert all(r.detail for r in errors)

    def test_suffix_exhaustion_is_skipped_not_fatal(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # FR-A5: up to MAX_COLLISION_SUFFIX attempts, then skipped. The cap is
        # monkeypatched so no 1001-file fixture is needed — after pinning the
        # production value the story actually ships.
        assert organizer_mod.MAX_COLLISION_SUFFIX == 1000
        monkeypatch.setattr(organizer_mod, "MAX_COLLISION_SUFFIX", 2)
        out = tmp_path / "organized"
        _touch(out / "cat-memes" / "cat.jpg")
        _touch(out / "cat-memes" / "cat-1.jpg")
        _touch(out / "cat-memes" / "cat-2.jpg")
        src = _touch(tmp_path / "inbox" / "cat.jpg")

        report = organize([OrganizeJob(src, "cat-memes")], out, allowed=CATEGORIES)

        assert report.skipped == 1
        assert report.records[0].status == STATUS_SKIPPED
        assert "Could not find a free name" in report.records[0].detail
        assert src.is_file()  # never destroyed

    def test_only_allow_listed_folders_are_created(self, tmp_path: Path) -> None:
        # No explicit `allowed`: exercises the default CATEGORIES fallback on
        # the production call path (cli.run never passes `allowed`).
        good = _touch(tmp_path / "inbox" / "ok.jpg")
        evil = _touch(tmp_path / "inbox" / "evil.jpg")
        out = tmp_path / "organized"

        report = organize(
            [
                OrganizeJob(good, "cat-memes", 0.9),
                OrganizeJob(evil, "../../evil", 0.5),
            ],
            out,
        )

        assert report.moved == 1
        assert report.refused == 1
        assert report.skipped == 0
        assert (out / "cat-memes" / "ok.jpg").is_file()
        assert sorted(p.name for p in out.iterdir()) == ["cat-memes"]
        assert sorted(p.name for p in tmp_path.iterdir()) == ["inbox", "organized"]
        assert evil.is_file()

    def test_intra_batch_collision_is_renamed(self, tmp_path: Path) -> None:
        # The cli-shaped call: one organize() batch, two same-basename jobs.
        out = tmp_path / "organized"
        first = _touch(tmp_path / "inbox" / "one" / "cat.jpg")
        second = _touch(tmp_path / "inbox" / "two" / "cat.jpg")

        report = organize(
            [OrganizeJob(first, "cat-memes"), OrganizeJob(second, "cat-memes")],
            out,
            allowed=CATEGORIES,
        )

        assert report.moved == 2
        assert (out / "cat-memes" / "cat.jpg").is_file()
        assert (out / "cat-memes" / "cat-1.jpg").is_file()
        assert not first.exists() and not second.exists()


def test_organizer_module_is_stdlib_only() -> None:
    """NFR-A1: organizer.py must import nothing beyond stdlib + first-party."""
    import ast
    import sys

    src = Path(organizer_mod.__file__).read_text(encoding="utf-8")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    third_party = imported - set(sys.stdlib_module_names) - {"config"}
    assert third_party == set(), f"non-stdlib imports: {sorted(third_party)}"


def test_empty_report_is_zeroed() -> None:
    report = empty_report()
    assert report.records == []
    assert report.moved == report.planned == 0
    assert report.refused == report.failed == report.skipped == 0
    assert report.errors == []
    assert report.counts_by_category() == {}
    assert report.fixture_correct == 0
    assert report.fixture_total == 0
    assert report.fixture_accuracy is None
    assert report.unsorted_share == 0.0


def _fixture_tree(root: Path) -> dict[str, list[Path]]:
    """Build a tiny labelled tree: {category: [paths]} with fake bytes."""
    tree: dict[str, list[Path]] = {}
    for category in ("cat-memes", "gym-memes"):
        paths = []
        for name in ("a.jpg", "b.jpg"):
            p = root / category / name
            paths.append(_touch(p))
        tree[category] = paths
    return tree


class TestReadFixtureLabels:
    def test_maps_subfolder_name_to_expected_label(self, tmp_path: Path) -> None:
        tree = _fixture_tree(tmp_path / "fx")
        labels = organizer_mod.read_fixture_labels(tmp_path / "fx")

        assert labels[tree["cat-memes"][0].resolve()] == "cat-memes"
        assert labels[tree["gym-memes"][1].resolve()] == "gym-memes"
        assert len(labels) == 4

    def test_missing_root_returns_empty(self, tmp_path: Path) -> None:
        assert organizer_mod.read_fixture_labels(tmp_path / "nope") == {}

    def test_files_directly_under_root_are_skipped(self, tmp_path: Path) -> None:
        _touch(tmp_path / "fx" / "loose.jpg")
        _touch(tmp_path / "fx" / "cat-memes" / "a.jpg")

        labels = organizer_mod.read_fixture_labels(tmp_path / "fx")

        assert len(labels) == 1
        assert list(labels.values()) == ["cat-memes"]

    def test_hidden_files_are_skipped(self, tmp_path: Path) -> None:
        _touch(tmp_path / "fx" / ".hidden" / "secret.jpg")
        _touch(tmp_path / "fx" / "cat-memes" / "a.jpg")

        labels = organizer_mod.read_fixture_labels(tmp_path / "fx")

        assert len(labels) == 1


class TestFixtureAccuracy:
    def test_accuracy_counts_correct_over_matched(self, tmp_path: Path) -> None:
        fx = tmp_path / "fx"
        cat_a = _touch(fx / "cat-memes" / "a.jpg")
        gym_b = _touch(fx / "gym-memes" / "b.jpg")
        out = tmp_path / "out"

        report = organize(
            [
                OrganizeJob(cat_a, "cat-memes", 0.9),
                OrganizeJob(gym_b, "cat-memes", 0.9),  # wrong placement
            ],
            out,
            fixture_root=fx,
        )

        assert report.fixture_total == 2
        assert report.fixture_correct == 1
        assert report.fixture_accuracy == pytest.approx(0.5)

    def test_unmatched_records_are_excluded(self, tmp_path: Path) -> None:
        fx = tmp_path / "fx"
        inside = _touch(fx / "cat-memes" / "a.jpg")
        outside = _touch(tmp_path / "elsewhere" / "b.jpg")
        out = tmp_path / "out"

        report = organize(
            [
                OrganizeJob(inside, "cat-memes", 0.9),
                OrganizeJob(outside, "cat-memes", 0.9),
            ],
            out,
            fixture_root=fx,
        )

        assert report.fixture_total == 1
        assert report.fixture_correct == 1

    def test_non_moves_never_count_as_correct(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        fx = tmp_path / "fx"
        doomed = _touch(fx / "cat-memes" / "doomed.jpg")
        evil = _touch(fx / "cat-memes" / "evil.jpg")
        out = tmp_path / "out"

        def boom(source: str, destination: str) -> None:
            raise OSError("disk on fire")

        monkeypatch.setattr(organizer_mod.shutil, "move", boom)

        report = organize(
            [
                OrganizeJob(doomed, "cat-memes", 0.9),  # failed move
                OrganizeJob(evil, "../../evil", 0.5),  # refused category
            ],
            out,
            fixture_root=fx,
        )

        # Both sources are under the fixture root so both are matched, but
        # neither placed correctly: failed + refused are never correct.
        assert report.fixture_total == 2
        assert report.fixture_correct == 0
        assert report.fixture_accuracy == 0.0

    def test_no_fixture_leaves_zeroed_fields(self, tmp_path: Path) -> None:
        src = _touch(tmp_path / "inbox" / "a.jpg")

        report = organize([OrganizeJob(src, "cat-memes", 0.9)], tmp_path / "out")

        assert report.fixture_total == 0
        assert report.fixture_correct == 0
        assert report.fixture_accuracy is None

    def test_dry_run_accuracy_uses_planned_status(self, tmp_path: Path) -> None:
        fx = tmp_path / "fx"
        a = _touch(fx / "cat-memes" / "a.jpg")
        out = tmp_path / "out"

        report = organize(
            [OrganizeJob(a, "cat-memes", 0.9)],
            out,
            dry_run=True,
            fixture_root=fx,
        )

        assert report.fixture_total == 1
        assert report.fixture_correct == 1

    def test_unsorted_share_counts_placed_only(self, tmp_path: Path) -> None:
        out = tmp_path / "organized"
        jobs = [
            OrganizeJob(_touch(tmp_path / "inbox" / "a.jpg"), "cat-memes", 0.9),
            OrganizeJob(_touch(tmp_path / "inbox" / "b.jpg"), "unsorted", 0.2),
            OrganizeJob(_touch(tmp_path / "inbox" / "evil.jpg"), "../../evil", 0.5),
        ]

        report = organize(jobs, out)

        # refused excluded from placed denominator: 1 unsorted / 2 placed
        assert report.unsorted_share == pytest.approx(0.5)


def test_organizer_carries_no_floor_logic() -> None:
    """Story 3.5 boundary: floors are judged in tests only, never in organizer."""
    import ast

    tree = ast.parse(Path(organizer_mod.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "config":
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
    assert "ACCURACY_FLOOR" not in imported
    assert "UNSORTED_SHARE_FLOOR" not in imported
