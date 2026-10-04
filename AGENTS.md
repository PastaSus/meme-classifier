<!-- bmad:context -->
<!-- Verified 2026-09-27 against 5bee309. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## meme-classifier

University case-study CLI: scans a folder of images, classifies meme/reaction pictures into 5 categories, sorts them into `data/organized/<category>/`. Python 3.14 flat modules at the repo root; organizer is stdlib-only, ML backends optional (TensorFlow). Planning lives in `docs/`; BMad workflow artifacts go to `_bmad-output/`.

## Policy

- Log every AI prompt verbatim in `../PROMPTS_LOG.md` — append-only, never rewrite or delete entries (course requirement).
- Story branches are `feature/<story-key>-<slug>` (e.g. `feature/1-1-provision-the-uv-environment`); commits are atomic Conventional Commits (`type(scope): subject`).

## Where things are

- Requirements/design: `docs/product-requirements.md`, `docs/system-architecture.md`, `docs/bmad-plan.md` — read the PRD before changing behavior.
- Entry point: `main.py` → `cli.py` → `classifier.py`/`organizer.py` → `config.py`.

## Running and verifying

- Never run bare `python` — it's a broken Windows Store stub; use `py` (3.14.6) or `uv`.
- Tests: `uv run --with pytest pytest -q` (158 tests, ~15s).
- `py main.py data/inbox --dry-run` works without TensorFlow installed.

## Conventions that differ from defaults

- Flat root modules, snake_case files in kebab-case folders — don't introduce a package or `src/` layout; `conftest.py` exists to make pytest imports work.
- `organizer.py` stays stdlib-only, no ML imports — QA must run without TensorFlow (NFR-A1).
- Dependency direction `main → cli → {classifier, organizer} → config` — never import upward.

## Known pitfalls

- README's `python -m pytest -q` fails (pytest not installed in the `py` env) — use `uv run --with pytest pytest -q`.
- Both `classifier.py` backends are implemented (`mobilenet` zero-shot; `custom-cnn` via `--train`-built `--model-path` artifact) — end-to-end classification works with TensorFlow installed; without it, non-dry runs exit 2 and `--dry-run` plans everything to `unsorted`.

<!-- /bmad:context -->
