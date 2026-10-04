---
title: 'Story 3.5: Fixture accuracy and calibrated floors'
type: 'feature'
created: '2026-10-04'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '62aea52'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `--fixture` is a dead flag and no accuracy is ever computed: mapping quality is asserted, not measured, so AC-A6/AC-A7 have no automated proof (FR-A7, AR-13).

**Approach:** Add stdlib `organizer.read_fixture_labels()` (subfolder name = expected label), compute placement accuracy inside `organize()` into new `OrganizeReport` fields when a fixture root is passed, thread `args.fixture` through `cli.run` (validate explicit roots, render only), commit 10 Pillow-generated fixture images (2 per category), and pin the OQ-1 first-pass floors in tests only.

## Boundaries & Constraints

**Always:** `read_fixture_labels()` is stdlib-only; accuracy computed inside `organize()`, never in cli; cli validates explicit fixture roots (exit 1) and renders only, never instantiates the report; floors compared in tests only, never in organizer/cli logic; floor values stay `0.6`/`0.8` (no OQ-1 recalibration); Pillow only in the fixture generator + tests; fixture images committed to the repo.

**Never:** No OQ-1 recalibration or floor changes; no ML imports outside `classifier.py`; no argparse `type=` path validation (exit-2 collision, H9); no fixture logic in `cli.py` beyond pass-through + render; no accuracy enforcement inside organizer/cli (report carries numbers, tests judge).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| FIXTURE_RUN | inbox == fixture root, working backend | report shows `Fixture accuracy: C/M (P%)` + per-category counts | N/A |
| EXPLICIT_BAD_ROOT | `--fixture` points at missing dir | exit 1 with zeroed report, before side effects | `OSError`-style path validation in `run()` |
| DEFAULT_ROOT_MISSING | flag untouched, default dir absent | fixture silently skipped, run proceeds normally | N/A |
| UNMATCHED_RECORD | scanned path not under fixture root | excluded from accuracy, run continues | N/A |
| BACKEND_DOWN_FIXTURE | `--fixture` + `load()` fails, non-dry | exit 2, no accuracy section (3-3 ordering) | existing exit-2 path |

</frozen-after-approval>

## Code Map

- `organizer.py` — add `read_fixture_labels(root)`, `fixture_root` param on `organize()`, accuracy fields on `OrganizeReport`; reuse `MoveRecord`/`counts_by_category()`/`empty_report()`; real-run path unchanged.
- `cli.py` — validate `args.fixture` in `run()` after the output check; pass root to `organize()`; render accuracy section in `_print_report()`; reuse `empty_report()` on the exit-1 path.
- `config.py` — reuse `ACCURACY_FLOOR`/`UNSORTED_SHARE_FLOOR`/`DEFAULT_FIXTURE_DIR` as-is; do not touch values.
- `tests/fixtures/make_labeled.py` — new Pillow generator (allowed by AD-4 amendment); outputs committed under `tests/fixtures/labeled/<category>/`.
- `tests/test_organizer.py`, `tests/test_cli_run.py` — accuracy math, floor asserts with stub backend, exit-1 bad root, default-missing skip.

## Tasks & Acceptance

**Execution:**
- [x] `organizer.py` -- add `read_fixture_labels()` + accuracy in `organize()` -- expectations and placement meet in one module per AD-12
- [x] `cli.py` -- validate/thread/render `--fixture` -- cli stays render-only per spine:115
- [x] `tests/fixtures/make_labeled.py` + `tests/fixtures/labeled/` -- 10 committed images, 2 per category -- AC-A6's Given needs a real tree
- [x] `tests/test_organizer.py` + `tests/test_cli_run.py` -- accuracy/floor/exit-1/default-skip tests -- floors judged in tests only

**Acceptance Criteria:**
- Given `--fixture tests/fixtures/labeled/` (10 images, 2 per category) with a working backend, when the run completes, then the report shows placement accuracy and per-category counts
- Given `config.ACCURACY_FLOOR` (0.6) and `config.UNSORTED_SHARE_FLOOR` (0.8), when a test run asserts them, then the stub-backed fixture run meets both and no floor logic lives in organizer/cli
- Given an explicitly-passed missing fixture root, when the run executes, then exit is 1 with a zeroed report before side effects

## Implementation Notes

## Spec Change Log

## Review Triage Log

- `false` — diff lacks committed fixture binaries: the review diff excluded `*.jpg`; all 10 images exist on disk and in the tree.
- `false` — no `add_argument("--fixture")` in diff: the flag pre-exists as a dead flag; the story threads it through, no parser change needed.
- `false` — no per-category fixture breakdown printed: ACs require accuracy + per-category counts, both rendered (accuracy line + existing `counts_by_category` section).
- `low → patched` — `unsorted_share` computed but never rendered: fixture block now prints the share line, floors test asserts it.
- `false` — labels unfiltered by extension inflate totals: scoring is record-driven (records only exist for scanned images), so stray label entries can never count.
- `false` — default-root detection unnormalized: untouched flag yields the exact default string so the skip path always triggers; explicit spellings correctly validate-or-fail.
- `low → patched` — `getattr` guard beside direct field read: simplified to direct access; every producer returns `OrganizeReport`.
- `false` — `None` vs `0.0` no-data ambiguity: no consumer branches on the distinction; render path guards on `fixture_total`.
- `false` — near-duplicate shade fixtures: colors are human-eyeball aids only; no gate depends on inter-image variance (floors pinned via stub, OQ-1 owns calibration).
- `false` — generator usage lacks Pillow guarantee: Pillow is a declared project dependency, `uv run` provides it.
- `low → patched` — `fixture_root=""` would rglob the CWD: both guards now truthiness checks, empty degrades like `None`.
- `low → patched` — `resolve()` `OSError` lost the whole mapping: per-entry skip now catches `(ValueError, OSError)`.
- `false` — nested fixture files take top-folder label silently: our tree is flat and nothing nests; no reachable harm to guard.
- `false` — vanishing fixture root degrades to no-accuracy: pathological TOCTOU race; crashing instead would be worse, graceful skip stands.
- `false` — committed-tree claim vs missing jpgs in diff: same `*.jpg` exclusion artifact as above; tree verified on disk.
- `medium → patched` — dry-run fallback + matched fixture had zero coverage: added the fallback accuracy test (`Fixture accuracy: 2/10`, exit 0).

## Verification

**Commands:**
- `uv run --with pytest pytest -q` -- expected: full suite green, TF-free
