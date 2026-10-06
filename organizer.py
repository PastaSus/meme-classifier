"""Image scanning and file organization for the Meme & Reaction Image Organizer.

Implements FR-A1 (scan) and FR-A4-A7 (move, no-overwrite, dry-run, report).
Pure standard library (os/shutil/pathlib) so it works and is testable without
TensorFlow installed (NFR-A1).

Non-move taxonomy (FR-A7): *refused* (allow-list/policy rejection), *failed*
(move-phase error), *skipped* (never attempted: missing source, exhausted
suffixes). Reasons ride on ``OrganizeJob.reason`` into ``MoveRecord.detail``;
stage errors are appended, never replacing the job reason.
"""
from __future__ import annotations

import logging
import re
import shutil
from collections.abc import Collection, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from config import CATEGORIES, IMAGE_EXTENSIONS, MAX_COLLISION_SUFFIX

logger = logging.getLogger(__name__)

STATUS_MOVED = "moved"
STATUS_PLANNED = "planned"
STATUS_REFUSED = "refused"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"

_NON_MOVE_STATUSES = (STATUS_REFUSED, STATUS_FAILED, STATUS_SKIPPED)


@dataclass(frozen=True)
class OrganizeJob:
    """A single pending move produced by a classifier.

    *reason* carries the classifier-layer failure text (AD-7: organizer
    defines the field, cli fills it) so it can reach the report.
    """

    source: Path
    category: str
    confidence: float = 0.0
    reason: str | None = None


@dataclass(frozen=True)
class MoveRecord:
    """Audit trail for one attempted move."""

    source: Path
    destination: Path | None
    category: str
    confidence: float
    status: str
    detail: str = ""


@dataclass
class OrganizeReport:
    """Aggregated result of an organize run (FR-A7)."""

    records: list[MoveRecord] = field(default_factory=list)
    fixture_correct: int = 0
    fixture_total: int = 0

    @property
    def moved(self) -> int:
        return sum(1 for r in self.records if r.status == STATUS_MOVED)

    @property
    def planned(self) -> int:
        return sum(1 for r in self.records if r.status == STATUS_PLANNED)

    @property
    def refused(self) -> int:
        return sum(1 for r in self.records if r.status == STATUS_REFUSED)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.records if r.status == STATUS_FAILED)

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.records if r.status == STATUS_SKIPPED)

    @property
    def errors(self) -> list[MoveRecord]:
        """Non-move records (refused/failed/skipped) carrying reasons (AR-7)."""
        return [r for r in self.records if r.status in _NON_MOVE_STATUSES]

    @property
    def fixture_accuracy(self) -> float | None:
        """Placement accuracy on the labelled fixture, or None when no fixture.

        Tests compare this against config floors; organizer never enforces them.
        """
        if self.fixture_total == 0:
            return None
        return self.fixture_correct / self.fixture_total

    @property
    def unsorted_share(self) -> float:
        """Share of placed records filed as unsorted (AC-A7 counter-metric).

        Tests compare this against the configured floor; organizer never
        enforces it.
        """
        placed = self.moved + self.planned
        if placed == 0:
            return 0.0
        unsorted = self.counts_by_category().get("unsorted", 0)
        return unsorted / placed

    def counts_by_category(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in self.records:
            if record.status not in (STATUS_MOVED, STATUS_PLANNED):
                continue
            counts[record.category] = counts.get(record.category, 0) + 1
        return dict(sorted(counts.items()))


def empty_report() -> OrganizeReport:
    """Zeroed report for early exits (AR-7): cli renders this, never builds one."""
    return OrganizeReport()


def read_fixture_labels(root: Path | str) -> dict[Path, str]:
    """Map fixture image paths to expected labels (AD-12, FR-A7).

    The immediate subfolder name under *root* is the expected category:
    ``<root>/<category>/image.jpg`` -> ``{resolved_path: "<category>"}``.
    Stdlib-only (pathlib). Missing roots yield ``{}`` so ``organize()``
    degrades to no-accuracy instead of crashing; cli owns explicit-root
    validation. Hidden files/dirs and files sitting directly under *root*
    (no label part) are skipped.
    """
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        return {}
    labels: dict[Path, str] = {}
    for path in root_path.rglob("*"):
        if not path.is_file():
            continue
        try:
            relative = path.resolve().relative_to(root_path)
        except (ValueError, OSError):
            continue
        if not relative.parts or len(relative.parts) < 2:
            continue
        if any(part.startswith(".") for part in relative.parts):
            continue
        labels[path.resolve()] = relative.parts[0]
    return labels


def _has_hidden_part(root: Path, path: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    return any(part.startswith(".") for part in relative.parts)


def scan_images(
    input_dir: Path,
    recursive: bool = False,
    exclude: Path | None = None,
) -> list[Path]:
    """Return sorted image paths under *input_dir* (FR-A1).

    Recursion is OFF by default — `-r` opts in (PRD 2.1). Non-image files,
    hidden files/directories, and anything under *exclude* (typically the
    output root) are ignored.
    """
    root = Path(input_dir).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Input directory does not exist: {root}")

    exclude_root = Path(exclude).resolve() if exclude else None
    candidates: Iterable[Path] = root.rglob("*") if recursive else root.iterdir()

    found: list[Path] = []
    for path in candidates:
        if not path.is_file():
            continue
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if _has_hidden_part(root, path):
            continue
        if exclude_root is not None:
            try:
                path.resolve().relative_to(exclude_root)
                continue  # skip files already living in the output tree
            except ValueError:
                pass
        found.append(path)
    return sorted(found)


def sanitize_category(category: str, allowed: Collection[str] | None = None) -> str:
    """Normalize a category label and validate it against the allow-list (NFR-A2).

    Raises ValueError for anything outside *allowed* (path traversal, unknown
    labels, empty strings, ...).
    """
    allowed_set = set(CATEGORIES if allowed is None else allowed)
    if not isinstance(category, str):
        raise ValueError(f"Category not allowed: {category!r}")
    cleaned = re.sub(r"[\s_]+", "-", category.strip().lower())
    cleaned = re.sub(r"[^a-z0-9-]", "", cleaned)
    if not cleaned or cleaned in {".", ".."} or cleaned not in allowed_set:
        raise ValueError(f"Category not allowed: {category!r}")
    return cleaned


def unique_destination(
    directory: Path, filename: str, reserved: Collection[Path] | None = None
) -> Path:
    """Return a non-colliding destination path (FR-A5): file.jpg, file-1.jpg, ...

    *reserved* holds already-planned paths that do not exist on disk yet (the
    dry-run virtual tree, FR-A6) — they count as taken alongside real files.
    """
    if (
        not isinstance(filename, str)
        or not filename
        or filename in {".", ".."}
        or Path(filename).name != filename
    ):
        # Phase 5 (NFR-A2): a separator-carrying filename would escape
        # *directory* via ``directory / filename`` — refuse instead.
        raise ValueError(f"Unsafe filename: {filename!r}")
    taken = set(reserved) if reserved else set()
    candidate = directory / filename
    if not candidate.exists() and candidate not in taken:
        return candidate
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    for index in range(1, MAX_COLLISION_SUFFIX + 1):
        alternative = directory / f"{stem}-{index}{suffix}"
        if not alternative.exists() and alternative not in taken:
            return alternative
    raise FileExistsError(
        f"Could not find a free name for {filename!r} in {directory} "
        f"after {MAX_COLLISION_SUFFIX} attempts"
    )


def _with_reason(base: str | None, error: str) -> str:
    """Combine a job-carried reason with a stage error without losing either."""
    return f"{base}; {error}" if base else error


def organize(
    jobs: Iterable[OrganizeJob],
    output_dir: Path,
    dry_run: bool = False,
    allowed: Collection[str] | None = None,
    fixture_root: Path | str | None = None,
) -> OrganizeReport:
    """Move classified images into labelled subfolders (FR-A4, FR-A6).

    Never overwrites (FR-A5): colliding names get a numeric suffix. Non-moves
    are recorded without aborting the batch: policy rejections are *refused*,
    move-phase errors are *failed*, jobs that never reach the move (missing
    source, exhausted suffixes) are *skipped*. With *dry_run* no filesystem
    changes occur — records are reported as "planned", and planned names are
    reserved in a virtual in-memory tree so same-basename jobs plan
    cat.jpg, cat-1.jpg, ... without touching disk (FR-A6).

    With *fixture_root*, placement accuracy is computed into
    ``report.fixture_correct``/``report.fixture_total`` by comparing each
    record's placed category against ``read_fixture_labels()`` expectations.
    Records whose source is not under the fixture root are excluded. Only
    moved/planned records can count as correct; refused/failed/skipped never
    do. No floor enforcement lives here — the report carries numbers, tests
    judge (Story 3.5).
    """
    out_root = Path(output_dir)
    report = OrganizeReport()
    reserved: set[Path] = set()

    # Snapshot expectations BEFORE any move: a real run files images OUT of
    # the fixture root (inbox == fixture root), so a post-move rglob would
    # find nothing. Records keep their original source paths for lookup.
    expected: dict[Path, str] = {}
    if fixture_root:
        try:
            expected = read_fixture_labels(fixture_root)
        except OSError:
            expected = {}

    for job in jobs:
        try:
            source = Path(job.source)
        except TypeError as exc:
            # Phase 5: a non-pathlike source must not abort the batch.
            report.records.append(
                MoveRecord(
                    Path("<invalid-source>"),
                    None,
                    "unsorted",
                    0.0,
                    STATUS_SKIPPED,
                    f"invalid source: {exc}",
                )
            )
            logger.warning("Skipped job with invalid source: %s", exc)
            continue
        detail = job.reason or ""
        try:
            category = sanitize_category(job.category, allowed)
        except ValueError as exc:
            report.records.append(
                MoveRecord(
                    source,
                    None,
                    job.category,
                    job.confidence,
                    STATUS_REFUSED,
                    _with_reason(job.reason, str(exc)),
                )
            )
            logger.warning("Refused %s: %s", source.name, exc)
            continue

        if not source.is_file():
            error = f"Source image not found: {source}"
            report.records.append(
                MoveRecord(
                    source, None, category, job.confidence, STATUS_SKIPPED, _with_reason(job.reason, error)
                )
            )
            logger.warning("Skipped %s: %s", source.name, error)
            continue

        try:
            destination = unique_destination(
                out_root / category, source.name, reserved if dry_run else None
            )
        except FileExistsError as exc:
            report.records.append(
                MoveRecord(
                    source, None, category, job.confidence, STATUS_SKIPPED, _with_reason(job.reason, f"error: {exc}")
                )
            )
            logger.warning("Skipped %s: %s", source.name, exc)
            continue

        if dry_run:
            reserved.add(destination)
            report.records.append(
                MoveRecord(source, destination, category, job.confidence, STATUS_PLANNED, detail)
            )
            continue

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
        except OSError as exc:
            report.records.append(
                MoveRecord(
                    source,
                    None,
                    category,
                    job.confidence,
                    STATUS_FAILED,
                    _with_reason(job.reason, f"error: {exc}"),
                )
            )
            logger.warning("Failed to move %s: %s", source.name, exc)
            continue

        report.records.append(
            MoveRecord(source, destination, category, job.confidence, STATUS_MOVED, detail)
        )
        logger.debug("Moved %s -> %s", source, destination)

    if fixture_root:
        correct = 0
        total = 0
        for record in report.records:
            try:
                key = Path(record.source).resolve()
            except OSError:
                continue
            label = expected.get(key)
            if label is None:
                continue  # UNMATCHED_RECORD: not under the fixture root
            total += 1
            if (
                record.category == label
                and record.status in (STATUS_MOVED, STATUS_PLANNED)
            ):
                correct += 1
        report.fixture_correct = correct
        report.fixture_total = total

    return report
