# Validation Report — Meme & Reaction Image Organizer (PRD Baseline v1.0)

- **PRD:** `docs/product-requirements.md`
- **Rubric:** `.agents/skills/bmad-prd/assets/prd-validation-checklist.md`
- **Run at:** 2026-09-27T18:16:09+08:00
- **Grade:** Poor

## Overall verdict

**Adequate (rubric).** This is a tight, honest capability spec that fits its academic CLI brief: concrete FRs with named mechanisms (`shutil.move`, `os.makedirs`, exit codes), product-specific NFRs (stdlib-only organizer, path-traversal allow-list), a Non-Goals section that does real work, and a lab-reference traceability table built for the professor Q&A it names. What's at risk is the center of the product: FR-A2 claims to "classify meme templates / reaction styles" using an ImageNet classifier whose label space contains none of the five categories, and neither that mapping nor the FR-A3 confidence threshold value appears anywhere in the PRD — both were resolved silently in `system-architecture.md` §2.3. Done-ness and scope honesty are the weak dimensions; shape fit and substance are the strengths.

**REJECT (adversarial) — major revision required.** The PRD is currently satisfiable end-to-end with zero machine learning working; FR-A2's dependency stack (`tensorflow>=2.15,<2.20`) is verified uninstallable on the committed Python 3.14.6 with no contingency; no acceptance criterion requires classification to actually happen; and the flagship dry-run demo (AC-1) exits 2 in the current environment because dry-run-without-backend behavior is unspecified. Each of these is a defense Q&A kill-shot.

## Dimension verdicts

- Decision-readiness — thin
- Substance over theater — strong
- Strategic coherence — adequate
- Done-ness clarity — adequate
- Scope honesty — thin
- Downstream usability — adequate
- Shape fit — strong

## Findings by severity

### Critical (3)

**[Adversarial] C1 — FR-A2 unconditional, but dependency stack not installable as pinned; no contingency (§2.3 FR-A2 · §2.4 NFR-A1 · §4)**
FR-A2 requires both backends as functional requirements, yet `requirements.txt` pins TF `<2.20` — verified `No matching distribution` on Python 3.14.6 (only `2.22.0rc0` exists for cp314). No fallback backend, no version constraint, no acceptance path for "backend unavailable": FR-A8's exit code 2 has zero ACs, so a run that exits 2 and does nothing is "compliant". The Dev epic cannot be started until someone picks (a) install the RC, (b) downgrade Python, or (c) change backend — a decision the PRD owns.
Fix: Resolve the environment/backend decision first and rewrite FR-A2 accordingly; nothing else in the Dev phase is estimable until this exists.

**[Adversarial] C2 — No acceptance criterion requires the classifier to classify; all 5 ACs pass with NotImplementedError stubs (§2.3 FR-A2, FR-A3 · §2.5 AC 1–5)**
AC-1..AC-5 verify dry-run counts, folder allow-listing, collisions, non-image skips, pytest green. Not one asserts "this cat image ends in `cat-memes/`". No accuracy/precision/recall requirement anywhere — the sibling deliverable mandates `accuracy_score`, `classification_report`, `confusion_matrix`. A file-mover with a hardcoded `unsorted` label satisfies this PRD; QA gets no oracle.
Fix: Add classification ACs with a measurable oracle — a small labeled fixture set (even 10 images) with expected categories and a minimum pass rate; report per-category results.

**[Adversarial] C3 — AC-1 (flagship demo) depends on a loadable backend; dry-run-unavailable behavior unspecified (§2.3 FR-A6 · §2.5 AC-1 · §2.4 NFR-A1)**
`cli.run()` loads the backend before organizing, so in the committed environment `py main.py data/inbox --dry-run` exits 2 with no report — AC-1 is unpassable as written on this machine. The PRD nowhere says dry-run must work without TensorFlow, nor how a destination is planned when the backend is down.
Fix: Specify dry-run-without-backend semantics in one sentence, then make code, architecture, and AC-1 agree.

### High (5)

**[Done-ness clarity] FR-A2's central operation is undefined in the PRD (§1; §2.3 FR-A2)**
MobileNetV2 cannot emit `gym-memes`/`cat-memes` without a label→category mapping, none specified here; the CNN is only layer names with no input size, units, or training-data source. Mapping appears only downstream as "Dev Agent TODO". An engineer cannot state "done" for the primary FR from this document.
Fix: Specify the mapping rule and one testable condition per backend, or explicitly delegate with `[NOTE FOR PM]`.

**[Adversarial] H1 — ImageNet → 5 meme categories semantically indefensible; §1 contradicts §4 (§1 · §2.2 · §2.3 · §3 · §4)**
Shipped mapping shows the rot (`monitor → chaotic-screenshots`, `seashore → wholesome-posts`); no minimum coverage, so 95% landing in `unsorted` meets every AC. §1 claims meme classification while §4 forbids training a meme model — no in-scope mechanism ever learns what a meme is.
Fix: Reconcile §1/§4, add minimum coverage / unsorted-rate bounds, correct §3's wording.

**[Adversarial] H2 — AC-4 contradicts architecture and implementation on corrupt images (§2.5 AC-4 · §2.3 FR-A3)**
AC-4: "logged and skipped" (stays in inbox); architecture: "land in `unsorted`/skipped"; code: *moves* them (`predict()` exception → `category="unsorted"`). Three mutually exclusive readings, no test covers either. One of {PRD, architecture, code} is wrong.
Fix: Pick one disposition, one sentence, then align AC-4, architecture §2.4.5, and `cli.py`.

**[Adversarial] H3 — custom-cnn unimplementable as specified (§2.3 FR-A2 · §2.4 NFR-A4 · §4)**
No training workflow at all: no labeling FR, data contract, min dataset, split/seed/evaluation, artifact format. NFR-A4 already violated: `model_path` exists in code but no CLI flag. Circular provenance: the only labeled tree on disk is the tool's own output.
Fix: Define the training FR or demote custom-cnn to explicitly deferred — then §3 must say how the lab's CNN requirement is met.

**[Adversarial] H4 — FR-A8 exit codes untraced and contradicted; FR-A7's "errors" don't exist in the report contract (§2.3 FR-A7, FR-A8 · §2.5)**
No AC mentions an exit code (bmad-plan DoD #1 fails). Partial failures still return 0; empty dir returns 0 with no report (violates FR-A7 "after every run"); `NotImplementedError` and missing TF both collapse into exit 2. `--threshold` accepts any float.
Fix: Add exit-code ACs, define report error semantics, validate `--threshold` range.

### Medium (12)

**[Decision-readiness] No open-items mechanism at real tensions (whole PRD; §2.3 FR-A2/FR-A3)**
Zero Open Questions / `[NOTE FOR PM]` / `[ASSUMPTION]` anywhere while the mapping and threshold sit undecided in this document.
Fix: Open Questions section (mapping rule, default threshold, default backend) + `[NOTE FOR PM]` on FR-A2.

**[Strategic coherence] Success criteria don't validate the classification thesis (§2.5 AC 1–5)**
All five ACs verify plumbing; none verifies categorization; no `unsorted`-rate counter-metric guards the dump-everything escape hatch.
Fix: Add one AC on a labelled sample (≥7 of 10 expected placements) + counter-metric bounding `unsorted` share.

**[Done-ness clarity] "Confidence threshold" has no value and no AC exercises it (§2.3 FR-A3; §2.5)**
Default and range unstated; no AC covers the below-threshold path.
Fix: State the default (config constant, flag-overridable) + AC: below-threshold → `unsorted` with reason logged.

**[Done-ness clarity] AC coverage gaps for FR-A2 and FR-A8 (§2.5 vs §2.3)**
Nothing accepts "backends selectable and produce category + confidence" or "exit codes 0/1/2 behave as specified".
Fix: ACs for `--backend` switch honored; missing TF → exit 2.

**[Scope honesty] Omissions are inferred, not flagged (whole PRD; §2.3–§2.4)**
Reader must infer threshold default, output-dir default, recursion default, training-data source, OCR stance — no `[ASSUMPTION]` tags exist.
Fix: Assumptions Index with 3–4 inline tags + Open Questions section.

**[Downstream usability] No glossary; domain nouns under-defined and drifting (§2.3 FR-A3; §2.1)**
"confidence threshold" undefined; PRD says "user-specified input folder" while arch fixes `data/inbox/`.
Fix: 5-term glossary; align §2.1 with arch paths.

**[Adversarial] M1 — NFR-A3 (idempotency) has zero ACs and zero tests (§2.4 NFR-A3 · §2.5)**
Re-import produces `cat-1.jpg` duplicates — is that "no damage"? "Run it twice" is the most common professor demo; untested and ambiguous.

**[Adversarial] M2 — Confidence semantics undefined; §2.2 and FR-A3 disagree on unsorted (§2.2 · §2.3 FR-A3)**
High-confidence-but-unrecognized labels handled by neither clause; default 0.45 lives in code, not the PRD; what the score measures is undefined — FR-A3 is not testable.

**[Adversarial] M3 — FR-A7 promises "errors" the report cannot express (§2.3 FR-A7)**
Report has planned/moved/skipped only; skips conflate policy rejections, missing sources, and `OSError` failures.

**[Adversarial] M4 — Destructive moves with no persisted manifest, no undo (§2.3 FR-A4 · §2.4 NFR-A3)**
Audit trail is printed and discarded; a misclassified file cannot be traced or reverted. No run manifest required anywhere.

**[Adversarial] M5 — Status board and PRD status stale relative to implementation (PRD header; bmad-plan §2)**
Organizer + CLI + 17 tests shipped, yet bmad-plan Phase 4 "Pending". Epics derived from this board will mis-scope remaining work.

**[Adversarial] M6 — §3 traceability partial and misquotes the lab reference (§3)**
Row 2 claims "categorical cross-entropy"; lab text says "binary *or* categorical". Row 1 overstates the ImageNet mapping.

### Low (8)

**[Decision-readiness] Backend trade-off stated without what's given up (§2.3 FR-A2)**
Fix: One sentence — default `mobilenet` (zero-shot), `custom-cnn` needs user-labelled training folder.

**[Done-ness clarity] NFR-A3 "does no damage" is an adjective (§2.4)**
Fix: "re-run produces an identical tree; zero writes outside the output root."

**[Scope honesty] Out of Scope omits the classifier-quality boundary (§4)**
Fix: One line each: no labelled training dataset provided; no minimum accuracy target.

**[Downstream usability] ACs lack IDs though architecture cites them by ID (§2.5; system-architecture.md:80)**
Fix: Rename to `AC-A1..AC-A5`.

**[Adversarial] L1 — "Image file" is extension-only; adversarial cases live in architecture, not PRD ACs (§2.3 FR-A1 · §2.5 AC-4)**
Zero-byte images, unicode filenames, permission-denied moves appear only in architecture's QA table — DoD #4 unanchored in requirements.

**[Adversarial] L2 — AC-5's literal command doesn't run in this environment (§2.5 AC-5)**
Bare `pytest` not installed in the `py` env; grader following AC-5 verbatim gets command-not-found.
Fix: Specify `uv run --with pytest pytest -q`.

**[Adversarial] L3 — Filesystem edge cases unaddressed (§2.3 FR-A4, FR-A5)**
Cross-device move partial failure, NTFS 260-char paths, Windows reserved names, inbox symlinks — none acknowledged.

**[Adversarial] L4 — Folder-name deviation from lab prompt tracked outside the PRD (§1 · §4)**
Kickoff specified `meme_classifier/`; build uses `meme-classifier/`; conflict logged in bmad-plan §5, silent in the PRD.

## Mechanical notes

- **ID continuity:** FR-A1..A8, NFR-A1..A4 contiguous and unique; all §3 cross-refs resolve; only break: ACs unnumbered while arch cites "AC-4".
- **Glossary:** absent; "confidence threshold" undefined; input-folder wording drifts from arch.
- **Assumptions Index roundtrip:** N/A — no `[ASSUMPTION]` tags exist (absence is itself a Scope honesty finding).
- **UJ protagonist naming:** N/A — no UJs, appropriate for capability-spec shape.
- **Required sections:** Present: Overview, Problem, FRs, NFRs, Acceptance, Traceability, Out of Scope. Absent: Open Questions, Assumptions, Vision (acceptable at this stake level).
- **External refs verified:** `../spam-detector/docs/` and `../PROMPTS_LOG.md` resolve; header metadata complete.

## Reviewer files

- `review-rubric.md`
- `review-adversarial-general.md`
