---
title: 'Story 3.2: Report contract with reasons (FR-A7)'
type: 'feature'
created: '2026-10-03'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The report cannot carry reasons end to end: `OrganizeJob` has no `reason` field so cli's corrupt-image conversion logs the failure instead of reporting it (AC-A4), only `skipped` exists so refused/failed cannot be counted separately (FR-A7/AR-7), `counts_by_category` excludes just one bucket, and the empty-inbox path renders no report.

**Approach:** Add `reason` to `OrganizeJob` (organizer defines, cli fills) and propagate it into `MoveRecord.detail`; split non-moves into `refused` (allow-list/policy rejection), `failed` (move-phase `OSError`), `skipped` (never attempted: missing source, suffix exhaustion); `counts_by_category` excludes all three, the report gains `refused`/`failed` counters plus an `errors` view, the printed summary lists each error with its reason, and cli renders `organizer.empty_report()` on the empty-inbox exit. Exit codes and lifecycle ordering stay untouched for 3.3, dry-run semantics for 3.4, accuracy for 3.5.

</frozen-after-approval>

## Implementation Notes

- 2026-10-03: taxonomy decision (artifacts leave refused/failed split undefined):
  `refused` = allow-list/policy rejection (`sanitize_category` ValueError);
  `failed` = move-phase `OSError` (missing source stays `skipped` — never
  attempted — as do exhausted suffixes per the pinned 3-1 AC). `organizer.py`:
  `STATUS_REFUSED`/`STATUS_FAILED`, `OrganizeJob.reason` (organizer defines,
  cli fills), `MoveRecord.detail` seeded from `job.reason` with stage errors
  appended (`_with_reason`, lossless), `counts_by_category` excludes every
  non-move, new `refused`/`failed` counters + `errors` view + `empty_report()`.
  `organize()` restructured into sequential stages (sanitize → source check →
  destination → dry-run → move) so each outcome maps to exactly one status.
  `cli.py`: corrupt path fills `reason=str(exc)` and continues; success path
  forwards `result.reason` so filed unsorted stays explainable; empty inbox
  renders `organizer.empty_report()`; `_print_report` shows detail on any
  record plus refused/failed counters and an `Errors:` section with reasons.
  Exit codes untouched (3.3 owns lifecycle).
- Caught during verification: a mid-class module-level insertion silently nested
  three 3-1 tests inside the new function (collected 85, not 88 — pytest does
  not warn). Fixed by moving the module-level test to end of file; suite now
  collects the full 88. Lesson: always reconcile collected count vs expectation.
- Tests: `test_organizer.py` — disallowed→refused rewrite, mixed-batch counts
  update, new non-moves-excluded, move-error-is-failed (monkeypatched
  `shutil.move`), job-reason-into-detail, errors-view, empty-report-zeroed;
  `test_cli_run.py` — new `TestReportWiring` (corrupt→unsorted+reason in
  stdout report with run continuing; empty inbox renders both lines).
- Verification: `uv run --with pytest pytest -q` — 88 passed (count reconciled
  after fixing a silent test-swallowing nesting slip; see notes).
- Review (blind-hunter, N = min(floor(sqrt(17.06) + 1), 10) = 5 → 7 findings):
  patched 2, confirmed 1 already deferred, rejected the rest — see Review
  Triage Log. Final suite still 88 passed.

## Review Triage Log

- `low → patched` — empty-inbox exit rendered no counters, only "Nothing to
  organize.": `_print_report` now always prints the `Summary:` block (zeroed
  for empty reports); empty-inbox test asserts the zeroed counter line.
- `low → patched` — module/class docs never defined refused/failed/skipped or
  the reason flow: `organizer.py` module docstring now documents the taxonomy
  and the `reason → detail` rule (`organize()` docstring already did).
- `defer (already recorded)` — dry-run duplicate planned destinations for
  same-basename jobs: identical to the `deferred-work.md` entry filed during
  3-1 review; no new entry (preview contract is 3.4's).
- `false` — `errors` may include empty-`detail` records masked by the
  `or category` fallback: unreachable — every non-move path sets non-empty
  detail (pinned by `test_errors_view_carries_reasons` asserting `all(detail)`).
- `low → rejected` — narrow `except` clauses could abort the batch on exotic
  errors / misreport permission failures: `Path.exists`/`is_file` return
  `False` (never raise) on permission errors, and non-`OSError` from
  `shutil.move` is outside stdlib's contract; a broad `except` would be the
  worse fix.
- `false` — no planned-vs-moved per-category split, no errors total, no
  accuracy section: `dry_run` is run-global so one run never mixes planned and
  moved (the merged dict IS that run's counts); accuracy sections are 3.5's
  ACs, not 3-2's.
- `low → rejected` — `reason=str(exc)` drops the exception type, newlines
  unnormalized, `""` ≡ `None`: all classifier messages are single-line by
  construction, the type prefix adds noise, and empty-reason-means-absent is
  intended.

