# Epic 2 Context: Classify Images (mobilenet default)

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Give every scanned image a trustworthy category plus confidence through a single classifier interface, using the default pre-trained backend and a shipped label-to-category mapping with honest fallback to `unsorted` — so organizing (Epic 3) and future backends build on one routing policy, not per-backend guesses.

## Stories

- Story 2.1: Classifier contract and backend selection
- Story 2.2: MobileNetV2 backend with shipped mapping
- Story 2.3: Confidence threshold and category normalization

## Requirements & Constraints

- One interface serves all backends; `--backend` selects between exactly two names: `mobilenet` (default) and `custom-cnn`. Unknown backend names fail as backend-unavailable.
- Default backend resolves images via pre-trained MobileNetV2 on ImageNet; top-1 label passes through the shipped label→category mapping. Any label with no mapping entry routes to `unsorted` regardless of confidence.
- Each result carries a category plus a confidence score defined as the top-1 probability of a mapped label. Default threshold 0.45, valid range (0, 1], overridable via `--threshold`; below threshold routes to `unsorted` with a reason stating actual vs threshold.
- Unmapped-label results route to `unsorted` with a reason naming the unmapped label; corrupt/unreadable images raise a stable, documented predict-stage exception (Epic 3 converts it to a reason-carrying `unsorted` job and continues the run).
- Category authority is the five allow-listed IDs (`gym-memes`, `cat-memes`, `chaotic-screenshots`, `wholesome-posts`, `unsorted`); no other folder name may be produced. Normalization to `unsorted` happens once, inside the classifier layer.
- Threshold override flows only through the classifier factory (`get_classifier(name, threshold=…)`); CLI passes the flag value through and never re-routes, and the organizer never recomputes confidence.
- Success: zero-training classification works out of the box; borderline or uncovered images are parked in `unsorted` with reasons rather than misfiled.

## Technical Decisions

- Strategy seam in `classifier.py`: a base-class interface declaring `load()` and `predict()`; a factory validates the backend name against config and raises backend-unavailable when TensorFlow is unimportable. Shared result type (`ClassificationResult`: five-element probability vector over the configured categories plus final category, confidence, and reason) lives in `classifier.py` and is never forked.
- ML isolation: TensorFlow and NumPy import only in `classifier.py`; CLI, organizer, and config stay stdlib-only so the organizer test path stays green without TensorFlow. Backend-specific tests live in a separate module that skips when TensorFlow is absent.
- All model and network I/O (including the one-time ImageNet weight fetch, ~14 MB) happens inside `load()`; `predict()` never fetches. First-run weight download means demos should pre-warm the cache; offline plus non-dry-run surfaces as backend-unavailable (exit 2, owned by Epic 3's lifecycle).
- Five-element normalized distribution over the configured categories is the per-backend contract; routing (unmapped or below threshold → `unsorted`) is implemented once in the classifier layer, not per backend.
- Config remains the single source of truth: category list, backend names, threshold default, and mapping structure are read from config, never re-declared. The classifier's path-traversal safety relies on the allow-list check; the organizer's sanitizer is defense-in-depth only.
- Dependency direction is `main → cli → {classifier, organizer} → config`; classifier and organizer never import each other. Flat root modules, no new package layout.
- Every AI prompt is appended verbatim to the append-only log at `<project>/../PROMPTS_LOG.md` — applies to all build work.

## Cross-Story Dependencies

- Story 2.1 (contract + factory) must land first: 2.2 implements the backend against the interface and 2.3 implements routing on top of the distribution contract it defines.
- Story 2.2 (backend + mapping) precedes 2.3 (threshold/normalization): routing rules in 2.3 assume mapped top-1 labels with probabilities from 2.2.
- Depends on Epic 1 for category IDs, threshold default, backend names, and mapping structure from config; produces the final category + confidence + reason contract that Epic 3 (organize/report/lifecycle) consumes. Custom-CNN training/inference (Epic 4) reuses the same interface and distribution contract.
