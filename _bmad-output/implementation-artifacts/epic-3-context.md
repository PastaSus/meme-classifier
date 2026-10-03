# Epic 3 Context: Organize Safely & Report (end-to-end)

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Make the tool trustworthy end to end: scanned and classified images are actually filed into category folders without ever overwriting, every run (including dry-runs and empty inputs) prints one honest summary and exits with a stable code, and re-runs are idempotent — so an examiner can run it once and defend exactly what happened.

## Stories

- Story 3.1: Collision-free filing (FR-A4, FR-A5)
- Story 3.2: Report contract with reasons (FR-A7)
- Story 3.3: Run lifecycle and exit codes (FR-A8)
- Story 3.4: Dry-run that touches nothing (FR-A6)
- Story 3.5: Fixture accuracy and calibrated floors
- Story 3.6: Idempotency and TF-free QA suite (NFR-A1, NFR-A3)

## Requirements & Constraints

- Files are moved (not copied) into per-category folders created on demand; colliding filenames get a numeric suffix (`cat-1.jpg`, up to 1000 attempts) and are never overwritten.
- Only allow-listed category folder names may ever be created; category strings are path-traversal-safe.
- A summary report prints after every run, including empty inputs: per-category planned/moved counts plus separate refused/failed/skipped counters with reasons; corrupt/unreadable images continue the run as `unsorted` jobs with the reason in the report, never only in logs.
- When a labelled fixture (10 images, 2 per category across the 5 categories) is supplied, the report shows placement accuracy and per-category counts; accuracy and unsorted-share floors live as config constants and are asserted in tests only, never enforced in organizer/cli logic (first-pass values pending calibration sign-off).
- Dry-run prints planned moves with zero filesystem mutations (no mkdir, move, or cache-priming) against a virtual destination tree; it works with the backend unavailable by planning everything to `unsorted` with a visible warning and exiting 0.
- Exit codes are deterministic: 0 for success including reported skips/refusals/failures, 1 for runtime/filesystem errors such as a missing input dir, 2 for backend unavailable on a non-dry run.
- Organizer logic and its tests run without TensorFlow installed (stdlib-only); TF-dependent backend tests live in a separate skipping module.
- Re-running with an empty inbox leaves the output tree byte-identical; restored colliding files re-file via suffixing; no writes occur outside the output root.

## Technical Decisions

- Fixed run lifecycle in `cli.run`: parse → train? → scan → empty-check → load → organize → render, with a report rendered before every return; the missing-dir check happens before side effects; `load()` owns all model/network I/O so backend-down on a non-dry run exits 2 with no partial moves.
- The backend-down dry-run fallback is cli-side job synthesis only — no fallback name is added to the backend list.
- Failure reasons travel on the organize job's `reason` field into the report's error counters; refused/failed/skipped outcomes are excluded from per-category counts; cli renders the organizer's empty-report helper on early exits and never instantiates the report directly.
- Expected fixture labels come from an organizer helper and accuracy is computed inside `organize()`; cli only passes roots through and renders.
- Module boundaries: ML imports only in `classifier.py`; organizer/cli/config stay stdlib-only; imports flow `main → cli → {classifier, organizer} → config`; the classification result type lives in the classifier module and the job/report types live in the organizer module; flat root modules with no new package layout.
- Category normalization happens in the classifier layer before the organizer boundary; the organizer's sanitize helper is path-traversal defense-in-depth only.
- First default-backend `load()` fetches weights (~14 MB) — pre-warm the cache before live demos; offline plus non-dry run means exit 2.

## Cross-Story Dependencies

- Story 3.1 (collision-free moves) is the foundation 3.2–3.6 build on; 3.2 defines the report shape 3.4 and 3.5 render into.
- Story 3.3's lifecycle ordering gates 3.4 (backend availability is resolved before any move, so non-dry backend-down exits cleanly).
- Corrupt-image handling depends on Epic 2's classifier contract: predict-stage failures are converted at the cli layer into reason-carrying `unsorted` jobs.
- Builds on Epic 1 (scan, CLI surface, config single source of truth, output root excluded from scans); the `--train` lifecycle hook belongs to Epic 4 but its ordering and dry-run-skip behavior constrain Story 3.3.
