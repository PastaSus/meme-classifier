"""Command-line interface and orchestration for the Meme & Reaction Image Organizer.

Flow (docs/system-architecture.md 2.2): scan -> classify -> organize -> report.
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence

from classifier import get_classifier
from config import (
    CONFIDENCE_THRESHOLD,
    DEFAULT_BACKEND,
    DEFAULT_INPUT_DIR,
    DEFAULT_OUTPUT_DIR,
    MODEL_BACKENDS,
)
from organizer import OrganizeJob, OrganizeReport, organize, scan_images

logger = logging.getLogger("meme-organizer")


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
        "--output-dir",
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
        type=float,
        default=CONFIDENCE_THRESHOLD,
        help="confidence below which images go to 'unsorted' (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print planned moves without touching the filesystem (FR-A6)",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="only scan the top level of input_dir",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="debug-level logging",
    )
    return parser


def _print_report(report: OrganizeReport, dry_run: bool) -> None:
    if not report.records:
        print("Nothing to organize.")
        return

    verb = "Planned moves" if dry_run else "Moved files"
    print(f"\n{verb}:")
    width = max(len(r.source.name) for r in report.records)
    for record in report.records:
        dest = record.destination or "-"
        confidence = f"{record.confidence * 100:5.1f}%"
        line = f"  [{record.status:<7}] {record.category:<18} {confidence}  {record.source.name:<{width}} -> {dest}"
        if record.detail and record.status == "skipped":
            line += f"  ({record.detail})"
        print(line)

    print("\nSummary:")
    print(f"  planned: {report.planned} | moved: {report.moved} | skipped: {report.skipped}")
    for category, count in report.counts_by_category().items():
        print(f"    {category}: {count}")


def run(args: argparse.Namespace) -> int:
    paths = scan_images(
        args.input_dir,
        recursive=not args.no_recursive,
        exclude=args.output_dir,
    )
    if not paths:
        print(f"No images found in {args.input_dir}")
        return 0

    print(f"Scanned {len(paths)} image(s) from {args.input_dir}")
    print(f"Backend: {args.backend} | threshold: {args.threshold:.2f} | dry-run: {args.dry_run}")

    try:
        classifier = get_classifier(args.backend).load()
    except NotImplementedError as exc:
        logger.error("%s", exc)
        logger.error("Backend not implemented yet — BMAD Dev phase pending.")
        return 2
    except Exception as exc:  # e.g. TensorFlow missing (NFR-A1)
        logger.error("Failed to initialise backend %r: %s", args.backend, exc)
        return 2

    jobs: list[OrganizeJob] = []
    for path in paths:
        try:
            result = classifier.predict(path)
        except Exception as exc:
            logger.warning("Classification failed for %s (%s) -> unsorted", path.name, exc)
            jobs.append(OrganizeJob(source=path, category="unsorted", confidence=0.0))
            continue

        category = (
            result.category if result.confidence >= args.threshold else "unsorted"
        )  # FR-A3
        jobs.append(
            OrganizeJob(source=path, category=category, confidence=result.confidence)
        )

    report = organize(jobs, args.output_dir, dry_run=args.dry_run)  # FR-A4, FR-A6
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
        return 1
    except OSError as exc:
        logger.error("Filesystem error: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
