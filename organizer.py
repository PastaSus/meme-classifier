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
    cleaned = re.sub(r"[\s_]+", "-", category.strip().lower())
    cleaned = re.sub(r"[^a-z0-9-]", "", cleaned)
    if not cleaned or cleaned in {".", ".."} or cleaned not in allowed_set:
        raise ValueError(f"Category not allowed: {category!r}")
    return cleaned


def unique_destination(directory: Path, filename: str) -> Path:
    """Return a non-colliding destination path (FR-A5): file.jpg, file-1.jpg, ..."""
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    for index in range(1, MAX_COLLISION_SUFFIX + 1):
        alternative = directory / f"{stem}-{index}{suffix}"
        if not alternative.exists():
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
) -> OrganizeReport:
    """Move classified images into labelled subfolders (FR-A4, FR-A6).

    Never overwrites (FR-A5): colliding names get a numeric suffix. Non-moves
    are recorded without aborting the batch: policy rejections are *refused*,
    move-phase errors are *failed*, jobs that never reach the move (missing
    source, exhausted suffixes) are *skipped*. With *dry_run* no filesystem
    changes occur — records are reported as "planned".
    """
    out_root = Path(output_dir)
    report = OrganizeReport()

    for job in jobs:
        source = Path(job.source)
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
            destination = unique_destination(out_root / category, source.name)
        except FileExistsError as exc:
            report.records.append(
                MoveRecord(
                    source, None, category, job.confidence, STATUS_SKIPPED, _with_reason(job.reason, f"error: {exc}")
                )
            )
            logger.warning("Skipped %s: %s", source.name, exc)
            continue

        if dry_run:
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

    return report
