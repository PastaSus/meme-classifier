---
title: 'Story 2.2: MobileNetV2 backend with shipped mapping'
type: 'feature'
created: '2026-10-02'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `MobileNetV2Classifier.load()`/`predict()` still raise `NotImplementedError`, so no image can be classified (FR-A2).

**Approach:** Implement `load()` as the single weight-fetch point (AD-8) and `predict()` as preprocess → top-1 → `IMAGENET_LABEL_TO_CATEGORY` → result, routing unmapped labels to `unsorted` with a reason; failures surface as `BackendUnavailable`/`PredictFailed`.

</frozen-after-approval>

## Implementation Notes

- 2026-10-02: `load()` imports `tensorflow.keras` inside the method and builds
  `keras.applications.MobileNetV2(weights=self.weights)` plus the
  `preprocess_input`/`decode_predictions` helpers, wrapping both the import and
  the build in `BackendUnavailable` — the only weight fetch in the module
  (AD-8), so importing `classifier` never needs TF. `predict()` guards on the
  unloaded state first (AD-7 `PredictFailed("mobilenet backend not loaded…")`)
  before importing numpy/Pillow, resizes to 224×224 RGB, runs
  `model.predict(verbose=0)`, decodes top-1, lower-cases the label, and looks it
  up in the shipped mapping: mapped → that category with `reason=None`, unmapped
  → `unsorted` with `reason="unmapped label '…'"`. Image-open/inference errors
  become `PredictFailed`, and `probabilities` is the five-element one-hot over
  `config.CATEGORIES` (AD-10). The module docstring now states mobilenet is
  implemented while custom-cnn stays a stub.
- Threshold routing intentionally untouched: `model-docstring`/notes record that
  below-threshold → `unsorted` still happens in `cli.run` and moves into the
  classifier layer in Story 2.3; Story 2.2's tests therefore assert only
  mapped-or-unmapped behaviour. Test slice: `TestMobileNetFailurePaths`
  (TF-free) and `TestMobileNetV2TF` behind a `needs_tf` skip with a module-scope
  `mobilenet` fixture (one real load per run). The 2.1 test
  `test_backend_bodies_are_still_stubs` was narrowed to
  `test_custom_cnn_body_is_still_a_stub` since the mobilenet body is no longer a
  stub.

## Spec Change Log

- None — intent unchanged during implementation. (Two deltas vs. the design
  note, both in-scope: the unloaded-state guard sits before the numpy/Pillow
  imports so the TF-free path raises `PredictFailed` even without numpy, and the
  class-scope fixture was made module-scope to clear a
  `PytestRemovedIn10Warning`.)

## Review Triage Log

- 2026-10-02 (step-oneshot inline, no subagent runtime): blind-hunter
  N = min(floor(sqrt(21) + 1), 10) = 5 candidates traced; edge-case enumeration
  over unloaded/loaded backend, corrupt file, missing file, unmapped label;
  verification-gap trace over both interpreter environments. Verdicts:
  - `false` — downloading ImageNet weights on every test run: the module-scope
    fixture loads once per module and Keras caches weights in `~/.keras`;
    measured 4.4–5.4s warm.
  - `false` — a TF-free test suite silently losing coverage: `needs_tf` skips
    only the five inference tests; every failure path (unloaded predict, unknown
    backend, TF-absent `load()`) is asserted TF-free.
  - `false` — `verbose=0` unavailable on older Keras: `tensorflow>=2.21,<2.22`
    is pinned in `pyproject.toml`, where the argument is supported.
  - `false` — 224×224 hard-coding ignoring `img.convert("RGB")` metadata:
    MobileNetV2's fixed input size is the documented contract for this backend.
  - `low → rejected` — `predict()` returning a one-hot `probabilities` vector is
    not a true ImageNet distribution: AD-10 only requires a five-element vector
    over `config.CATEGORIES`; real per-category scores are not derivable from a
    top-1 decode without the full 1000-class output and are out of scope here.
- Result: no patch, no HALT, one item deferred by design (true distribution →
  not required by AD-10).

## Verification

**Commands:**
- `uv run --with pytest pytest -q -rw` -- 66 passed in 15.41s, 0 warnings
  (TF present in `.venv`; includes 5 real MobileNetV2 inference tests)
- `py _tf_free_check.tmp.py` (system 3.14.6: no TF, no numpy, no Pillow;
  throwaway script, deleted after the run) -- `imports ok (no TF): False`
  (i.e. tensorflow not in `sys.modules`), `factory: MobileNetV2Classifier
  threshold: 0.7`, `unknown backend rejected: Unknown backend 'resnet'…`,
  `unloaded predict: mobilenet backend not loaded (call load() first)`,
  `load without TF: TensorFlow unavailable: No module named 'tensorflow'`,
  `categories: 5 mapping labels: 13 scan ok: True` — NFR-A1 holds.
- Limitation: the system `py` interpreter has no pytest, so the TF-free
  assertions above are a script, not the suite; pytest's skip markers keep the
  suite importable and green in that environment.

**Not verified:** real ImageNet weights are fetched/cached on first run; the
inference assertions allow `unsorted` for synthetic solid-colour images, so
mapping *accuracy* is not measured here (accuracy harness → Story 3.x).
