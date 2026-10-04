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

from classifier import BackendUnavailable, get_classifier, train_labeled_model
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
    if report.fixture_total:
        accuracy = report.fixture_accuracy or 0.0
        print(
            f"Fixture accuracy: {report.fixture_correct}/{report.fixture_total} "
            f"({accuracy * 100:.1f}%)"
        )
        print(f"Unsorted share: {report.unsorted_share * 100:.1f}%")
    if report.errors:
        print("  Errors:")
        for record in report.errors:
            print(f"    [{record.status}] {record.source.name}: {record.detail or record.category}")


def _dry_run_without_backend(
    args: argparse.Namespace, paths: list[Path], exc: Exception,
    fixture_root: Path | None = None,
) -> int:
    """Plan every scanned file to unsorted when load() fails under --dry-run.

    FR-A6/AC-A9: a preview survives a broken environment — no backend call, a
    visible warning, everything planned to unsorted, exit 0.
    """
    reason = f"backend unavailable: {exc}"
    print(f"Warning: backend {args.backend!r} unavailable ({exc}) — planning {len(paths)} file(s) to unsorted")
    logger.warning("%s — dry-run fallback to unsorted", reason)
    jobs = [
        OrganizeJob(source=path, category="unsorted", confidence=0.0, reason=reason)
        for path in paths
    ]
    report = organize(jobs, Path(args.output), dry_run=True, fixture_root=fixture_root)
    _print_report(report, True)  # FR-A7
    return 0


def _run_train(args: argparse.Namespace, train_root: Path) -> int:
    """Epic 4 train slot (FR-A9): fit the lab CNN, then return (AD-13).

    Runs before scanning and needs no inbox: input/output/fixture validation
    and the scan/organize loop are skipped — training prints its own summary
    and returns. A missing root exits 1 in every mode (validation precedes
    the dry-run skip); dry-run skips with a warning and zero writes (exit 0);
    TF/model failures exit 2.
    """
    model_path = Path(getattr(args, "model_path", str(DEFAULT_MODEL_PATH)))
    if not train_root.is_dir():
        logger.error("Training root does not exist: %s", train_root.resolve())
        _print_report(empty_report(), args.dry_run)
        return 1
    if args.dry_run:
        print(
            f"Warning: --train {train_root} skipped "
            "(--dry-run requested) — no model written"
        )
        logger.warning("dry-run: skipping training on %s", train_root)
        _print_report(empty_report(), True)
        return 0
    try:
        info = train_labeled_model(train_root, model_path)
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        logger.error("Training data error: %s", exc)
        _print_report(empty_report(), args.dry_run)
        return 1
    except BackendUnavailable as exc:
        logger.error("Training failed: %s", exc)
        _print_report(empty_report(), args.dry_run)
        return 2
    except Exception as exc:  # TF/model failure bucket (AD-8 exit-2 semantics)
        logger.error("Training failed: %s", exc)
        _print_report(empty_report(), args.dry_run)
        return 2
    saved = info["model_path"]
    print(
        f"Training custom-cnn on {info['samples']} image(s) from {train_root} "
        f"(epochs={info['epochs']}, batch={info['batch_size']}, "
        f"image={info['image_size']}x{info['image_size']})"
    )
    print(f"Saved model artifact to {saved}")
    print(
        f"Training complete: {info['samples']} samples across "
        f"{len(info['per_category'])} categories -> {saved}"
    )
    return 0


def run(args: argparse.Namespace) -> int:
    # AD-13 lifecycle: parse → train? → scan → empty-check → load → organize
    # → render. (`parse` lives in main()/argparse; the `train?` slot below
    # belongs to Epic 4.) A report prints before every return below, except
    # the successful train path which prints its own summary (FR-A7/FR-A8).
    train_raw = getattr(args, "train", None)
    if train_raw is not None and str(train_raw) == "":
        # An explicitly-passed empty --train is a missing root, not a
        # normal run: fail loudly instead of training on the CWD (E1).
        logger.error("Training root does not exist: %s", train_raw)
        _print_report(empty_report(), args.dry_run)
        return 1
    if train_raw is not None:
        # Training runs first and needs no inbox: return before any
        # input/output/fixture validation or scanning (FR-A9).
        return _run_train(args, Path(str(train_raw)))

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

    # Story 3.5 (AD-12): validate the explicit fixture root here (exit 1,
    # before side effects) and pass it through to organize(); render-only —
    # accuracy is computed inside organize(), floors judged in tests only.
    # A missing *default* root is silently skipped so plain runs never fail
    # for want of a fixture tree.
    fixture_raw = getattr(args, "fixture", str(DEFAULT_FIXTURE_DIR))
    fixture_root: Path | None = None
    if fixture_raw is not None and str(fixture_raw) != "":
        candidate = Path(str(fixture_raw))
        is_default = candidate == DEFAULT_FIXTURE_DIR
        if candidate.is_dir():
            fixture_root = candidate
        elif is_default:
            fixture_root = None
        else:
            logger.error("Fixture directory does not exist: %s", candidate)
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
        if args.dry_run:
            return _dry_run_without_backend(args, paths, exc, fixture_root)
        _print_report(empty_report(), args.dry_run)
        return 2
    except Exception as exc:  # e.g. TensorFlow missing (NFR-A1)
        logger.error("Failed to initialise backend %r: %s", args.backend, exc)
        if args.dry_run:
            return _dry_run_without_backend(args, paths, exc, fixture_root)
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

    report = organize(jobs, output, dry_run=args.dry_run, fixture_root=fixture_root)  # FR-A4, FR-A6
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
