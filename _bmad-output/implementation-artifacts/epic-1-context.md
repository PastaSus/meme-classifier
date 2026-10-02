# Epic 1 Context: Scan & Validate the Inbox (foundation)

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Establish a reproducible, PRD-conformant foundation: any folder can be scanned with the exact CLI surface, all tunables live in one config module, and only real image files enter the pipeline — so every later epic (classification, organizing, training) builds on identical defaults and a trustworthy scan.

## Stories

- Story 1.1: Provision the uv environment
- Story 1.2: Establish config.py single source of truth
- Story 1.3: Reconcile the CLI surface to PRD §2.1
- Story 1.4: Scan and validate the inbox (FR-A1)

## Requirements & Constraints

- Scan discovers only `.jpg .jpeg .png .gif .bmp .webp` files; all other files are silently ignored and never enter the pipeline.
- Recursion is off by default; `-r` enables nested-subfolder discovery.
- Missing/nonexistent input directory is a loud failure: exit 1 before any writes.
- CLI surface is frozen: positional inbox, `-o/--output` (default `data/organized/`), `-r` (off by default), `--backend` (default `mobilenet`), `--threshold` (default 0.45), `--dry-run`, `--fixture`, `--train`, `--model-path`, `--verbose`. Drift names (`--output-dir`, `--no-recursive` default-on) must be removed.
- `--threshold` accepts only values in (0, 1]; out-of-range values are rejected at parse time.
- Every CLI flag maps to exactly one config value; no env vars, no duplicated literals, no module-level globals outside config.
- Config must declare: five category IDs (`gym-memes`, `cat-memes`, `chaotic-screenshots`, `wholesome-posts`, `unsorted`), six image extensions, threshold default 0.45, backend names (`mobilenet`, `custom-cnn`), default I/O paths, label→category mapping structure, `DEFAULT_MODEL_PATH`, `ACCURACY_FLOOR` / `UNSORTED_SHARE_FLOOR`, fixture default. A test asserts the category and extension sets.
- Environment: Python 3.13 managed project-locally by uv (system interpreter untouched); `pyproject.toml` declares `requires-python = "3.13"` with a committed lockfile; organizer/test path stays green with TensorFlow absent.
- Success: fresh-clone `uv sync`/`uv run` reproduces the env; documented commands work verbatim from `--help`.

## Technical Decisions

- Flat root module layout: all modules live at repo root, no `src/` or `__init__.py` hierarchy; a new root module may be imported by at most one of cli/classifier/organizer.
- Dependency direction is strictly `main → cli → {classifier, organizer} → config`; organizer and classifier never import each other; no upward imports.
- `config.py` is the single source of truth for every tunable listed above; classifier reads the mapping, never re-declares it; there is no on-disk mapping file.
- ML libraries (TensorFlow, NumPy) may appear only in `classifier.py`; `organizer.py`, `cli.py`, and `config.py` stay stdlib-only. Pillow is allowed in classifier and test fixture helpers only.
- Scan lives in the organizer layer; path-existence validation happens in `cli.run` before side effects (argparse owns value-shape validation only).
- New on-disk folders must be justified by an architecture decision before a story creates them; writes are confined to the output tree, `models/`, and the uv/Keras weight cache.
- Every AI prompt is appended verbatim to the append-only log at `<project>/../PROMPTS_LOG.md` (workspace root, not inside the repo) — applies to all build work.

## Cross-Story Dependencies

- Story 1.1 (uv provisioning) unblocks everything: later stories assume the pinned Python 3.13 env and TF-free test path.
- Story 1.2 (config authority) must land before 1.3 and 1.4: flags (1.3) and scan/extensions (1.4) both import defaults from config with no duplicate literals.
- Story 1.3 (CLI surface) precedes 1.4: scan behavior (recursion default, output default) is exercised through the reconciled flags.
- Epic 1 as a whole is the foundation for Epics 2–4 (classifier backends, organizing/reporting, training all consume config values and the scan contract).
