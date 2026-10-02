---
title: 'Story 1.2: Establish config.py single source of truth'
type: 'chore'
created: '2026-10-02'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `config.py` declares only part of the tunable set (categories, extensions, backends, threshold 0.45, I/O paths, collision cap) — `DEFAULT_MODEL_PATH`, `ACCURACY_FLOOR` / `UNSORTED_SHARE_FLOOR`, and the fixture default are missing, and the label→category mapping still lives in `classifier.py` (`IMAGENET_LABEL_TO_CATEGORY`), violating AD-3; no test pins the exact category/extension sets.

**Approach:** Declare every missing constant exactly once in `config.py` (stdlib-only), move the mapping table home to `config` with `classifier.py` importing it, and add a TF-free test asserting the five categories, six extensions, and key defaults — no CLI or runtime behavior changes.

</frozen-after-approval>

## Implementation Notes

- 2026-10-02: added `DEFAULT_MODEL_PATH` (`models/custom-cnn.keras`), `DEFAULT_FIXTURE_DIR`
  (`tests/fixtures/labeled`), `ACCURACY_FLOOR = 0.6` / `UNSORTED_SHARE_FLOOR = 0.8`
  (OQ-1 first-pass), moved `IMAGENET_LABEL_TO_CATEGORY` table home to `config.py`;
  `classifier.py` imports it and re-exports the same object (back-compat, single
  declaration). New `tests/test_config.py` (7 tests, TF-free) pins categories,
  extensions, defaults, floors, mapping coverage. Verified: 24 passed
  (17 organizer + 7 config); stdlib-only check clean for `config.py`,
  `cli.py`, `organizer.py`.

## Review Triage Log

- 2026-10-02 (step-oneshot inline, no subagent runtime): blind-hunter
  N = min(floor(sqrt(4) + 1), 10) = 3 candidates traced; edge-case enumeration
  over new constants + mapping move + config test; verification-gap trace over
  24-test suite. Verdicts:
  - `false` — `classifier` importing `config` creates a cycle: direction is
    `classifier → config` (AD-6 legal); `config` imports only stdlib `pathlib`.
    No cycle exists.
  - `false` — re-export `IMAGENET_LABEL_TO_CATEGORY = IMAGENET_LABEL_TO_CATEGORY`
    is a duplicate declaration: verified `classifier.X is config.X` → True;
    single table, single home.
  - `false` — new test imports `classifier` (pulls TF-adjacent module into
    TF-free suite): `classifier.py` has zero TF/NumPy/Pillow imports at module
    level (stubs only); 24 passed with TF absent.
  - `low → rejected` — `DEFAULT_FIXTURE_DIR` points at a not-yet-created
    `tests/fixtures/labeled` tree: no code reads it this story (Story 3-5 owns
    fixtures); creating empty dirs now would add unjustified on-disk folders
    (AD-1 rule).
- Result: no patch, no HALT, nothing deferred. ACs verified: 24 passed;
  mapping identity True; stdlib-only clean.
