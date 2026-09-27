# System Architecture — Meme & Reaction Image Organizer

**Project:** `meme-classifier/` · **Deliverable:** Project A — Image Detection
**Author:** Architect Agent · **Status:** Baseline v1.0 · **Date:** 2026-09-27
**Companion (this folder):** `product-requirements.md` (FR IDs referenced throughout) · `bmad-plan.md`
**Sibling project architecture:** `../../spam-detector/docs/system-architecture.md`

---

## 1. Global Decisions

| # | Decision | Rationale |
|---|---|---|
| AD-1 | **Kebab-case folders** (`meme-classifier/`, `spam-detector/`, `docs/`); **snake_case modules** (`organizer.py`, `model.py`) | Explicit project convention; hyphens are illegal in Python identifiers, so importable module *files* stay snake_case (PEP 8) |
| AD-2 | **Flat module layout** inside each project (no nested package) | Small scope; `main.py` runs from project root; `conftest.py` fixes pytest imports |
| AD-3 | Shared patterns across projects: `config.py` (constants) → domain modules → `cli.py` (argparse) → `main.py` (entry) | Consistent, reviewable structure |
| AD-4 | ML backends isolated behind an **ABC interface**; file/metrics logic has zero ML dependency | QA can test organizer + metrics without TensorFlow; swap backends without touching orchestration |
| AD-5 | All AI prompts append-only logged in root `PROMPTS_LOG.md` | Professor requirement |

---

## 2. Project A — `meme-classifier/`

### 2.1 Module Map

```
meme-classifier/
├── main.py            # entry: raise SystemExit(main())
├── cli.py             # argparse, orchestration loop, report printing   [FR-A1..A8]
├── config.py          # categories, extensions, thresholds, default dirs
├── classifier.py      # BaseClassifier ABC + MobileNetV2 / CustomCNN backends [FR-A2, A3]
├── organizer.py       # scan + shutil.move + collision-safe naming      [FR-A4..A7] (stdlib only)
├── conftest.py        # pytest sys.path bootstrap
├── tests/
│   └── test_organizer.py
├── data/
│   ├── README.md
│   ├── inbox/         # drop unorganized images here
│   └── organized/     # output root (category subfolders created at runtime)
├── docs/              # PRD, this architecture doc, BMAD plan (agent context root)
├── requirements.txt
└── README.md
```

**Dependency rule (no cycles):** `main → cli → {classifier, organizer} → config`

### 2.2 Data Flow

```
inbox/ ──scan_images──▶ [Path] ──classifier.predict──▶ ClassificationResult
                              │                          (category, confidence, backend)
                              └──────── organize(jobs) ──▶ organized/<category>/<file>
                                        │                    + OrganizeReport (counts)
                                        └──-- --dry-run ──▶ report only, zero writes
```

### 2.3 Backend Strategy (FR-A2)

| Backend | Mechanism | Needs training data? | Status |
|---|---|---|---|
| `mobilenet` (default) | `tf.keras.applications.MobileNetV2(weights="imagenet")` → ImageNet label → category mapping table (e.g. `barbell → gym-memes`, `tabby/Egyptian_cat → cat-memes`), low max-prob → `unsorted` | No — zero-shot | **Dev Agent TODO** |
| `custom-cnn` | Lab-reference CNN: `Conv2D → MaxPooling2D → Flatten → Dense(softmax, categorical cross-entropy)`, trained on a user-labeled folder tree, then reused for inference | Yes — user labels a training set | **Dev Agent TODO** |

Both implement:
```python
class BaseClassifier(ABC):
    def load(self) -> "BaseClassifier": ...
    def predict(self, image_path: Path) -> ClassificationResult: ...
```
`get_classifier(name)` factory validates against `config.MODEL_BACKENDS`. Missing TensorFlow or
untrained model raises `NotImplementedError` with a Dev-phase message → `cli` converts it to
exit code `2` (FR-A8).

### 2.4 Organizer Safety Rules (FR-A4..A7, NFR-A2/A3)

1. Category sanitized (`lower`, whitespace→`-`) then validated against the allow-list — rejects `..`, separators, absolute paths.
2. Destination = `output / category / filename`; if it exists → `stem-1.suffix`, `stem-2.suffix`, … (cap 1000).
3. Skip-on-error: one failing `shutil.move` is recorded and logged, never aborts the batch.
4. `OrganizeReport` accumulates `MoveRecord(source, destination, category, confidence, moved)` → summary table (FR-A7).
5. Scanning ignores hidden dirs and non-image extensions; corrupt images fail at predict-stage and land in `unsorted`/skipped, not fatal (AC-4).

---

## 3. Testing Strategy (QA Agent hand-off)

| Layer | Tests | TF needed? |
|---|---|---|
| organizer | scan filtering, dry-run no-write, collision rename, allow-list rejection, report counts | No |
| backends | mapping table coverage, threshold → `unsorted` (Dev Agent supplies fixtures) | Yes |
| adversarial (QA) | empty dir, zero-byte image, unicode filenames, permission-denied move | Mixed |

**Exit criteria:** `python -m compileall` clean · `pytest` green · no circular imports · type hints
on public APIs · every FR traceable to ≥1 test.
