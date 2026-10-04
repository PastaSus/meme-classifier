---
title: 'Story 4.1: Training lifecycle (FR-A9)'
type: 'feature'
created: '2026-10-04'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'ce55327'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `--train` is parsed but never read, so no custom-cnn artifact can be produced: the Epic 4 backend has nothing to load and the reserved lifecycle slot does nothing.

**Approach:** Add `classifier.train_labeled_model()` fitting the AD-10 lab CNN on `<root>/<category>/*.jpg` and saving `.keras` to `--model-path`, plus the cli train slot before scanning (dry-run skips with warning and zero writes, bad root exits 1, TF/model failure exits 2, training prints its own summary and returns without organizing). `CustomCNN.load/predict` stay unimplemented — Story 4.2 owns them.

## Boundaries & Constraints

**Always:** Training code lives in `classifier.py` only (ML firewall; no top-level TF imports elsewhere); lab arch Conv2D → MaxPooling2D → Flatten → Dense per AD-10; artifact writes go only to the resolved `--model-path` (sole NFR-A3 exception, AD-11); root problems exit 1, TF/model problems exit 2; real fit covered by a TF-gated test module, slot mechanics by TF-free tests.

**Never:** No CLI flags for hyperparameters (story picks small-CPU values, records them); no train logic in cli beyond call + summary + exits; no committed `.keras` artifact; no `CustomCNN` inference changes (4-2); no floor/OQ-1 touch.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| TRAIN_OK | `<root>/<category>/*.jpg`, no dry-run | fits lab CNN, saves artifact, prints train summary, exit 0, scan/organize never run (inbox not required) | N/A |
| DRY_SKIP | `--train` + `--dry-run` | warning, training skipped, zero writes, exit 0 | N/A |
| BAD_ROOT | missing train root / no images | exit 1 with zeroed report, before side effects | path validation in `run()` |
| TF_FAIL | TF missing/broken during fit or save | exit 2, no partial artifact relied upon | `BackendUnavailable` mapping |
| LATE_TRAIN | `--train` with normal inbox args | training still runs first; organize loop skipped after train summary | N/A |

</frozen-after-approval>

## Code Map

- `classifier.py` — add `train_labeled_model(root, model_path)` (TF imports function-local; reuse `CATEGORIES`, image size 64 to match fixture scale); `CustomCNN` untouched.
- `cli.py` — train slot after the fixture check, before `scan_images()`; reuse `empty_report()` + exit-1/exit-2 patterns; render train summary, return without organize.
- `config.py` — reuse `DEFAULT_MODEL_PATH` as-is; no new constants.
- `tests/test_cli_run.py` — TF-free slot tests (order pin, dry skip, bad root, TF-fail mapping) with monkeypatched train function.
- `tests/test_train.py` — new TF-gated module (skip without TF, mirroring `test_backends.py`): real fit on a generated 5-category tree asserts a loadable `.keras` artifact.

## Tasks & Acceptance

**Execution:**
- [x] `classifier.py` -- add `train_labeled_model()` (AD-10 lab CNN, few-epoch CPU fit, `.keras` save) -- ML stays behind the classifier boundary
- [x] `cli.py` -- train slot before scan with dry-run skip, exits, summary -- lifecycle per AD-13
- [x] `tests/test_cli_run.py` -- TF-free slot mechanics -- exits and ordering without TF
- [x] `tests/test_train.py` -- TF-gated real fit -- artifact exists and reloads

**Acceptance Criteria:**
- Given `<root>/<category>/*.jpg`, when `--train <root>` runs without `--dry-run`, then the artifact is saved to `--model-path`, a train summary prints, exit is 0, and scan/organize never run
- Given `--train` with `--dry-run`, when the run executes, then training is skipped with a warning, zero writes occur, exit is 0
- Given a missing/bad train root, when training starts, then exit is 1; given TF/model failure, exit is 2

## Implementation Notes

## Spec Change Log

## Review Triage Log

- `low → patched` — per-category counted pre-decode while samples counted decoded: both now derive from decoded labels; corrupt-mix + all-corrupt tests pin it.
- `false` — no minimum-sample guard: a floor would break the spine-mandated fixture smoke-train (2/category); training on few samples is intended.
- `false` — train success prints no zeroed report: the approved spec defines the train summary as this path's output; generic lifecycle prose does not override it.
- `low → patched` — dry-run answered before root validation: `is_dir` check now precedes the dry branch (missing root exits 1 in every mode, matching input/fixture precedent); missing+dry test added.
- `low → patched` — TF-mapping test sat in the `@needs_tf` class: moved to module level so it runs TF-free.
- `false` — TF-free tests need Pillow: Pillow is a declared project dependency present in every supported run; NFR-A1 scopes to TensorFlow.
- `false` — no fit history for 4-3/OQ-1: calibration consumes fixture accuracy, not train loss; nothing blocked.
- `low → rejected` — non-`.keras` paths, silent overwrite, no seed: output-path overwrite is intended retrain semantics; no AC requires format/seed guards.
- `low → patched` — empty-string `--train` trained on CWD: explicitly-passed empty now exits 1 (test added); fall-through to organize rejected as silent flag-ignoring.
- `low → patched` — `iterdir` `OSError` leaked into the exit-2 bucket: unreadable subdirs skipped with warning, total failure still `ValueError` (exit 1).
- `medium → patched` — failed save could truncate a pre-existing artifact: temp-sibling + `os.replace` atomicity; save-failure tests pin fresh-cleanup and pre-existing preservation.
- `low → rejected` — full in-memory image load: story scale is tens of images per the AC; streaming is unrequired complexity.
- `medium → patched` — corrupt-skip path untested: mixed valid/corrupt and all-corrupt tests added (also verifies the counting fix).
- `low → patched` — summary keys unpinned real-side: fit test now asserts `batch_size`/`image_size`/`per_category` from the real return.
- `low → patched` — corrupt skips still counted in per-category totals: `per_category` now built from decoded labels only, so skipped files appear in neither count.
- `medium → patched` — failed save risks a truncated artifact at the target: save goes to a temp sibling with `os.replace` on success and temp cleanup on failure.
- `medium → patched` — no test failed a real save: save-failure tests assert `BackendUnavailable`, no fresh file remains, and pre-existing bytes survive intact.
- `false` — Pillow-less QA errors at fixture setup: Pillow ships as a project dependency in all supported runs and AD-4 exempts test tooling; TF-absence (the NFR-A1 claim) is unaffected.

## Verification

**Commands:**
- `uv run --with pytest pytest -q` -- expected: full suite green (TF-gated fit runs where TF present, skips cleanly where absent)
