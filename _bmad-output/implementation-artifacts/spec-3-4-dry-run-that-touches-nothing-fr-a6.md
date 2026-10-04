---
title: 'Story 3.4: Dry-run that touches nothing (FR-A6)'
type: 'feature'
created: '2026-10-04'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `cli.run` treats a `load()` failure identically under `--dry-run` and real runs (exit 2), so a preview cannot survive a broken environment; and `organizer` plans duplicate destinations when two dry-run jobs share a basename because `unique_destination()` probes only the real filesystem (deferred from spec-3-1).

**Approach:** On `load()` failure under `--dry-run`, skip the backend entirely (zero cache-priming) and plan every scanned file to `unsorted` with a visible warning, rendering the report and exiting 0 — while non-dry keeps exit 2 with no partial moves; in `organizer.organize`, reserve planned destinations in a virtual in-memory set so same-basename jobs plan `cat.jpg`, `cat-1.jpg`, … with zero mkdir/move writes.

</frozen-after-approval>

## Implementation Notes

- 2026-10-04: `cli.run` load-failure branches now check `args.dry_run`
  first: under `--dry-run` they delegate to `_dry_run_without_backend()`,
  which warns (stdout + log), synthesizes one zero-confidence `unsorted`
  job per scanned path (scan runs before load, so paths exist), organizes
  dry, renders, and returns 0. Non-dry keeps exit 2 with `organize`
  uncalled (3-3 pin intact).
- 2026-10-04: `organizer.unique_destination()` takes optional
  `reserved: Collection[Path]`; `organize()` keeps a dry-run-only
  reservation set, so same-basename dry jobs plan `cat.jpg`, `cat-1.jpg`.
  Real-run path passes `None` — FS probes unchanged (a failed real move
  must not poison later names). Consumes the deferred-work basename
  item from spec-3-1.
- 2026-10-04: Deliberate scope call — dry-run with a *working* backend
  still classifies (load+predict) per PRD FR-A6/AC-A1 ("the folder is
  untouched" = inbox/output trees); only the backend-down path skips
  `load()`. A cold Keras cache would fetch weights to `~/.keras` outside
  the repo on first use — TF-inherent, not tool disk writes.
- 2026-10-04: Tests — `TestOrganize.
  test_dry_run_shared_basename_plans_suffixed_names` (organizer) and
  parametrized `test_backend_down_dry_run_plans_unsorted_and_exits_0`
  (`BackendUnavailable` + `NotImplementedError`, cli). `uv run --with
  pytest pytest -q` — 103 passed (100 pre-existing + 3 new). Manual
  TF-free `main.py --dry-run` prints the warning, plans 2 unsorted,
  exit 0, no output tree created.

## Review Triage Log

- `low → patched` — stdout warning omitted the backend id: now prints
  `backend 'mobilenet' unavailable (...)`.
- `low → patched` — no test proving fallback + reservation compose: added
  `test_backend_down_dry_run_reserves_against_files_on_disk` (same
  basename ×2 with `unsorted/cat.jpg` on disk plans `cat-1/cat-2`,
  exit 0, disk unchanged) — covers the on-disk-mix case too.
- `false` — duplicated `if args.dry_run` in both except branches: the
  shared logic lives in the helper; the two-line dispatch preserves the
  intentional distinct diagnostics (3-3 precedent).
- `false` — helper docstring "no backend call" unscoped: first sentence
  already scopes it to "when load() fails under --dry-run".
- `false` — cross-category reservation leak: the set holds full paths,
  so different parent dirs can never compare equal.
- `false` — unnormalized Path equality: the set is function-local and
  every entry derives from the same `out_root`, one form per call.
- `false` — fallback relies on the default allow-list for `unsorted`:
  same contract as the normal `organize` call one line below;
  special-casing would diverge, not harden.
