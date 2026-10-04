# Product Requirements Document (PRD) — Meme & Reaction Image Organizer

**Project:** `meme-classifier/` · **Deliverable:** Project A — Image Detection
**Author:** PM Agent · **Status:** Final v2.0 · **Date:** 2026-09-27
**Source of truth:** Lab reference sheet (encoded verbatim in root `PROMPTS_LOG.md` → INIT-001)
**Validation:** `_bmad-output/planning-artifacts/prds/prd-meme-classifier-2026-09-27/validation-report.md` (Grade: Poor → findings applied in this revision)
**Companion docs (this folder):** `system-architecture.md` · `bmad-plan.md`
**Sibling project PRD:** `../../spam-detector/docs/product-requirements.md`

---

## 1. Product Overview

**Meme & Reaction Image Organizer** is the *Image Detection* deliverable of a two-project
university semifinals case study. It analyzes image files sitting in an unorganized folder,
assigns each one a category, and files them into labelled subfolders.

Classification is **zero-shot by design**: a pre-trained ImageNet model (MobileNetV2) resolves
each image to a label, and a shipped label→category mapping turns that label into one of the
five categories; the lab-mandated custom CNN operates on a trained artifact when provided
(FR-A2, FR-A9). Images whose label is unmatched, low-confidence, or unreadable go to
`unsorted`. Deep meme-culture understanding (template recognition, OCR of impact font) is
**explicitly out of scope** (§4) — the tool recognizes what the mapping covers, and nothing
pretends otherwise.

This project must run as a CLI program, be modular enough for code review, and be defensible
in a professor Q&A session.

---

## 2. Project A — Meme & Reaction Image Organizer

### 2.1 Problem

Users accumulate reaction images and memes in a single unorganized folder. Manual sorting is
tedious. The tool must analyze image files and automatically move them into labelled category
folders using Python's `os` and `shutil` modules.

**Defaults:** input `data/inbox/` (any path accepted as the positional argument), output
`data/organized/` (`-o/--output`), recursion off (`-r` enables) `[ASSUMPTION: recursion defaults to off]`.

### 2.2 Categories (labelled subfolders, kebab-case)

| Category ID | Description |
|---|---|
| `gym-memes` | Lifting, fitness, gym-rat humor |
| `cat-memes` | Cat templates and reaction cats |
| `chaotic-screenshots` | Absurd, unhinged, cursed screenshots |
| `wholesome-posts` | Wholesome, feel-good, kind content |
| `unsorted` | Safety net: low-confidence, label not in the mapping, or unreadable/corrupt |

### 2.3 Functional Requirements

- **FR-A1:** Scan the input folder for image files (`.jpg .jpeg .png .gif .bmp .webp`), optionally recursive; non-image files ignored; missing input directory is an error (exit 1).
- **FR-A2:** Classify each image via a selectable backend behind a single interface:
  - **`mobilenet` (default)** — MobileNetV2 pre-trained on ImageNet; top-1 label resolved through a shipped label→category mapping; **any label not in the mapping routes to `unsorted`** regardless of confidence.
  - **`custom-cnn`** — lab CNN (Conv2D → MaxPooling2D → Flatten → Dense, **binary *or* categorical** cross-entropy — verbatim lab wording) loaded from a trained artifact via `--model-path`.
- **FR-A3:** Assign each image a category + confidence score (top-1 probability of a mapped label). **Default threshold 0.45**, valid range (0, 1], `--threshold` overridable (NFR-A4). Below threshold → `unsorted`; a high-confidence but unmapped label → `unsorted` (see §2.2).
- **FR-A4:** Move files into `<output>/<category>/` with `shutil.move`, creating directories on demand (`os.makedirs`).
- **FR-A5:** Never overwrite existing files — colliding names get a numeric suffix (`meme-1.jpg`).
- **FR-A6:** `--dry-run` prints the planned moves without touching disk. **Works even when the backend is unavailable**: every scanned file is planned to `unsorted` with a visible warning, exit 0 (keeps the flagship demo environment-independent).
- **FR-A7:** Print a summary report after **every** run (including empty input): per-category planned/moved counts, skipped count, **errors count with reasons** (refused vs failed distinguished), and — when a labelled fixture is supplied — placement accuracy.
- **FR-A8:** Exit codes: `0` success (reported skips included), `1` runtime/filesystem error (e.g. missing input dir), `2` backend unavailable on a non-dry run.
- **FR-A9:** `--train <root>` trains the custom CNN on a user-labeled folder tree (`<root>/<category>/*.jpg`), saves the artifact to `--model-path` (default `models/custom-cnn.keras`); the same flag loads the artifact for inference (closes NFR-A4). `[ASSUMPTION: minimum ~10 labeled images per category to train]` Training on `data/organized/` is permitted but acknowledged as training on the tool's own prior output — user's choice, not a recommended workflow.

### 2.4 Non-Functional Requirements

- **NFR-A1:** Organizer logic (scan/move/report) must work **without TensorFlow installed** (pure stdlib) so QA can test file handling anywhere.
- **NFR-A2:** Path-traversal-safe category names — only sanitized, allow-listed categories accepted.
- **NFR-A3:** Idempotent: re-running with an empty inbox leaves the output tree byte-identical; **zero writes ever occur outside the output root** — excepting the trained-model artifact written by `--train` under `models/` (FR-A9; spine AD-11/AD-13); a restored inbox re-files via FR-A5 suffixing, never overwrites.
- **NFR-A4:** All config (paths, threshold, backend, model artifact) overridable via CLI flags — including `--model-path`.
- **NFR-A5:** **Environment:** Python **3.13**, managed project-locally by `uv` (system Python untouched); **stable TensorFlow 2.21.x** (verified 2026-09-27: no stable TF wheel exists for Python 3.14 — the earlier `<2.20` pin is retired). Organizer and tests remain TF-free (NFR-A1).

### 2.5 Acceptance Criteria

1. **AC-A1** — Given an inbox of 10 mixed images + `--dry-run`, the report lists 10 planned moves and the folder is untouched.
2. **AC-A2** — A real run creates only allow-listed category folders and moves every scanned image exactly once.
3. **AC-A3** — Two images with the same filename land as `cat.jpg` and `cat-1.jpg` — no overwrite.
4. **AC-A4** — A non-image file (`.txt`) is ignored; a corrupt image is **logged and moved to `unsorted` with its reason recorded** — run continues, not fatal.
5. **AC-A5** — `uv run --with pytest pytest -q` passes with TensorFlow absent.
6. **AC-A6** — On a labelled fixture of 10 images (5 categories, 2 each) the run **reports placement accuracy and per-category counts, and accuracy ≥ 6/10** `[ASSUMPTION: 6/10 floor is first-pass; final number calibrated after first implementation run — see OQ-1]`.
7. **AC-A7** — Counter-metric: **≤ 80% of a mixed run lands in `unsorted`** `[ASSUMPTION: 80% first-pass — see OQ-1]` (blocks the dump-everything escape hatch).
8. **AC-A8** — Exit codes: success → `0` (including reported skips); missing input dir → `1`; backend unavailable on a non-dry run → `2`.
9. **AC-A9** — `--dry-run` with TensorFlow uninstalled: files listed, all planned to `unsorted`, warning printed, exit `0`.
10. **AC-A10** — Idempotency: re-run on an already-organized folder (inbox empty) leaves the tree byte-identical (NFR-A3).
11. **AC-A11** — `--train` on a labeled folder tree produces a loadable artifact, and `--model-path` inference returns category + confidence (FR-A9).

### 2.6 Open Questions

- **OQ-1:** Final values for the AC-A6 accuracy floor and AC-A7 `unsorted` share — calibrated after the first implementation run, Tech Lead sign-off required before QA locks tests.
  - **Decided 2026-10-04 (Story 4.3):** keep `ACCURACY_FLOOR=0.6` / `UNSORTED_SHARE_FLOOR=0.8`;
    real calibration pending labeled real memes (synthetic fixtures cannot measure mapping
    quality). Floors change only on explicit Tech Lead sign-off.
- **OQ-2:** Is live `--train` demoed at the defense, or is the CNN covered architecture-only? (determines whether FR-A9 is must-demo or must-exist)
  - **Decided 2026-10-04 (Story 4.3):** live `--train` demoed (seconds, offline-safe) with a
    pre-built artifact as fallback — FR-A9 is must-demo.

### 2.7 Glossary

| Term | Meaning |
|---|---|
| **Category** | One of the five allow-listed output folder IDs (§2.2) |
| **Backend** | Selectable classifier implementation behind one interface: `mobilenet` (default) or `custom-cnn` |
| **Confidence** | Top-1 probability of a mapped label; below threshold → `unsorted` (FR-A3) |
| **Inbox** | The scanned input folder — defaults to `data/inbox/` |
| **Organizer** | Stdlib-only scan/move/report layer (`organizer.py`) |
| **Label→category mapping** | Shipped table resolving ImageNet labels to category IDs; unmatched → `unsorted` |

---

## 3. Lab Reference Traceability (Project A)

| Lab reference requirement | FR |
|---|---|
| Analyze image files in an unorganized folder | FR-A1 |
| MobileNetV2 pre-trained on ImageNet | FR-A2 *(label→category mapping is our design choice, not lab-derived — unmatched labels → `unsorted`)* |
| Custom CNN: Conv2D/MaxPooling2D/Flatten/Dense; **binary *or* categorical** cross-entropy (verbatim) | FR-A2, FR-A9 |
| Lab example categories (gym / cat / chaotic / wholesome) → §2.2 folder IDs | §2.2 |
| `os` + `shutil` folder organization | FR-A4 |
| *(YOLOv8, webcam, Haar cascades — covered as reference knowledge, out of build scope)* | Out of scope §4 |

## 4. Out of Scope (explicitly)

- Real-time webcam/video detection, YOLOv8 object detection **via ultralytics**, OpenCV processing, Haar-cascade face detection with `haarcascade_frontalface_default.xml` (lab reference context only — discussed in defense, not built).
- Training a production-grade meme dataset model — FR-A9 trains only on user-labeled folders, on demand; no production dataset pipeline.
- OCR / text reading of meme captions; deep meme-template recognition beyond the label→category mapping.
- **No labelled training dataset is provided by the course; no accuracy guarantee beyond the AC-A6 floor.**
- Mobile deployment; web UI; database.
