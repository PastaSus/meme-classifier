---
title: 'Story 2.1: Classifier contract and backend selection'
type: 'feature'
created: '2026-10-02'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `ClassificationResult` lacks the AD-10 five-element probability vector + reason fields, and `get_classifier` takes no threshold and raises `ValueError` instead of the documented `BackendUnavailable`.

**Approach:** Extend the ABC contract (probabilities, reason), add `BackendUnavailable`, make `get_classifier(name, threshold=…)` validate against `config.MODEL_BACKENDS` and raise `BackendUnavailable` for unknown names or unimportable TF — no backend bodies touched.

</frozen-after-approval>

## Implementation Notes

- 2026-10-02: `ClassificationResult` gained `reason` (why `unsorted`) and
  `probabilities` (five-element vector over `config.CATEGORIES`), both optional
  so existing constructions keep working; `BackendUnavailable` and
  `PredictFailed` added with distinct meanings (AD-7). `BaseClassifier` now
  takes a constructor `threshold` defaulted from `config.CONFIDENCE_THRESHOLD`;
  both backends forward it via `super().__init__()`. `get_classifier(backend,
  threshold=…)` validates `config.MODEL_BACKENDS` (imported at module top, no
  local import) and raises `BackendUnavailable` — replacing the previous
  `ValueError` — then constructs the backend with the threshold.
- Backend bodies deliberately untouched: `load()`/`predict()` still raise
  `NotImplementedError` and a test pins that, so 2.1 stays contract-only
  (MobileNet body → 2.2, routing → 2.3, custom CNN → 4.2). New TF-free
  `tests/test_backends.py` (13 tests): result defaults/fields, ABC
  conformance, factory threshold plumbing + config allow-list rejection, and
  exception hierarchy.

## Spec Change Log

- None — intent unchanged during implementation.

## Review Triage Log

- 2026-10-02 (step-oneshot inline, no subagent runtime): blind-hunter
  N = min(floor(sqrt(13) + 1), 10) = 4 candidates traced; edge-case enumeration
  over unknown/empty/miscased backend names, threshold defaults, dataclass
  field ordering; verification-gap trace over the 58-test suite. Verdicts:
  - `false` — adding fields to a frozen dataclass breaks positional callers:
    both new fields are keyword-defaulted at the tail, so existing positional
    constructions and `ClassificationResult(image_path, category, confidence,
    backend)` keep working (asserted).
  - `false` — constructor `threshold` breaks subclasses that override
    `__init__`: both backends were updated in the same change and forward via
    `super().__init__()`; factory test asserts `threshold` reaches each.
  - `false` — replacing `ValueError` with `BackendUnavailable` regresses a
    caller: only `cli.run` calls the factory and its handler returns exit 2 for
    both, and argparse already restricts `choices` to `MODEL_BACKENDS`.
  - `low → rejected` — "unimportable TF" cannot be checked in the factory yet:
    TF is touched only inside `load()` (AD-8), so the check lands with the
    backend bodies in 2.2/4.2; the exception type is introduced here.
- Result: no patch, no HALT, one item deferred by design (TF probe → 2.2/4.2).

## Verification

**Commands:**
- `uv run --with pytest pytest -q` -- 58 passed in 0.25s (TF-free, no Keras import)
- `git --no-pager show --stat` -- story diff limited to `classifier.py` + `tests/test_backends.py`
