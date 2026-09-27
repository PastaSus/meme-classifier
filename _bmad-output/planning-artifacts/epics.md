---
stepsCompleted: ["step-01", "step-02", "step-03"]
inputDocuments:
  - docs/product-requirements.md
  - _bmad-output/planning-artifacts/architecture/architecture-meme-classifier-2026-09-27/ARCHITECTURE-SPINE.md
  - docs/system-architecture.md
---

# meme-classifier - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for meme-classifier, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

- FR-A1: Scan the input folder for image files (`.jpg .jpeg .png .gif .bmp .webp`), optionally recursive; non-image files ignored; missing input directory is an error (exit 1).
- FR-A2: Classify each image via a selectable backend behind a single interface: `mobilenet` (default) — MobileNetV2 pre-trained on ImageNet, top-1 label through shipped label→category mapping, any label not in the mapping routes to `unsorted` regardless of confidence; `custom-cnn` — lab CNN (Conv2D → MaxPooling2D → Flatten → Dense, binary or categorical cross-entropy) loaded from a trained artifact via `--model-path`.
- FR-A3: Assign each image a category + confidence score (top-1 probability of a mapped label). Default threshold 0.45, valid range (0, 1], `--threshold` overridable (NFR-A4). Below threshold → `unsorted`; high-confidence but unmapped label → `unsorted`.
- FR-A4: Move files into `<output>/<category>/` with `shutil.move`, creating directories on demand (`os.makedirs`).
- FR-A5: Never overwrite existing files — colliding names get a numeric suffix (`meme-1.jpg`).
- FR-A6: `--dry-run` prints the planned moves without touching disk. Works even when the backend is unavailable: every scanned file is planned to `unsorted` with a visible warning, exit 0.
- FR-A7: Print a summary report after every run (including empty input): per-category planned/moved counts, skipped count, errors count with reasons (refused vs failed distinguished), and — when a labelled fixture is supplied — placement accuracy.
- FR-A8: Exit codes: `0` success (reported skips included), `1` runtime/filesystem error (e.g. missing input dir), `2` backend unavailable on a non-dry run.
- FR-A9: `--train <root>` trains the custom CNN on a user-labeled folder tree (`<root>/<category>/*.jpg`), saves the artifact to `--model-path` (default `models/custom-cnn.keras`); the same flag loads the artifact for inference. Min ~10 labeled images per category to train.

### NonFunctional Requirements

- NFR-A1: Organizer logic (scan/move/report) must work without TensorFlow installed (pure stdlib) so QA can test file handling anywhere.
- NFR-A2: Path-traversal-safe category names — only sanitized, allow-listed categories accepted.
- NFR-A3: Idempotent: re-running with an empty inbox leaves the output tree byte-identical; zero writes ever occur outside the output root; a restored inbox re-files via FR-A5 suffixing, never overwrites.
- NFR-A4: All config (paths, threshold, backend, model artifact) overridable via CLI flags — including `--model-path`.
- NFR-A5: Environment: Python 3.13, managed project-locally by `uv` (system Python untouched); stable TensorFlow 2.21.x. Organizer and tests remain TF-free (NFR-A1).

### Additional Requirements

From `ARCHITECTURE-SPINE.md` (final, AD-1..AD-14):

- AR-1 (AD-14): CLI surface frozen to PRD §2.1 — `-o/--output`, `-r` recursion **off** by default, `--backend`, `--threshold`, `--dry-run`, `--fixture`, `--train`, `--model-path`. Existing code drift (`--output-dir`, `--no-recursive` default-on) reconciled in a dedicated first story before feature work.
- AR-2 (Deferred + NFR-A5): uv environment provisioning — `pyproject.toml` + `requires-python = "3.13"` + lockfile; first build-phase task; today `uv run` resolves 3.12.13.
- AR-3 (AD-3): `config.py` is the single source of truth — categories, extensions, threshold, backends, paths, label→category mapping structure, `DEFAULT_MODEL_PATH`, `ACCURACY_FLOOR`/`UNSORTED_SHARE_FLOOR`, fixture default; every CLI flag maps to one config name.
- AR-4 (AD-10): Five-element probability distribution over `config.CATEGORIES` per backend; routing (unmapped or < threshold → unsorted) once in classifier layer; threshold hand-off `get_classifier(name, threshold=…)`.
- AR-5 (AD-13): Run lifecycle `parse → train → scan → empty-check → load → organize → render`; `--dry-run` = zero filesystem mutations everywhere (virtual tree); `--train` runs before scan, skips with warning under `--dry-run`; report rendered before every return.
- AR-6 (AD-8): Exit/availability matrix — `load()` owns all model/network I/O (incl. ImageNet weight fetch); missing dir → 1; backend down + non-dry → 2; backend down + dry → fallback unsorted-plan, exit 0; argparse value-shape only, path existence → 1.
- AR-7 (AD-7/AD-12): Failure reasons travel on `OrganizeJob.reason` → `OrganizeReport.errors`; refused/failed/skipped excluded from `counts_by_category`; cli renders `organizer.empty_report()` on early exits.
- AR-8 (AD-4): TensorFlow/NumPy only in `classifier.py`; organizer/cli/config stdlib-only; TF backend tests in a separate skipping module; `organizer.py` zero ML imports.
- AR-9 (AD-9): Classifier layer normalizes non-member categories → `unsorted` + reason before organizer; `sanitize_category` = defense-in-depth only.
- AR-10 (AD-6): Dependency direction `main → cli → {classifier, organizer} → config`; shared types fixed homes (`ClassificationResult` in classifier.py; `OrganizeJob`/`OrganizeReport` in organizer.py); flat root modules, no new package layout.
- AR-11 (AD-5): Every AI prompt append-only logged to `<project>/../PROMPTS_LOG.md` (course policy) — applies to every build story.
- AR-12 (Operational): First mobilenet `load()` downloads ImageNet weights (~14 MB) — pre-warm cache before defense demos; offline + non-dry → exit 2.
- AR-13 (AC-A6/OQ-1): Labelled fixture of 10 images (5 categories, 2 each) built in tests/fixtures; accuracy floor and unsorted-share floor live as config constants, values calibrated at OQ-1 sign-off.

### UX Design Requirements

- N/A — CLI tool with terminal report output; no UX design contract exists (no bmad-ux run).

### FR Coverage Map

- FR-A1: Epic 1 — Scan & Validate the Inbox (extensions, recursion flag, ignore non-images, missing dir → exit 1)
- FR-A2: Epic 2 — Classify Images (mobilenet backend) + Epic 4 — custom-cnn backend loaded from artifact seam
- FR-A3: Epic 2 — Classify Images (category + confidence, threshold 0.45 (0,1], routing rules)
- FR-A4: Epic 3 — Organize Safely & Report (shutil.move into `<output>/<category>/`, makedirs)
- FR-A5: Epic 3 — Organize Safely & Report (no overwrite, numeric suffix)
- FR-A6: Epic 3 — Organize Safely & Report (--dry-run, backend-unavailable fallback, exit 0)
- FR-A7: Epic 3 — Organize Safely & Report (summary report every run, refused vs failed, fixture accuracy)
- FR-A8: Epic 3 — Organize Safely & Report (exit codes 0/1/2)
- FR-A9: Epic 4 — Train & Use the Custom CNN (--train lifecycle, artifact, --model-path inference)

## Epic List

### Epic 1: Scan & Validate the Inbox (foundation)
Users can run the CLI against any folder and see a reliable scan: correct PRD §2.1 flags, reproducible uv environment (Python 3.13), config as single source of truth, non-image files ignored, missing input dir exits 1.
**FRs covered:** FR-A1
**ARs:** AR-1, AR-2, AR-3, AR-10; NFR-A5

### Epic 2: Classify Images (mobilenet default)
Users get every scanned image resolved to a category + confidence via MobileNetV2 behind the single classifier interface, using the shipped label→category mapping, with unmapped/low-confidence results normalized to `unsorted` inside the classifier layer.
**FRs covered:** FR-A2, FR-A3
**ARs:** AR-4, AR-8, AR-9, AR-12

### Epic 3: Organize Safely & Report (end-to-end)
Users see files actually filed into category folders without overwrites, a complete report on every run (refused/failed/skipped reasons + fixture accuracy), a trustworthy dry-run (zero writes, backend-down fallback), and stable exit codes with idempotent re-runs.
**FRs covered:** FR-A4, FR-A5, FR-A6, FR-A7, FR-A8
**ARs:** AR-5, AR-6, AR-7, AR-13; NFR-A1, NFR-A2, NFR-A3

### Epic 4: Train & Use the Custom CNN
Users train the lab CNN on a labeled folder tree and switch inference to their artifact via `--model-path`, with `--train` obeying the run lifecycle (runs first, dry-run-aware, never touching the inbox).
**FRs covered:** FR-A9
**ARs:** AR-5 (lifecycle), AR-6 (load() I/O); NFR-A4

## Epic 1: Scan & Validate the Inbox (foundation)

The project runs in a reproducible, PRD-conformant environment: any folder can be scanned with the exact §2.1 CLI surface, and the config layer gives every later story one authoritative place to read defaults from.

### Story 1.1: Provision the uv environment

As a lab engineer,
I want the project pinned to Python 3.13 with a locked uv environment,
So that everyone runs identical dependencies and NFR-A5 holds.

**Acceptance Criteria:**

**Given** a fresh clone of the repository
**When** `uv sync` (or `uv run`) is executed
**Then** uv creates a project-local environment using Python 3.13 without touching the system interpreter
**And** `pyproject.toml` declares `requires-python = "3.13"` and dependencies include `tensorflow>=2.21,<2.22`, `numpy>=1.26`, `pillow`, `pytest`
**And** a `uv.lock` is committed so re-syncs resolve identically
**And** `uv run --with pytest pytest -q` passes with TensorFlow absent (NFR-A1, AC-A5)

### Story 1.2: Establish config.py single source of truth

As a developer,
I want every tunable declared exactly once in `config.py`,
So that flags, tests, and backends read the same values and nothing drifts story to story.

**Acceptance Criteria:**

**Given** the flat repo layout (AD-2)
**When** any module needs a default (categories, image extensions, threshold 0.45, backend names, default I/O paths, label→category mapping structure, `DEFAULT_MODEL_PATH`, `ACCURACY_FLOOR`, `UNSORTED_SHARE_FLOOR`, fixture default)
**Then** it imports the value from `config.py` and declares no duplicate literal
**And** imports flow only `main → cli → {classifier, organizer} → config` (AD-6) — no upward imports
**And** a test asserts the five `CATEGORIES` IDs and six `IMAGE_EXTENSIONS` match PRD §2.2/§2.3

### Story 1.3: Reconcile the CLI surface to PRD §2.1

As a user,
I want the exact flags printed in the PRD's usage line,
So that documented commands work verbatim.

**Acceptance Criteria:**

**Given** `python main.py --help` (via `py`/`uv`)
**When** the help output renders
**Then** it lists the positional inbox argument, `-o/--output` (default `data/organized/`), `-r` (recursion **off** by default), `--backend` (default `mobilenet`), `--threshold` (default 0.45), `--dry-run`, `--fixture`, `--train`, `--model-path`, `--verbose`
**And** the drift names (`--output-dir`, `--no-recursive`) are gone (AD-14)
**And** `--threshold` rejects 0 and values > 1 at parse time with exit 2 (AD-8)
**And** every flag maps to exactly one `config.py` name (AR-3)

### Story 1.4: Scan and validate the inbox (FR-A1)

As a user,
I want only image files discovered in my inbox,
So that noise files never enter the pipeline and mistakes fail loudly.

**Acceptance Criteria:**

**Given** an inbox containing `.jpg .jpeg .png .gif .bmp .webp` files plus a `.txt` file
**When** the tool scans with recursion off
**Then** only image files are returned; the `.txt` is ignored (FR-A1)
**And** with `-r`, files in nested subfolders are found
**Given** a nonexistent input path
**When** the tool runs
**Then** it exits 1 before performing any writes (FR-A8)
**And** `organizer.py` imports only stdlib — no TensorFlow, NumPy, or Pillow (NFR-A1, AD-4)

## Epic 2: Classify Images (mobilenet default)

Every scanned image resolves to a category + confidence through one classifier interface, with mapping and threshold policy enforced inside the classifier layer.

### Story 2.1: Classifier contract and backend selection

As a developer,
I want one ABC and one factory for all backends,
So that adding or switching backends never touches cli or organizer.

**Acceptance Criteria:**

**Given** `classifier.py`
**When** it is imported
**Then** `BaseClassifier` declares `load()` and `predict()`; `ClassificationResult` holds a five-element probability vector over `config.CATEGORIES` plus category/confidence/reason (AD-10)
**And** `get_classifier(name, threshold=…)` returns the backend for `--backend` and raises `BackendUnavailable` for unknown names or unimportable TensorFlow (AD-4, AD-8)
**And** `MODEL_BACKENDS` in `config.py` lists exactly `mobilenet` and `custom-cnn`
**And** no TF/NumPy import exists outside `classifier.py` (AD-4)

### Story 2.2: MobileNetV2 backend with shipped mapping

As a user,
I want the default backend to resolve images through MobileNetV2 and a label→category mapping,
So that my memes land in the lab's five categories with zero training required.

**Acceptance Criteria:**

**Given** TensorFlow installed and weights available
**When** `mobilenet` `load()` runs
**Then** MobileNetV2/ImageNet weights load (fetching once if needed, inside `load()` only — `predict()` never fetches, AR-6/AD-8)
**And** `predict()` returns the top ImageNet labels mapped through the shipped mapping declared in `config.py` (AR-3)
**Given** an image whose top label has no mapping entry
**When** prediction completes
**Then** the result routes to `unsorted` regardless of confidence (FR-A2)
**And** a corrupt/unreadable image raises the documented predict-stage failure (consumed later by Epic 3's conversion to a reason-carrying unsorted job, AD-7) — verified by a unit test that the exception type and message are stable

### Story 2.3: Confidence threshold and category normalization

As a user,
I want a single threshold rule and a single category authority,
So that borderline images are honestly parked in `unsorted` instead of being misfiled.

**Acceptance Criteria:**

**Given** a prediction with top-1 probability 0.40 and default threshold 0.45
**When** routing evaluates
**Then** the image is assigned `unsorted` with reason `confidence 0.40 < 0.45` (FR-A3)
**Given** a top-1 probability above threshold but an unmapped label
**When** routing evaluates
**Then** the image is assigned `unsorted` with reason naming the unmapped label (FR-A2/FR-A3)
**Given** any classifier output
**When** it reaches the cli→organizer boundary
**Then** non-member categories are normalized to `unsorted` + reason inside the classifier layer; `organizer.sanitize_category` remains path-traversal defense only (AR-9)
**And** `--threshold` overrides the config default through `get_classifier(threshold=…)` — cli never re-routes (AR-4, NFR-A4)

## Epic 3: Organize Safely & Report (end-to-end)

Files are filed without overwrites, every run reports honestly, dry-runs touch nothing, and exit codes are stable — the tool an examiner can trust on the first try.

### Story 3.1: Collision-free filing (FR-A4, FR-A5)

As a user,
I want files moved into category folders without ever being overwritten,
So that organizing twice never destroys anything.

**Acceptance Criteria:**

**Given** a planned job for category `cat-memes`
**When** the run executes (non-dry)
**Then** `<output>/cat-memes/` is created on demand (`os.makedirs`) and the file is moved with `shutil.move` (FR-A4)
**Given** `cat.jpg` already exists in the destination
**When** another `cat.jpg` is filed
**Then** it lands as `cat-1.jpg`, then `cat-2.jpg`, … up to 1000 attempts before `skipped` (FR-A5)
**And** only allow-listed `config.CATEGORIES` folder names are ever created (NFR-A2, AD-9)
**And** the organizer module has zero ML imports (NFR-A1)

### Story 3.2: Report contract with reasons (FR-A7)

As a user,
I want every run to end with one accurate summary,
So that I can defend exactly what the tool did and why.

**Acceptance Criteria:**

**Given** a completed run
**When** the report prints
**Then** it shows per-category planned/moved counts with refused/failed/skipped **excluded** from `counts_by_category`, plus separate refused/failed/skipped counters carrying reasons (FR-A7, AR-7)
**Given** a corrupt image at predict time
**When** cli converts the failure
**Then** it becomes an `OrganizeJob(category="unsorted", reason=…)` (AD-7), the run continues, and the reason appears in the report — never only in the log (AC-A4)
**Given** an early-exit path (e.g. empty inbox)
**When** the run ends
**Then** cli renders `organizer.empty_report()` — it never instantiates `OrganizeReport` itself (AR-7)

### Story 3.3: Run lifecycle and exit codes (FR-A8)

As a user,
I want deterministic exit codes and a fixed execution order,
So that scripts and graders can branch on outcomes confidently.

**Acceptance Criteria:**

**Given** any invocation
**When** cli runs
**Then** it executes parse → train? → scan → empty-check → load → organize → render (AD-13)
**Given** a missing input dir
**When** the run executes
**Then** exit is 1, validated in `cli.run` before side effects (FR-A8)
**Given** `load()` fails (TensorFlow absent or offline) on a non-dry run
**When** the run executes
**Then** exit is 2 — all model/network I/O lives inside `load()` (FR-A8, AR-6)
**Given** reported refused/failed/skipped outcomes
**When** the run ends
**Then** exit is 0 (FR-A8)
**And** a report prints before every return (AD-13)

### Story 3.4: Dry-run that touches nothing (FR-A6)

As a user,
I want a preview run that survives a broken environment,
So that I can demo the tool anywhere without risk.

**Acceptance Criteria:**

**Given** `--dry-run` with TensorFlow installed
**When** the run executes
**Then** planned moves print, destination dirs are computed against a virtual tree, and the filesystem is byte-identical afterward — zero mkdir/move/cache-priming writes (AD-13, AC-A1)
**Given** `--dry-run` with TensorFlow uninstalled
**When** the run executes
**Then** every scanned file is planned to `unsorted` with a visible warning, exit 0 (FR-A6, AC-A9)
**Given** backend down on a **non**-dry run
**When** the run executes
**Then** exit is 2 with no partial moves (Story 3.3 ordering) — no fallback name appears in `MODEL_BACKENDS` (AR-6)

### Story 3.5: Fixture accuracy and calibrated floors

As a grader,
I want placement accuracy on a labelled fixture,
So that mapping quality is measurable, not asserted.

**Acceptance Criteria:**

**Given** `--fixture tests/fixtures/labeled/` with 10 images across the 5 categories (2 each)
**When** the run completes
**Then** the report shows placement accuracy and per-category counts, comparing `read_fixture_labels()` expectations from `organizer` against actual placement (FR-A7, AR-13)
**Given** `config.ACCURACY_FLOOR` and `config.UNSORTED_SHARE_FLOOR`
**When** a test run asserts them
**Then** the values are PRD AC-A6/AC-A7 first-pass numbers (6/10, 0.80) pending OQ-1 recalibration
**And** floors are compared in tests only, never inside organizer/cli logic

### Story 3.6: Idempotency and TF-free QA suite (NFR-A1, NFR-A3)

As QA,
I want the organizer suite green with TensorFlow absent and re-runs that change nothing,
So that file-handling guarantees are proven on any machine.

**Acceptance Criteria:**

**Given** an organized output tree and empty inbox
**When** the tool re-runs
**Then** the output tree is byte-identical (AC-A10, NFR-A3) — the output root is excluded from scans (AR-13 exclude pattern)
**Given** restored files with colliding names
**When** the tool re-runs
**Then** FR-A5 suffixing applies — never overwrite (NFR-A3)
**Given** TensorFlow not installed
**When** `uv run --with pytest pytest -q` runs
**Then** the organizer/scan/report/lifecycle suite passes (AC-A5) and TF backend tests skip in their own module (AR-8)
**And** all AC outcomes for Epics 1–3 have automated coverage where feasible

## Epic 4: Train & Use the Custom CNN

Users bring their own trained model: `--train` builds the lab CNN from a labeled tree, and `--model-path` switches inference to that artifact.

### Story 4.1: Training lifecycle (FR-A9)

As a user,
I want `--train <root>` to fit the lab CNN and save an artifact before organizing starts,
So that I can train once and reuse the model safely.

**Acceptance Criteria:**

**Given** `<root>/<category>/*.jpg` with ~10 images per category
**When** `--train <root>` runs (no `--dry-run`)
**Then** cli trains **before** scanning (inbox not required), writing only to the `--model-path` location (`config.DEFAULT_MODEL_PATH` default `models/custom-cnn.keras`) — the sole NFR-A3 exception (AD-11, AD-13)
**Given** `--train` together with `--dry-run`
**When** the run executes
**Then** training is skipped with a warning and zero writes occur (AD-13)
**Given** a missing/bad train root
**When** training starts
**Then** exit is 1; given model/TF failure during training, exit is 2 (AD-13)
**And** training reports its own summary and returns without running the organize loop (AD-13)

### Story 4.2: custom-cnn backend via --model-path (FR-A2, NFR-A4)

As a user,
I want the trained artifact loadable through the same classifier interface,
So that `--backend custom-cnn` behaves exactly like the default backend.

**Acceptance Criteria:**

**Given** an artifact produced by Story 4.1
**When** `--backend custom-cnn --model-path <path>` runs
**Then** the model loads and `predict()` returns a five-element distribution over `config.CATEGORIES` (AD-10) — a binary-output artifact is rejected at `load()` as unavailable
**And** the architecture matches the lab: Conv2D → MaxPooling2D → Flatten → Dense (binary or categorical cross-entropy) (PRD FR-A2, §3)
**Given** `--model-path` omitted
**When** custom-cnn loads
**Then** it uses `config.DEFAULT_MODEL_PATH`; that literal appears nowhere else (AD-11)
**And** AC-A11's inference half passes: category + confidence returned

### Story 4.3: Demo readiness and OQ calibration

As the presenter,
I want every AC demonstrable and floors calibrated before the defense,
So that the tool passes QA and survives live questioning.

**Acceptance Criteria:**

**Given** the complete tool
**When** the full test suite and a live demo run complete
**Then** AC-A1..A11 all pass; the mobilenet weight cache is pre-warmed (AR-12) with the documented offline behavior (exit 2 non-dry / fallback dry) verified
**Given** first-implementation accuracy results
**When** OQ-1 review happens
**Then** `ACCURACY_FLOOR` / `UNSORTED_SHARE_FLOOR` are updated to calibrated values and Tech Lead sign-off is recorded before QA locks tests (OQ-1)
**Given** OQ-2's decision
**When** defense prep completes
**Then** whether `--train` is live-demoed or architecture-only is recorded in the docs (OQ-2)
**And** `docs/system-architecture.md` narrative is synced with the final spine (Deferred) or explicitly deferred with rationale
