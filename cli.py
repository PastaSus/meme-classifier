"""Command-line interface and orchestration for the Meme & Reaction Image Organizer.

Lifecycle (AD-13): parse -> train? -> scan -> empty-check -> load -> organize
-> render, with a report printed before every return.
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from classifier import get_classifier
from config import (
    CONFIDENCE_THRESHOLD,
    DEFAULT_BACKEND,
    DEFAULT_FIXTURE_DIR,
    DEFAULT_INPUT_DIR,
    DEFAULT_MODEL_PATH,
    DEFAULT_OUTPUT_DIR,
    MODEL_BACKENDS,
)
from organizer import OrganizeJob, OrganizeReport, empty_report, organize, scan_images

logger = logging.getLogger("meme-organizer")


def _threshold(value: str) -> float:
    """Argparse value-shape validation for --threshold: must be in (0, 1].

    Path existence stays in cli.run (exit 1); this owns shape only (AD-8).
    argparse failures exit 2 per its default (AD-8 usage-error semantics).
    """
    try:
        parsed = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"threshold must be in (0, 1], got {value!r}")
    if not 0 < parsed <= 1:
        raise argparse.ArgumentTypeError(f"threshold must be in (0, 1], got {value!r}")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="meme-organizer",
        description=(
            "Classify meme & reaction images (gym memes, cat memes, chaotic "
            "screenshots, wholesome posts) and file them into labelled folders."
        ),
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        type=str,
        default=str(DEFAULT_INPUT_DIR),
        help=f"folder of unorganized images (default: {DEFAULT_INPUT_DIR})",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"root folder for category subfolders (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "-b",
        "--backend",
        choices=MODEL_BACKENDS,
        default=DEFAULT_BACKEND,
        help="classification backend (default: %(default)s)",
    )
    parser.add_argument(
        "-t",
        "--threshold",
        type=_threshold,
        default=CONFIDENCE_THRESHOLD,
        help="confidence below which images go to 'unsorted' (default: %(default)s)",
    )
    parser.add_argument(
        "--fixture",
        type=str,
        default=str(DEFAULT_FIXTURE_DIR),
        help=f"labelled fixture root for accuracy checks (default: {DEFAULT_FIXTURE_DIR})",
    )
    parser.add_argument(
        "--train",
        type=str,
        default=None,
        help="train the custom CNN on a labeled folder tree before organizing",
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=str(DEFAULT_MODEL_PATH),
        help=f"custom-cnn artifact path (default: {DEFAULT_MODEL_PATH})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print planned moves without touching the filesystem (FR-A6)",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="scan nested subfolders (default: top level only)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="debug-level logging",
    )
    return parser


def _print_report(report: OrganizeReport, dry_run: bool) -> None:
    if report.records:
        verb = "Planned moves" if dry_run else "Moved files"
        print(f"\n{verb}:")
        width = max(len(r.source.name) for r in report.records)
        for record in report.records:
            dest = record.destination or "-"
            confidence = f"{record.confidence * 100:5.1f}%"
            line = f"  [{record.status:<7}] {record.category:<18} {confidence}  {record.source.name:<{width}} -> {dest}"
            if record.detail:
                line += f"  ({record.detail})"
            print(line)
    else:
        # Empty reports still get their zeroed counters below (FR-A7: a
        # summary prints after every run, including empty inputs).
        print("Nothing to organize.")

    print("\nSummary:")
    print(
        f"  planned: {report.planned} | moved: {report.moved} | "
        f"skipped: {report.skipped} | refused: {report.refused} | failed: {report.failed}"
    )
    for category, count in report.counts_by_category().items():
        print(f"    {category}: {count}")
    if report.errors:
        print("  Errors:")
        for record in report.errors:
            print(f"    [{record.status}] {record.source.name}: {record.detail or record.category}")


def run(args: argparse.Namespace) -> int:
    # AD-13 lifecycle: parse → train? → scan → empty-check → load → organize
    # → render. (`parse` lives in main()/argparse; the `train?` slot belongs
    # to Epic 4 and is reserved here with no behavior yet.) A report prints
    # before every return below (FR-A7/FR-A8).
    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        logger.error("Input directory does not exist: %s", input_dir.resolve())
        _print_report(empty_report(), args.dry_run)
        return 1

    output = Path(args.output)
    if output.exists() and not output.is_dir():
        logger.error("Output path is not a directory: %s", output.resolve())
        _print_report(empty_report(), args.dry_run)
        return 1

    paths = scan_images(input_dir, recursive=args.recursive, exclude=output)
    if not paths:
        print(f"No images found in {args.input_dir}")
        _print_report(empty_report(), args.dry_run)  # AR-7: organizer owns it
        return 0

    print(f"Scanned {len(paths)} image(s) from {args.input_dir}")
    print(f"Backend: {args.backend} | threshold: {args.threshold:.2f} | dry-run: {args.dry_run}")

    try:
        classifier = get_classifier(args.backend, threshold=args.threshold).load()
    except NotImplementedError as exc:
        logger.error("%s", exc)
        logger.error("Backend not implemented yet — BMAD Dev phase pending.")
        _print_report(empty_report(), args.dry_run)
        return 2
    except Exception as exc:  # e.g. TensorFlow missing (NFR-A1)
        logger.error("Failed to initialise backend %r: %s", args.backend, exc)
        _print_report(empty_report(), args.dry_run)
        return 2

    jobs: list[OrganizeJob] = []
    for path in paths:
        try:
            result = classifier.predict(path)
        except Exception as exc:
            # AD-7: convert to a reason-carrying unsorted job and continue —
            # the reason must reach the report, never live only in the log.
            logger.warning("Classification failed for %s (%s) -> unsorted", path.name, exc)
            jobs.append(
                OrganizeJob(
                    source=path, category="unsorted", confidence=0.0, reason=str(exc)
                )
            )
            continue

        # FR-A3 lives in the classifier layer now (Story 2.3, AR-4): cli
        # trusts result.category and never re-routes. The layer's reason rides
        # along so successfully filed unsorted images stay explainable (FR-A7).
        jobs.append(
            OrganizeJob(
                source=path,
                category=result.category,
                confidence=result.confidence,
                reason=result.reason,
            )
        )

    report = organize(jobs, output, dry_run=args.dry_run)  # FR-A4, FR-A6
    _print_report(report, args.dry_run)  # FR-A7
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        return run(args)
    except NotADirectoryError as exc:
        logger.error("%s", exc)
        _print_report(empty_report(), args.dry_run)
        return 1
    except OSError as exc:
        logger.error("Filesystem error: %s", exc)
        _print_report(empty_report(), args.dry_run)
        return 1


if __name__ == "__main__":
    sys.exit(main())
