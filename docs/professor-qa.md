# Professor Q&A Sheet — Meme & Reaction Image Organizer

Short answers to the questions this project invites. Numbers are verified
(demo 2026-10-06); spec references point at `docs/product-requirements.md`.

## The model

**"Why does mobilenet put almost everything in `unsorted`?"**
By design (FR-A2/FR-A3). MobileNetV2 emits ImageNet labels; a shipped
15-entry table (`config.IMAGENET_LABEL_TO_CATEGORY`) maps a few of them
(`tabby` → cat-memes, `barbell` → gym-memes…) and *every unmapped label
routes to `unsorted` regardless of confidence*. Verified: Grumpy Cat hit
`cat-memes` at 79.5%; the other 10 real memes went to `unsorted` with reasons
(`unmapped label 'comic_book'`, `confidence 0.08 < 0.45`). The tool says "I
don't know" instead of guessing.

**"Why did the fixtures only score 20% on mobilenet?"**
The `tests/fixtures/labeled/` images are solid color blocks
(`tests/fixtures/make_labeled.py`) — MobileNet reads them as `matchstick` /
`wall_clock`, unmapped → unsorted. Synthetic fixtures test the *plumbing*,
never the mapping. Real calibration needs labeled real memes, which the
course did not provide (PRD §4) — hence OQ-1 below.

**"What are the 0.6 / 0.8 floors, and who decided them?"**
AC-A6 accuracy floor 0.6, AC-A7 unsorted-share ceiling 0.8
(`config.ACCURACY_FLOOR` / `UNSORTED_SHARE_FLOOR`). First-pass values kept
per Tech Lead decision 2026-10-04 (OQ-1); they change only on explicit
sign-off. Verified: custom-cnn on the demo tree scores 10/11 (90.9%) with
0% unsorted — inside both floors.

**"Why 0.45 threshold?"**
PRD default (FR-A3, NFR-A4), overridable via `-t/--threshold` in (0, 1].
Below it → `unsorted` with the exact comparison in the reason.

**"What does the custom CNN look like?"**
Lab-sheet architecture (FR-A2/FR-A9): Conv2D(32, 3×3, relu) → MaxPooling2D →
Flatten → Dense(softmax), categorical cross-entropy, adam; 64×64 RGB, 5
epochs, batch 16 (`classifier._TRAIN_*`). Trains on `<root>/<category>/`
trees via `--train`, saves one `.keras` artifact (default
`models/custom-cnn.keras`, gitignored — never committed).

**"Why did buff-doge land in chaotic-screenshots?"**
Nine samples and five epochs memorize; they don't understand. The white
background matched the white-background chaotic memes better than the gym
ones. Honest answer, and the fix is data, not code: more labeled images per
category (PRD assumes ~10 minimum).

**"Why don't the two stranger memes go to `unsorted` under custom-cnn?"**
Different honesty policies per backend. Mobilenet has an *unmapped* concept
(unknown label → unsorted). Custom-cnn outputs a distribution over exactly
the 4 trained categories, so strangers go to the *nearest*. If the defense
needs stranger-rejection on custom-cnn, that's future work (e.g. an
"everything below second-best margin → unsorted" rule).

## Engineering

**"Exit codes?"** 0 success · 1 bad path/filesystem · 2 backend unavailable
(non-dry). `--dry-run` with no backend plans everything to `unsorted` with a
warning, exit 0 (FR-A6). A report prints before *every* return, including
failures (FR-A7).

**"Overwrites? Re-runs?"** Never overwrites: `cat.jpg` → `cat-1.jpg` …
(FR-A5, cap 1000). Re-running on an empty inbox leaves the tree byte-identical
(AC-A10, tested). Corrupt images land in `unsorted` *with their reason* and
the batch continues (AC-A4).

**"No TensorFlow in the lab?"** The organizer/CLI scanning, moving, and
reporting layer is pure stdlib and fully tested without TF (NFR-A1); 190
tests, and the TF-gated ones skip cleanly. `--dry-run` is the flagship demo
precisely because it needs no backend.

**"Security?"** Phase 5 adversarial pass (3 lenses, 9 fixes, 32 regression
tests): decode pixel cap against decompression bombs, NaN-confidence routing,
threshold shape validation, path-traversal guards on categories *and*
filenames, blank-path and input==output rejection. Concurrency hardening was
rejected — single-user CLI, no such requirement.

**"Why no OCR / template recognition / YOLO?"** Explicitly out of scope
(PRD §4): no webcam/video, no OpenCV/Haar, no production dataset pipeline.
The mapping approach is the documented design choice, and its limits are
stated, not hidden.

## Process (BMAD)

**"How was this built?"** PM → PRD + acceptance criteria, Architect →
system-architecture + traceability, Dev → 17 stories across 4 epics, QA →
adversarial review + this defense kit. Every prompt logged verbatim,
append-only, in root `PROMPTS_LOG.md` (course requirement). Branch per story,
atomic Conventional Commits, PRs #13–#19.

**"With more time?"** Grow the mapping table from real misfiles; 10+
labeled images per category and re-calibrate OQ-1 floors on them; stranger-
rejection for custom-cnn; per-category thresholds; a `--report-only` audit
mode. In that order.
