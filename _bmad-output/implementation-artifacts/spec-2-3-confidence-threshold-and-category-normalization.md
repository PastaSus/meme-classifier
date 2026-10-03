---
title: 'Story 2.3: Confidence threshold and category normalization'
type: 'feature'
created: '2026-10-03'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Below-threshold routing still lives in `cli.run` (`cli.py:179-181`) and `cli.run` never passes `--threshold` to the factory (`cli.py:161` drops `args.threshold`), so the classifier layer owns neither the FR-A3 threshold rule nor category normalization (AR-4, AR-9).

**Approach:** Move both rules into the classifier layer behind one shared routing helper used by every backend: below-threshold → `unsorted` with reason `confidence {actual:.2f} < {threshold:.2f}`, non-member category → `unsorted` with a reason; `cli.run` passes `args.threshold` through `get_classifier(threshold=…)` and uses `result.category` directly with no re-routing. `organizer.sanitize_category` stays untouched as path-traversal defense only.

</frozen-after-approval>

## Implementation Notes

- 2026-10-03: `BaseClassifier.route(category, confidence, raw_label=None)` in
  `classifier.py` owns the single policy (AR-9/AD-10) so the future custom-cnn
  (4.2) inherits it: `None` (unmapped) → `unsorted` + `unmapped label '…'
  regardless of confidence (FR-A2); `confidence < threshold` (strict, preserves
  the old cli `>=` boundary) → `unsorted` + `confidence 0.40 < 0.45` (FR-A3);
  non-member → `unsorted` + `unknown category '…'`; else pass-through.
  `MobileNetV2Classifier.predict` maps top-1 then delegates; its stale
  "threshold stays with the caller" docstring updated. `cli.run` now calls
  `get_classifier(args.backend, threshold=args.threshold)` (AR-4 — the
  previously dropped flag) and files `result.category` verbatim; re-routing
  block deleted. `OrganizeJob` untouched (no reason field — reasons in jobs
  belong to Story 3.2) and `organizer.sanitize_category` untouched (AR-9).
- Tests: `TestThresholdRouting` (6 TF-free cases incl. exact AC reason string,
  inclusive boundary, unmapped-wins-over-low-confidence, custom threshold) in
  `tests/test_backends.py`; `TestThresholdWiring` (factory receives 0.6,
  cli files a raw low-confidence member category as-is proving no re-route,
  layer-routed unsorted filed unsorted) in `tests/test_cli_run.py`.
- Verification: `uv run --with pytest pytest -q` — 75 passed (66 existing + 9
  new), TF present in `.venv` so the 5 real-inference tests ran too.
- Review (blind-hunter, N = min(floor(sqrt(18.34) + 1), 10) = 5 → 10 findings):
  patched 3, rejected the rest — see Review Triage Log. Final suite: 76 passed.

## Review Triage Log

- `low → patched` — reason precedence (threshold vs membership) unpinned: added
  `test_below_threshold_wins_over_unknown_category` pinning the
  unmapped → threshold → membership order.
- `low → patched` — `result.reason` dropped at the cli→organizer boundary with
  no pointer to its future home: added a one-line `TODO(Story 3.2)` in `cli.run`;
  reason-carrying jobs are 3.2's ACs, not this story's.
- `low → patched` — custom-cnn had no documented obligation to call `route()`:
  extended its `predict` TODO to require delegating through
  `BaseClassifier.route` (enforcement lands with the 4.2 body).
- `low → rejected` — `route()` accepts NaN/out-of-range confidence: confidence
  originates from backend inference, not user input; no reachable path produces
  NaN, and input-validation machinery would exceed the ACs.
- `low → rejected` — `threshold` unvalidated for programmatic factory callers:
  the only real callers are the config default and the argparse-validated
  `(0, 1]` flag; guarding direct misuse is not an AC.
- `low → rejected` — no stubbed-model end-to-end test through
  `MobileNetV2.predict` + threshold: `predict` needs numpy/Pillow at call time,
  so such a test could not run in the TF-free QA env without new skip
  machinery; the 3-line delegation is covered by the TF unmapped tests.
- `false` — `route()` rejects e.g. `Cat_Memes` that `sanitize_category` would
  accept: no bug — the layer routing to `unsorted` + reason IS the AR-9
  specified outcome; backends only ever emit exact mapping values.
- `false` — `probabilities` one-hot over post-routing `final` discards
  pre-routing signal: by design, settled in 2.2's triage (AD-10 requires only a
  five-element vector); no 2.3 AC asks for pre-routing mass.
- `false` — threshold reason lacks mapped-category context for Epic 3 audit:
  reason wording is AC-mandated verbatim, and `raw_label`/`confidence` ride
  along on `ClassificationResult` for any 3.2 reporting need.
- `false` — `cli.run` never sanitizes `result.category` before `OrganizeJob`:
  no misfiling possible — `sanitize_category` remains the organizer's
  defense-in-depth by design (unknown → `skipped`, file stays, exit 0).

