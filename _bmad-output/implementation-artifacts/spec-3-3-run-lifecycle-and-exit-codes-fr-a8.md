---
title: 'Story 3.3: Run lifecycle and exit codes (FR-A8)'
type: 'feature'
created: '2026-10-03'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `cli.run` has no pinned lifecycle or report guarantee: missing-dir and output-is-file exits return 1 with no report, `load()` failures return 2 with no report, the `train?` slot is absent, and no test pins the parse → train? → scan → empty-check → load → organize → render order (AD-13, FR-A8).

**Approach:** Fix the lifecycle in `cli.run` only — validate paths (exit 1) before side effects, scan, empty-check rendering `organizer.empty_report()`, `load()` owning all model I/O (exit 2 on failure, non-dry, with no partial moves), then organize → render with a report printed before every return (exit 0 including skips/refusals/failures); reserve the `train?` slot for Epic 4 with zero behavior change.

</frozen-after-approval>

## Implementation Notes

- 2026-10-03: `cli.run` now carries the AD-13 lifecycle comment
  (parse → train? → scan → empty-check → load → organize → render) and
  renders `organizer.empty_report()` before every error return: missing
  input dir and output-is-file (exit 1), both `load()` failure branches
  (exit 2). `main()`'s `NotADirectoryError`/`OSError` handlers render it
  too. The `train?` slot is a reserved comment only — `--train` semantics
  belong to Epic 4, zero behavior change here.
- Deliberately unpinned: dry-run backend-down behavior (Story 3.4 owns the
  unsorted-fallback, exit 0). Current code exits 2 for dry and non-dry alike;
  3-3 tests pin only the non-dry exit-2 case so 3-4 has no manufactured
  failing test to delete.
- Load-failure renders the zeroed report by construction: jobs are built
  post-`load()`, so there is nothing to attach a per-file reason to; the
  exception text stays in the stderr log line.
- Consistency fix in the touched render path: the empty-inbox line now
  prints `args.input_dir` (raw string) like the non-empty `Scanned ...`
  line instead of the resolved `Path`.
- Tests: new `TestLifecycleAndExitCodes` in `tests/test_cli_run.py` —
  call-order pin (scan → load → organize → render), empty-inbox skips
  load/organize, exit-1 paths print zeroed reports without side effects,
  parametrized exit-2 (BackendUnavailable + NotImplementedError) with
  no-partial-moves asserts, parametrized non-moves (failed/skipped/refused)
  still exit 0 with reasons rendered, `main()` handler coverage.
- Verification: `uv run --with pytest pytest -q` — 100 passed
  (88 pre-existing + 12 new).

## Review Triage Log

- `low → patched` — module docstring still showed the old
  `scan -> classify -> organize -> report` flow: now states the AD-13
  lifecycle with report-before-every-return.
- `low → rejected` — `run()` never reads `args.train`, no no-op/test:
  the AD-13 comment explicitly reserves the slot for Epic 4; pinning
  no-op behavior now would manufacture a test Epic 4 must break.
- `low → rejected` — load-failure renders a zeroed report with the reason
  only in stderr: jobs are built post-`load()` so no per-file record can
  exist; ACs require the report plus exit 2, both satisfied.
- `patched` — `main()` error handlers had no report test: added a
  parametrized `NotADirectoryError`/`OSError` test asserting exit 1 plus
  the zeroed report.
- `patched` — only `failed` pinned exit 0: parametrized over
  failed/skipped/refused with reason-rendering asserts.
- `rejected (deferral documented)` — dry-run backend-down unpinned while
  code exits 2 for dry too: pinning exit-2-dry would bake in behavior
  Story 3-4 must delete; non-dry exit 2 is pinned instead.
- `patched` — input-as-file path and output-blocker side effects
  unasserted: added input-is-file exit-1 test and blocker-unchanged /
  no-new-tree asserts on the output-is-file test.
- `low → rejected` — non-`OSError` from scan/organize bubbles without a
  report: all reachable raises are `OSError` subclasses handled (with
  report) in `main()`; a broad `except` would mask bugs (3-2 precedent).
- `false` — spec has empty notes and no acceptance section: oneshot
  format carries Intent only at plan time (same shape as 3-1/3-2); notes
  filled at finalize.
- `low → patched` — empty-path message interpolated the resolved `Path`
  while the non-empty path used the raw string: now both use
  `args.input_dir`; existing substring asserts unaffected.
