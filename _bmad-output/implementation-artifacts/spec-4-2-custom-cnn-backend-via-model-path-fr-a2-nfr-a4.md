---
title: 'Story 4.2: custom-cnn backend via --model-path (FR-A2, NFR-A4)'
type: 'feature'
created: '2026-10-04'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `CustomCNNClassifier.load/predict` still raise `NotImplementedError` and the factory never threads `model_path`, so the 4-1 artifact cannot be used for inference: `--backend custom-cnn` is a dead end (FR-A2, NFR-A4, AC-A11).

**Approach:** Implement `CustomCNN` load (lazy TF, missing artifact and non-five-output artifacts rejected as `BackendUnavailable`) and predict (64px RGB preprocessing mirroring training, top-1 over `CATEGORIES` with shared `route()` threshold handling, five-element softmax distribution), thread `model_path` through `get_classifier` into the cli `load()` call, and prove parity with TF-gated artifact tests plus TF-free wiring tests.

</frozen-after-approval>

## Implementation Notes

- 2026-10-04: `CustomCNN.load` (lazy keras, missing-file check before TF
  import for precise errors, non-five-wide rejected as unavailable) and
  `predict` (64px RGB//255 mirroring training, top-1 + shared `route()`,
  real five-element softmax distribution); factory threads `model_path`
  to custom-cnn only; cli passes `args.model_path`; stale Dev-phase
  docstring/message updated; `DEV_TODO` removed (last use gone).
- 2026-10-04: Precedent-following churn — all `get_classifier` fakes in
  `tests/test_cli_run.py` accept `model_path=None` (same as 3-5's
  `fixture_root` mock update).
- 2026-10-04: Tests — 4 TF-free wiring + 4 TF-gated artifact tests in
  `test_backends.py`, cli threading/exit-2 spy test, TF-gated
  train→inference e2e in `test_train.py` (10 images filed, inbox
  drained). `uv run --with pytest pytest -q` — 156 passed (147 + 9).

## Review Triage Log

- `false` — `output_shape` read outside the try-block: every reachable anomaly (multi-output list, `None` dim) compares unequal to 5 and raises `BackendUnavailable`; `AttributeError` is unreachable via a successful `load_model`.
- `false` — no input-shape check against the artifact: resolution mismatches fail loudly as `PredictFailed` at inference, never silently; the constant is the training contract both sides share.
- `low → patched` — `args.model_path` direct access vs `getattr` elsewhere: normalized to `getattr` with the config default; confusing user-error messages left alone (exits were already correct).
- `low → rejected` — unreachable `NotImplementedError` branch: kept as a safety net for future backends; zero runtime harm.
- `low → patched` — `--model-path` silently ignored by other backends: help text now says custom-cnn-only, and an explicitly-passed path with another backend warns and proceeds (test pinned).
- `false` — real softmax vs mobilenet one-hot divergence: the AC literally requires the five-element distribution, and no production code reads `.probabilities` (tests only).
- `low → patched` — garbage-bytes `.keras` had no test: TF-free rejection test added; near-miss widths and flat-inbox variants rejected as same-path duplication (1-wide exercises the `!= 5` gate; recursion modes pinned since 1-4).
