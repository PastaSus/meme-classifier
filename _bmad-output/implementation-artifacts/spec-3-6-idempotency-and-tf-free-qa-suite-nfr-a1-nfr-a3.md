---
title: 'Story 3.6: Idempotency and TF-free QA suite (NFR-A1, NFR-A3)'
type: 'feature'
created: '2026-10-04'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Epic 1–3 guarantees lack end-to-end proof: no test re-runs the CLI against a populated output tree (AC-A10 byte-identical + restored-collision refiling), AC-A1 has no 10-file dry-run test, AC-A4's corrupt path is pinned dry-run-only, and AC-A5 has no named TF-free pin.

**Approach:** Add five CLI-level tests with stub backends (TF-free, deterministic) — empty re-run byte-identical, restored collisions refile with suffixes, 10-file dry-run untouched, corrupt real-run to unsorted with reason, and a no-tensorflow-import pin; no production code change expected, real-backend accuracy stays OQ-1 calibration (infeasible on synthetic fixtures by construction).

</frozen-after-approval>

## Implementation Notes

- 2026-10-04: Tests-only story — no production code changed. New
  `TestIdempotency` in `tests/test_cli_run.py` plus helpers
  `_snapshot_tree`/`_FixedCategoryBackend`: empty re-run byte-identical,
  restored-copy refiles with suffix (no overwrite), 10-file dry-run
  untouched, corrupt real-run to unsorted with reason, cli stdlib-only
  AST pin.
- 2026-10-04: Surprise 1 — first draft of the restore test *moved* the
  filed file back, so no collision occurred and the test failed
  correctly; fixed to restore a copy, which is the true colliding case.
- 2026-10-04: Surprise 2 — a `sys.modules` TF-absence assert passed
  alone but failed in-suite: TF 2.21 is installed in the uv env and
  `test_backends` imports it, so the assert was order-dependent. Replaced
  with an order-independent AST stdlib-only pin mirroring the organizer
  one. Real-backend accuracy stays OQ-1 (infeasible on synthetic
  fixtures); floors remain stub-proven per 3-5.
- 2026-10-04: Verification: `uv run --with pytest pytest -q` —
  129 passed (124 pre-existing + 5 new).

## Review Triage Log

- `false` — snapshot blind to dirs/mtimes and raises on missing root: the re-run path performs zero FS ops before the snapshot point, so file bytes capture everything mutable; the raise is a loud failure, preferable to a silent `{}`.
- `low → rejected` — rerun test omits drain/placement/zero asserts: "No images found" implies the drained inbox and the zeroed report is pinned by 3-3 unit tests; placement location is irrelevant to byte-identity.
- `false` — identical-bytes restore hides overwrite: an overwrite would leave one file and fail the `cat-1.jpg` assert; count proves non-overwrite, bytes prove preservation.
- `false` — dry-run test is fresh-out-only and count-unchecked: dict equality pins count; pre-existing-out dry-runs are pinned by 3-4's reserves test.
- `false` — corrupt triggered by filename, attachment unasserted: filename dispatch is the only TF-free simulation; the reason string reaches stdout only via report rendering, proving record attachment (logger goes to stderr).
- `low → rejected` — no transitive/subprocess TF check: a top-level TF import anywhere in the chain fails the whole TF-free suite at collection — self-announcing; harness disproportionate.
- `low → rejected` — stub duplication and hardcoded threshold default: matches the file's established convention; dedup refactor risk outweighs developer-only friction.
