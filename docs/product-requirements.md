# Product Requirements Document (PRD) — Meme & Reaction Image Organizer

**Project:** `meme-classifier/` · **Deliverable:** Project A — Image Detection
**Author:** PM Agent · **Status:** Baseline v1.0 · **Date:** 2026-09-27
**Source of truth:** Lab reference sheet (encoded verbatim in root `PROMPTS_LOG.md` → INIT-001)
**Companion docs (this folder):** `system-architecture.md` · `bmad-plan.md`
**Sibling project PRD:** `../../spam-detector/docs/product-requirements.md`

---

## 1. Product Overview

**Meme & Reaction Image Organizer** is the *Image Detection* deliverable of a two-project
university semifinals case study. It analyzes image files sitting in an unorganized folder,
classifies meme templates / reaction styles, and files them into labelled subfolders.

The companion deliverable — **SMS Spam Classifier** (`spam-detector/`), the *Text Classification*
project — has its own PRD in `spam-detector/docs/`.

This project must run as a CLI program, be modular enough for code review, and be defensible
in a professor Q&A session.

---

## 2. Project A — Meme & Reaction Image Organizer

### 2.1 Problem
Users accumulate reaction images and memes in a single unorganized folder. Manual sorting is
tedious. The tool must analyze image files and automatically move them into labelled category
folders using Python's `os` and `shutil` modules.

### 2.2 Categories (labelled subfolders, kebab-case)
| Category ID | Description |
|---|---|
| `gym-memes` | Lifting, fitness, gym-rat humor |
| `cat-memes` | Cat templates and reaction cats |
| `chaotic-screenshots` | Absurd, unhinged, cursed screenshots |
| `wholesome-posts` | Wholesome, feel-good, kind content |
| `unsorted` | Low-confidence / unrecognized images (safety net) |

### 2.3 Functional Requirements
- **FR-A1:** Scan a user-specified input folder for image files (`.jpg .jpeg .png .gif .bmp .webp`), optionally recursive.
- **FR-A2:** Classify each image via a selectable backend: **MobileNetV2** (pre-trained on ImageNet) or a **custom CNN** (Conv2D → MaxPooling2D → Flatten → Dense, categorical cross-entropy) per the lab reference.
- **FR-A3:** Assign each image a category + confidence score; anything below the confidence threshold goes to `unsorted`.
- **FR-A4:** Move files into `<output>/<category>/` subfolders with `shutil.move`, creating directories on demand (`os.makedirs`).
- **FR-A5:** Never overwrite existing files — colliding names get a numeric suffix (`meme-1.jpg`).
- **FR-A6:** `--dry-run` mode prints the planned moves without touching disk.
- **FR-A7:** Print a per-category summary report (counts, skipped, errors) after every run.
- **FR-A8:** Exit codes: `0` success, `1` runtime error, `2` backend unavailable.

### 2.4 Non-Functional Requirements
- **NFR-A1:** Organizer logic (scan/move/report) must work **without TensorFlow installed** (pure stdlib) so QA can test file handling anywhere.
- **NFR-A2:** Path-traversal-safe category names — only sanitized, allow-listed categories accepted.
- **NFR-A3:** Idempotent: re-running on an already-organized folder does no damage.
- **NFR-A4:** All config (paths, threshold, backend) overridable via CLI flags.

### 2.5 Acceptance Criteria
1. Given an inbox of 10 mixed images + `--dry-run`, the report lists 10 planned moves and the folder is untouched.
2. A real run creates only allow-listed category folders and moves every scanned image exactly once.
3. Two images with the same filename land as `cat.jpg` and `cat-1.jpg` — no overwrite.
4. A non-image file (`.txt`) is ignored; a corrupt image is logged and skipped, not fatal.
5. `pytest` passes with TensorFlow absent.

---

## 3. Lab Reference Traceability (Project A)

| Lab reference requirement | FR |
|---|---|
| MobileNetV2 pre-trained on ImageNet | FR-A2 |
| Custom CNN: Conv2D/MaxPooling2D/Flatten/Dense, categorical cross-entropy | FR-A2 |
| `os` + `shutil` folder organization | FR-A4 |
| *(YOLOv8, webcam, Haar cascades — covered as reference knowledge, out of build scope)* | Out of scope §4 |

## 4. Out of Scope (explicitly)
- Real-time webcam/video detection, YOLOv8 object detection, Haar-cascade face detection (lab reference context only — will be discussed in defense, not built).
- Training a production-grade meme dataset model; mobile deployment; web UI; database.
