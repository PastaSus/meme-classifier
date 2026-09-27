# Reconciliation — Lab Reference (Project A / Image Detection) vs PRD v2.0

**Source:** `../PROMPTS_LOG.md` → `[INIT-001]` (verbatim prompt, 2026-09-27)
**Target:** `docs/product-requirements.md` — Draft v2.0, 2026-09-27
**Scope:** Project A (Image Detection / Meme & Reaction Image Organizer) only. Project B (Spam) lab text excluded.

---

## 1. Verbatim extract — Project A lab reference

Two passages in the INIT-001 prompt constitute the Project A lab reference.

### 1a. Project statement (INIT-001, prompt body)

> Project 1 is an Image Detection project where we want to build a custom "Meme & Reaction Image Organizer". Instead of basic object detection, we are building a Python script using MobileNetV2 or a custom CNN model to analyze image files in an unorganized folder, classify meme templates or reaction styles (such as gym memes, cat memes, chaotic screenshots, or wholesome posts), and automatically organize them into corresponding labelled subfolders using Python's os and shutil modules. This project will live in Python Projects/meme_classifier/.

### 1b. Lab reference sheet — Image Detection pipeline (INIT-001, "exact reference text")

> For the Image Detection pipeline, the reference document covers multiple approaches including object detection with YOLOv8 via ultralytics, real-time webcam processing with OpenCV, face detection using Haar Cascades (haarcascade_frontalface_default.xml), image classification using MobileNetV2 pre-trained on ImageNet, and custom CNN classification built with TensorFlow/Keras using Conv2D, MaxPooling2D, Flatten, and Dense layers with binary or categorical cross-entropy loss.

**Atomic lab requirements derived (Project A):**

| # | Lab requirement (verbatim key phrase) |
|---|---|
| L1 | custom **"Meme & Reaction Image Organizer"** Python script |
| L2 | **MobileNetV2 or a custom CNN model** |
| L3 | analyze image files in an **unorganized folder** |
| L4 | classify **meme templates or reaction styles** (gym memes, cat memes, chaotic screenshots, wholesome posts) |
| L5 | organize into **corresponding labelled subfolders** |
| L6 | using Python's **os and shutil** modules |
| L7 | object detection with **YOLOv8 via ultralytics** |
| L8 | real-time **webcam** processing with **OpenCV** |
| L9 | face detection using **Haar Cascades (`haarcascade_frontalface_default.xml`)** |
| L10 | image classification using **MobileNetV2 pre-trained on ImageNet** |
| L11 | custom CNN with **TensorFlow/Keras**, **Conv2D, MaxPooling2D, Flatten, Dense** |
| L12 | **binary or categorical cross-entropy** loss |
| L13 | project lives in `Python Projects/meme_classifier/` |

---

## 2. Gap analysis vs PRD v2.0

### 2.1 Traceable and accurate

| Lab # | PRD v2.0 location | Verdict |
|---|---|---|
| L1 | Title, §1, §2 | OK |
| L2 | FR-A2 (`mobilenet` + `custom-cnn` backends) | OK — both alternatives preserved |
| L3 | §2.1, FR-A1 | OK in body (no §3 row — see G2) |
| L4 | §2.2 categories (`gym-memes`, `cat-memes`, `chaotic-screenshots`, `wholesome-posts`) + `unsorted` | OK in body; "meme templates" half narrowed — see G3 |
| L5 | §2.2, FR-A4 | OK |
| L6 | §2.1, FR-A4 (`shutil.move`, `os.makedirs`) | OK — quote accurate |
| L7 | §3 row 4, §4 bullet 1 | OK (declared out of scope) |
| L8 | §4 bullet 1 | OK ("Real-time webcam/video detection") — "OpenCV" dropped, see G5 |
| L9 | §3 row 4, §4 bullet 1 | OK — filename dropped, see G5 |
| L10 | §3 row 1, FR-A2 | OK wording; mechanism appended, see G4 |
| L11 | FR-A2, FR-A9, NFR-A5 (`TensorFlow 2.21.x`, `.keras`) | OK — layer order preserved |
| L12 | §3 row 2 quotes "**binary *or* categorical** cross-entropy (verbatim)" — but FR-A2 does not | **Inconsistent — G1** |
| L13 | Deviation to `meme-classifier/` | Documented in INIT-001 response (kebab-case directive) — **not a gap** |

Non-lab additions (FR-A5..A8, FR-A9 `--train`, thresholds, NFR-A5, exit codes, accuracy ACs) are all **labeled as `[ASSUMPTION]` / PRD decisions, not attributed to the lab** — no false attribution found. `unsorted` is presented as a PRD safety net (§2.2), not as lab text.

### 2.2 Gaps

- **G1 — Quote inconsistency on cross-entropy (L12).** FR-A2 (§2.3) describes the "`custom-cnn` — **lab CNN** (Conv2D → MaxPooling2D → Flatten → Dense, **categorical cross-entropy**)", dropping the lab's "**binary or**"; §3 row 2 quotes it correctly and asserts "(verbatim)". The lab's "binary or categorical" survives in only one of the two places that purport to restate the lab.

- **G2 — Traceability rows missing for two genuine lab items (L3, L4).** §3 has no row for "analyze image files in an unorganized folder" (→ FR-A1) nor for the four lab example categories (→ §2.2). Both are implemented, but a reader walking §3 alone cannot trace them back to the lab.

- **G3 — "classify meme templates" narrowed, not satisfied (L4).** §4 bullet 3 places "deep meme-template recognition beyond the label→category mapping" out of scope; no FR delivers template classification. Declared (not silent), but half of the lab's "meme templates **or** reaction styles" phrasing is deliberately unmet with no §3/lab row recording that decision.

- **G4 — PRD-invented mechanism presented as lab traceability (L10).** §3 row 1 appends "**(used via label→category mapping; unmatched → `unsorted`)**" and §1 claims "**zero-shot by design**" — the lab says nothing about a mapping, zero-shot inference, or `unsorted`. Design choices are fine, but §3's framing makes them read as lab-derived; the lab's "MobileNetV2 pre-trained on ImageNet" is only *partially* satisfied since outputs are substituted for meme categories.

- **G5 — Lab artifact specifics dropped from §4 (L7–L9).** The out-of-scope bullet omits "**via ultralytics**", "**OpenCV**", and the asset filename **`haarcascade_frontalface_default.xml`** — none of these exact lab tokens appear anywhere in the PRD, so a verbatim-comparison reader can't match three of the five lab approaches by keyword.

### 2.3 Summary

Nothing lab-required was removed silently from the PRD body, and no requirement was invented *and attributed* to the lab. The five gaps above are: one internal quote inconsistency (G1), two traceability-table omissions (G2, G5), one declared-but-unmet narrowing (G3), and one over-attributed design mechanism (G4).
