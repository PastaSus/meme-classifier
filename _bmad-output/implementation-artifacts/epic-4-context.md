# Epic 4 Context: Train & Use the Custom CNN

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Users bring their own trained model: `--train` fits the lab CNN on a user-labeled folder tree and saves a reusable artifact, and `--model-path` switches inference to that artifact through the same classifier interface — with training obeying the fixed run lifecycle (runs first, dry-run-aware, never touching the inbox).

## Stories

- Story 4.1: Training lifecycle (FR-A9)
- Story 4.2: custom-cnn backend via --model-path (FR-A2, NFR-A4)
- Story 4.3: Demo readiness and OQ calibration

## Requirements & Constraints

- `--train <root>` consumes `<root>/<category>/*.jpg` with roughly 10 labeled images per category, and saves the artifact to the `--model-path` location (default `models/custom-cnn.keras`).
- All tunables including the model artifact path are overridable via CLI flags; omitting `--model-path` uses the config default.
- Training runs before scanning, does not require an inbox, emits its own summary, and returns without running the organize loop.
- Under `--dry-run`, training is skipped with a warning and zero filesystem writes occur anywhere.
- Bad/missing train root exits 1; TensorFlow or model failure during training or load exits 2.
- Model-artifact writes under `models/` are the sole exception to the zero-writes-outside-output-root idempotency rule.
- Demo gate: all acceptance criteria demonstrable, weight cache pre-warmed, offline behavior verified (exit 2 non-dry / fallback dry); accuracy floors recalibrated at review and the live-train-vs-architecture-only decision recorded.

## Technical Decisions

- Single model-path literal lives in config as the default; every other module receives it as a constructor/flag argument, never re-declares it.
- Fixed run order is parse → train? → scan → empty-check → load → organize → render, with a report rendered before every return.
- All model and network I/O lives inside `load()`; `predict()` never fetches weights.
- Every backend returns a five-element probability distribution over the configured categories; routing of unmapped or below-threshold results to `unsorted` happens once inside the classifier layer, and a binary-output artifact is rejected at load time as unavailable.
- Lab CNN shape is Conv2D → MaxPooling2D → Flatten → Dense with binary or categorical cross-entropy; training hyperparameters are decided at implementation and smoke-tested on the fixture.
- ML imports (TensorFlow, NumPy) exist only in the classifier module; organizer, CLI, and config stay stdlib-only so file-handling tests pass without TensorFlow.
- Dependency direction is entry → CLI → {classifier, organizer} → config; shared result/report types keep their fixed homes; modules stay flat at the repo root with no new package layout.
- Writes are confined to the output tree, `models/`, and the weight cache; categories are allow-listed IDs with path-traversal validation as defense-in-depth.

## Cross-Story Dependencies

- Story 4.2 depends on Story 4.1's artifact: training must produce a loadable file before `--model-path` inference can be exercised.
- Story 4.1 builds on the Epic 3 lifecycle, exit-code matrix, and dry-run zero-write guarantee; training is a new first stage in that same ordered run.
- Story 4.2 builds on the Epic 2 classifier contract (single ABC/factory, threshold hand-off, classifier-side normalization) and behaves identically to the default backend from the CLI's perspective.
- Story 4.3 depends on all prior epics and both 4.1/4.2: full acceptance coverage, pre-warmed weights, calibrated accuracy floors, and the recorded demo-scope decision.
