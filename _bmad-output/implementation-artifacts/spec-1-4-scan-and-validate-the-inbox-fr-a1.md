---
title: 'Story 1.4: Scan and validate the inbox (FR-A1)'
type: 'feature'
created: '2026-10-02'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `organizer.scan_images` defaults `recursive=True` (PRD: off unless `-r`) and path-existence validation is split between organizer and argparse, so missing-input behavior is not owned in one place before side effects.

**Approach:** Flip `scan_images` default to non-recursive, validate input/output paths in `cli.run` before any side effect (missing inbox → exit 1), and add a TF-free test pinning extension filtering, recursion on/off, and exit-1-before-writes.

</frozen-after-approval>

## Implementation Notes

- 2026-10-02: `scan_images(recursive=False)` default flipped to match PRD 2.1
  (`-r` opts in); docstring records the default. `cli.run()` now owns path
  validation before any filesystem side effect — missing inbox logs
  `Input directory does not exist: <abs>` and returns 1, a non-directory output
  path returns 1 — and the Story 1.3 drift compat shim (`output_dir` /
  `no_recursive` getattr fallbacks) is deleted, so `run()` reads `args.output`
  and `args.recursive` directly. `main()` keeps `NotADirectoryError`/`OSError`
  handlers as a backstop only.
- Tests: `tests/test_organizer.py::TestScanImages` re-pinned to
  `test_recursion_is_off_by_default` + `test_exclude_skips_output_tree` (the
  output tree now lives inside the inbox to prove exclusion); new TF-free
  `tests/test_cli_run.py` covers missing-dir exit 1 with no output tree
  created, non-directory output exit 1, empty-inbox exit 0, and
  `recursive`/`exclude` wiring into `scan_images` via a stubbed scan (no
  classifier constructed).

## Spec Change Log

- None — intent unchanged during implementation.

## Review Triage Log

- 2026-10-02 (step-oneshot inline, no subagent runtime): blind-hunter
  N = min(floor(sqrt(5) + 1), 10) = 3 candidates traced; edge-case enumeration
  over missing/relative paths, non-directory output, empty inbox, nested
  inboxes; verification-gap trace over the 45-test suite. Verdicts:
  - `false` — flipping the `scan_images` default silently changes callers:
    only `cli.run` calls it, and it now passes `args.recursive` explicitly;
    the old default-on assertion was re-pinned to explicit `recursive=True`.
  - `false` — early `return 1` could leave the output tree half-built: the
    check runs before `scan_images`, `get_classifier`, and `organize`, so no
    directory is created (asserted in test).
  - `false` — dropping the compat shim breaks external callers: shim was
    documented as Story 1.4 cleanup; `tests/test_cli_surface.py` asserts the
    drift names are gone from the parser, so nothing can supply them.
- Result: no patch, no HALT, nothing deferred.

## Verification

**Commands:**
- `uv run --with pytest pytest -q` -- 45 passed in 0.20s (TF-free, no Keras import)
- `uv run python main.py /nope --dry-run; echo EXIT:$?` -- exit 1, no writes
- `uv run python main.py data/inbox --dry-run; echo EXIT:$?` -- exit 0, "No images found"
