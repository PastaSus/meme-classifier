# Adversarial General Review — `docs/product-requirements.md` (Baseline v1.0, 2026-09-27)

**Reviewer role:** Adversarial reviewer (PRD attack)
**Scope:** `docs/product-requirements.md` as primary target; `docs/system-architecture.md`, `docs/bmad-plan.md`, and current implementation (`classifier.py`, `cli.py`, `organizer.py`, `config.py`, `tests/`, `requirements.txt`, `README.md`) used as evidence.
**Environment facts verified during review (2026-09-27):**
- Python 3.14.6, TensorFlow **not installed** (`ModuleNotFoundError`).
- `py -m pip install --dry-run --only-binary=:all: "tensorflow>=2.15,<2.20"` → **`ERROR: No matching distribution found`** (the pin in `requirements.txt` is uninstallable on this interpreter).
- `py -m pip index versions tensorflow --pre --python-version 3.14` → only version available: **`2.22.0rc0`** (pre-release, pulls `keras-nightly`); no stable TF wheel exists for cp314.
- Both ML backends are `NotImplementedError` stubs (`classifier.py:95,103,124,133`); 17 tests cover organizer only.

**Verdict: REJECT — major revision required.** The PRD is *currently satisfiable end-to-end with zero machine learning working*, contains at least one self-contradiction between acceptance criteria and implementation/architecture, mandates an FR whose dependency stack cannot be installed under the project's own pinned requirements, and specifies no correctness measure for the classifier it exists to deliver. Each of these is a defense Q&A kill-shot.

---

## CRITICAL

### C1 — FR-A2 is unconditional, but its dependency stack is not installable as pinned; no contingency exists
**Cites:** §2.3 FR-A2 · §2.4 NFR-A1 · §4 Out of Scope

- FR-A2 requires both MobileNetV2 and custom CNN backends as *functional requirements*, with no qualifier ("where available", "Phase 4", etc.). Yet `requirements.txt:4` pins `tensorflow>=2.15,<2.20` — verified uninstallable on the committed Python 3.14.6 (`No matching distribution`), and TF is not installed. The only cp314 wheel that exists is the pre-release `tensorflow-2.22.0rc0` paired with `keras-nightly` — a moving target nobody should ship in a graded deliverable.
- The PRD states **no fallback backend** (no ONNX Runtime / tflite / PyTorch / scikit alternative), **no Python/TF version constraint**, **no environment requirement**, and **no acceptance path for "backend unavailable"**. FR-A8 defines exit code 2, but zero acceptance criteria exercise it — so a run that exits 2 and does nothing is "compliant".
- **Downstream burn:** the Dev epic for FR-A2 cannot be estimated or even started until someone decides (a) install the RC, (b) downgrade Python, or (c) change the backend — a decision the PRD owns and hasn't made. Architecture's "swap backends behind the ABC" (AD-4) presumes a swappable backend exists; it doesn't.
- **Defense Q&A:** *"Can you run your classifier right now?"* → No. *"Your requirements file installs?"* → Verified: no. Either answer ends the demo.

### C2 — No acceptance criterion requires the classifier to classify; all 5 ACs pass with `NotImplementedError` stubs
**Cites:** §2.3 FR-A2, FR-A3 · §2.5 Acceptance Criteria 1–5

- AC-1 (dry-run count), AC-2 (allow-listed folders), AC-3 (collision suffix), AC-4 (non-image ignored), AC-5 (`pytest` green without TF). Not one asserts **"this cat image ends in `cat-memes/`"**, or any classification behavior at all. Today, with both backends stubbed and TF absent, the entire AC set is passable (AC-1/AC-2/AC-3 are blocked only by an implementation ordering choice — see C3 — not by any PRD requirement). A file-mover with a hardcoded `unsorted` label satisfies this PRD.
- There is **no accuracy, precision, recall, coverage, or distribution requirement anywhere** — ironic given the sibling deliverable (per lab reference, PROMPTS_LOG INIT-001) explicitly mandates `accuracy_score`, `classification_report`, and `confusion_matrix`. A professor comparing the two projects will ask why the image classifier reports *nothing*.
- §1 promises the tool is "defensible in a professor Q&A session." A PRD whose acceptance criteria cannot distinguish "classifier" from "mv loop" is not defensible.
- **Downstream burn:** QA has no oracle to test against; epics derived from these ACs will encode "tests pass" instead of "classification correct," and the gap surfaces for the first time in the defense.

### C3 — AC-1 (the flagship demo) depends on a loadable backend; PRD never specifies dry-run behavior when the backend is unavailable
**Cites:** §2.3 FR-A6 · §2.5 AC-1 · §2.4 NFR-A1

- FR-A6 says `--dry-run` "prints the planned moves without touching disk" — but planned moves require a category, which requires classification. `cli.run()` loads the backend *before* organizing (`cli.py:116`), so in the committed environment `py main.py data/inbox --dry-run` exits `2` with no report at all. **AC-1 is unpassable as written on the machine the project runs on.**
- NFR-A1's stated rationale ("QA can test file handling anywhere") and AC-1's "folder is untouched" framing both imply dry-run is the environment-independent smoke test — yet the PRD nowhere says dry-run must work without TensorFlow, nor how a destination is planned when the backend is down (report everything as `unsorted`? placeholder? bail?).
- **Downstream burn:** Dev must invent dry-run-without-backend semantics; QA must guess which of two behaviors is correct. This is precisely the kind of ambiguity that becomes a "the spec said X" argument during review.

---

## HIGH

### H1 — ImageNet → 5 meme categories is semantically indefensible, and §1 contradicts §4 on how memes would ever be learned
**Cites:** §1 Product Overview · §2.2 Categories · §2.3 FR-A2 · §3 Traceability · §4 Out of Scope

- FR-A2 routes a **1000-class ImageNet label set** into five *cultural* categories. ImageNet has no "chaotic screenshot" or "wholesome post". The shipped mapping (`classifier.py:55-73`, 14 entries) shows the rot: `monitor → chaotic-screenshots`, `seashore → wholesome-posts`, `teddy → wholesome-posts` — content-free associations. Any real meme showing a person (ImageNet `person`, unmapped) goes to `unsorted`; a screenshot of a cat goes to `cat-memes` because of the *cat*, not the screenshot-ness.
- The PRD sets **no minimum coverage or expected category distribution**, so a run where 95% of images land in `unsorted/` meets AC-1 through AC-5 while delivering nothing. §2.2 even legitimizes this by defining `unsorted` as the catch-all.
- **Direct contradiction:** §1 claims the tool "classifies meme templates / reaction styles"; §4 puts "training a production-grade meme dataset model" out of scope. Between those two statements sits *no in-scope mechanism that ever learns what a meme is*. The custom CNN (FR-A2) needs labeled meme data (see H3) that the PRD also forbids obtaining. The professor's first question — *"so how does your model know what a chaotic screenshot is?"* — has no answer in this document.
- §3's traceability row "MobileNetV2 pre-trained on ImageNet → FR-A2" overstates the mapping: the lab requirement is ImageNet *classification output*; FR-A2 delivers meme categories *instead of* it. Traceability is asserted, not established.

### H2 — AC-4 contradicts the architecture and the implementation on corrupt images: "skipped" vs "moved to unsorted"
**Cites:** §2.5 AC-4 · §2.3 FR-A3 · (architecture §2.4.5, `cli.py:128-132`)

- AC-4: *"a corrupt image is logged and skipped, not fatal"* — the natural reading is the file **stays in the inbox**. Architecture §2.4.5 says corrupt files *"land in `unsorted`/skipped"* (two behaviors in one clause). The code actually **moves** them: any `predict()` exception becomes `OrganizeJob(category="unsorted", confidence=0.0)` (`cli.py:130-131`), which `organize()` then `shutil.move`s.
- These readings are mutually exclusive and **no test covers either**. A QA agent writing a test from AC-4 will fail the current implementation; a QA agent reverse-engineering from code will bake in behavior the AC denies. Worse, "corrupt" can only be detected *inside* the backend — which doesn't exist yet (C1) — so today corrupt detection has no implementation at all: extension-only scanning (`organizer.scan_images`) happily feeds text files to a classifier.
- **Downstream burn:** story acceptance for FR-A3/AC-4 cannot be written until this is resolved; whichever way it resolves, one of {PRD, architecture, code} is wrong.

### H3 — `custom-cnn` is an unimplementable requirement as specified
**Cites:** §2.3 FR-A2 · §2.4 NFR-A4 · §4 Out of Scope

- The CNN requires "a user-labeled folder tree" (architecture §2.3), but the PRD specifies **no training workflow whatsoever**: no `--train`/labeling FR, no data-ingestion contract, no minimum dataset size, no train/val split, no random seed, no evaluation, no saved-model artifact format or location.
- **NFR-A4 is already violated by the design:** "All config (paths, threshold, backend) overridable via CLI flags" — `CustomCNNClassifier.__init__(model_path=...)` exists, but the CLI exposes no `--model-path` flag and the PRD doesn't require one. A model file you cannot point at is not a config.
- **Circular data provenance:** the only on-disk folder tree matching the five category IDs is `data/organized/<category>/` — i.e., the output of the tool itself. Using it as training data means the classifier trains on its own prior guesses. The PRD neither acknowledges nor forbids this.
- §4's ban on "production-grade" training never defines where user-labeling *stops* being allowed — the scope boundary between FR-A2 and §4 is a razor.
- `bmad-plan.md` §5 risk register flags "No labeled meme dataset provided" — the *requirements* document, which is what epics get written from, does not.

### H4 — FR-A8 exit codes are untraced and contradicted by observed behavior; FR-A7's "errors" don't exist in the report contract
**Cites:** §2.3 FR-A7, FR-A8 · §2.5 (absence of AC) · §2.2 §2.4 NFR-A4

- **No acceptance criterion mentions an exit code.** `bmad-plan.md` §3 DoD #1 requires every FR traceable to testable ACs — FR-A8 fails this today, and FR-A7 only partially (no AC asserts report *content*).
- Behavior gaps a grader will hit: partial move failures (report shows `skipped`) still return **0** — is that "success"? Empty/missing input: missing dir → `1`, empty dir → `0` *with no report at all*, violating FR-A7's "after every run" (`cli.py:108-110`). `NotImplementedError` (not implemented) and missing TF (not installed) both collapse into exit `2`, indistinguishable to a caller — yet only the latter is arguably "backend unavailable".
- `--threshold` accepts any float (`-t 9` → everything to `unsorted`; `-t -1` → nothing) with no validation, despite NFR-A4 making it a first-class config surface.
- README documents `python main.py ...`, which on this machine is the broken Windows Store stub (AGENTS.md pitfall) — the documented demo command fails before the program starts.

---

## MEDIUM

### M1 — NFR-A3 (idempotency) has zero acceptance criteria and zero tests; duplicate-on-rerun semantics are unspecified
**Cites:** §2.4 NFR-A3 · §2.5

"Re-running on an already-organized folder does no damage" is doing a lot of unexamined work. The 17-test suite exercises none of it. Re-importing a restored inbox produces `cat-1.jpg`, `cat-2.jpg`, … duplicates (by design, FR-A5) — is that "no damage"? Running against `data/organized` itself is only safe because `scan_images(exclude=...)` happens to exclude the output root; if the user passes a *different* output dir than the default, `cli.run` excludes `args.output_dir` — verified only for the default nesting. "Run it twice" is the most common professor demo; this NFR is untested and ambiguous.

### M2 — Confidence semantics are undefined; §2.2 and FR-A3 disagree on what `unsorted` means
**Cites:** §2.2 Categories · §2.3 FR-A3

FR-A3 routes only *below-threshold* images to `unsorted`. §2.2 defines `unsorted` as "Low-confidence / **unrecognized**". A top-1 ImageNet label at 0.95 that isn't in the 14-entry mapping table is *high-confidence but unrecognized* — FR-A3 says nothing about it, so a literal implementation leaves it in its mapped-or-bust state. The default threshold `0.45` (`config.py:37`) appears nowhere in the PRD and has no rationale. What the score measures (max softmax? top-1 prob pre-mapping? post-mapping mass?) is never defined — so FR-A3 is not testable.

### M3 — FR-A7 promises "errors" the report cannot express
**Cites:** §2.3 FR-A7 · (architecture §2.4.4)

The report tracks planned/moved/skipped only; skips conflate policy rejections (bad category), missing sources, and `OSError` move failures into one bucket. There is no error count, no distinction between "refused" and "failed". FR-A7 as written is not implemented and not testable.

### M4 — Destructive moves with no persisted manifest, no undo — NFR-A3's "no damage" is unverifiable
**Cites:** §2.3 FR-A4 · §2.4 NFR-A3

`shutil.move` relocates originals; the audit trail (`OrganizeReport`) is printed and discarded. A misclassified file cannot be traced or bulk-reverted after the run. "What happens when it files 200 images wrong?" has no PRD answer. At minimum the PRD should require a run manifest (source → destination → category → confidence) — currently nothing in FR-A4..A7 or any NFR asks for it.

### M5 — Status board and PRD status are stale relative to actual implementation state
**Cites:** PRD header ("Status: Baseline v1.0") · (bmad-plan §2 phases 1/4/5)

Organizer + CLI + 17 tests are shipped and `README.md` says so, yet `bmad-plan.md` Phase 4 is "Pending" and Phase 1/2 claim Done via INIT-001 while the docs were relocated/rewritten in INIT-005. Epics and sprint planning derived from this board will mis-scope remaining work (backend decision = the real Phase 4, not "write the CNN").

### M6 — §3 traceability table is partial and misquotes the lab reference
**Cites:** §3 Lab Reference Traceability

Row 2 claims the lab specifies "categorical cross-entropy"; the verbatim lab text (PROMPTS_LOG INIT-001) says "**binary or categorical** cross-entropy loss". Row 1 claims MobileNetV2-on-ImageNet is satisfied by FR-A2, but FR-A2 substitutes meme categories for ImageNet outputs (H1). FR-A1, FR-A5, FR-A6, FR-A7, FR-A8 have no row at all (defensible as non-lab items) — but combined with H4's missing exit-code AC, the traceability story a professor can walk is thinner than §3 implies.

---

## LOW

### L1 — "Image file" is extension-only; adversarial cases live in architecture, not in the PRD's ACs
**Cites:** §2.3 FR-A1 · §2.5 AC-4
Zero-byte images, unicode filenames, permission-denied moves, `.jpg`-that-is-text appear only in architecture §3's QA table. The PRD's AC set (the contract QA actually grades against) omits them, so "adversarial cases covered" (bmad-plan DoD #4) is unanchored in requirements.

### L2 — AC-5's literal command doesn't run in this environment
**Cites:** §2.5 AC-5
"`pytest` passes with TensorFlow absent" — bare `pytest` is not installed in the `py` env (AGENTS.md: use `uv run --with pytest pytest -q`). As written, a grader following AC-5 verbatim gets command-not-found. Specify the invocation.

### L3 — Filesystem edge cases unaddressed
**Cites:** §2.3 FR-A4, FR-A5
Cross-device `shutil.move` (copy-then-delete) can leave a truncated destination on partial failure, which the collision renamer then treats as a real file; NTFS 260-char paths under deep `rglob`; Windows reserved names (`CON.jpg`); symlinks in the inbox. None acknowledged as accepted risks.

### L4 — Folder-name deviation from the lab prompt is tracked outside the PRD
**Cites:** §1 · §4
The kickoff prompt specified `meme_classifier/`; the build uses `meme_classifier/` → `meme-classifier/`. `bmad-plan.md` §5 logs the conflict; the PRD (the document a grader reads for scope) is silent. If naming compliance is graded, the justification is in the wrong artifact.

---

## What must change before this PRD can pass (ordered by downstream leverage)

1. **Resolve the environment/backend decision (C1):** pick and pin a runnable path (Python downgrade → TF 2.19/2.20, *or* accept the 2.22.0rc0 RC explicitly, *or* add a non-TF backend) and rewrite FR-A2 accordingly. Nothing else in the Dev phase is estimable until this exists.
2. **Add classification ACs with a measurable oracle (C2):** a tiny labeled fixture set (even 10 hand-picked images) with expected categories and a minimum pass rate; state what happens when the model misses it. Mirror the sibling project's evaluation posture (accuracy/per-class results at least reported).
3. **Specify dry-run-without-backend and corrupt-file disposition (C3, H2):** one sentence each, then make code, architecture, and AC-4 agree.
4. **Fix or remove `custom-cnn` (H3):** define the training FR (flag, data contract, artifact path, minimum data), or demote it to explicitly out-of-scope/deferred — but then §3's traceability row must say how the lab's CNN requirement is met (e.g., demonstrated architecture + smoke train on synthetic data).
5. **Close the metric/config gaps (M2, M3, H4):** define confidence, threshold validation, unrecognized-label routing, error reporting in FR-A7, and add exit-code ACs.

Until items 1–3 are done, epics and stories written from this PRD will encode its ambiguities as requirements — and the defense will surface them live.
