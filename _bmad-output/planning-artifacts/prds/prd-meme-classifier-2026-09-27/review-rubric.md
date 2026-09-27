# PRD Quality Review — Product Requirements Document (PRD) — Meme & Reaction Image Organizer (Baseline v1.0)

## Overall verdict

**Adequate.** This is a tight, honest capability spec that fits its academic CLI brief: concrete FRs with named mechanisms (`shutil.move`, `os.makedirs`, exit codes), product-specific NFRs (stdlib-only organizer, path-traversal allow-list), a Non-Goals section that does real work, and a lab-reference traceability table built for the professor Q&A it names (§1: "defensible in a professor Q&A session"). What's at risk is the center of the product: FR-A2 claims to "classify meme templates / reaction styles" using an ImageNet classifier whose label space contains none of the five categories, and neither that mapping nor the FR-A3 confidence threshold value appears anywhere in the PRD — it was resolved silently in `system-architecture.md` §2.3 ("mapping table (e.g. `barbell → gym-memes`)", status "Dev Agent TODO") without any Open Question or assumption flagged here. Done-ness and scope honesty are the weak dimensions; shape fit and substance are the strengths.

## Decision-readiness — thin

FR-level choices are stated as decisions (selectable backend, `--dry-run`, collision suffixes, exit codes), so this is not a smooth-to-neutral PRD. But there is not a single Open Question, `[NOTE FOR PM]`, or `[ASSUMPTION]` in 77 lines, and the two decisions an engineer would push back on first are exactly the ones dodged: (a) how an ImageNet pre-trained model produces one of five meme categories, and (b) what the confidence threshold actually is. Both were answered downstream in the architecture doc rather than surfaced here, so a reviewer pushing back on FR-A2's feasibility finds no acknowledgement of the objection. The backend choice is presented as a menu ("**MobileNetV2** … or a **custom CNN**", §2.3 FR-A2) with no default named and no cost stated — the architecture doc picks `mobilenet` as default and notes the CNN "Needs training data? Yes — user labels a training set" (§2.3 table); the PRD gives neither.

### Findings
- **medium** — No open-items mechanism at real tensions (whole PRD; sharpest at §2.3 FR-A2/FR-A3) — Zero Open Questions, `[NOTE FOR PM]`, or `[ASSUMPTION]` callouts anywhere, while the ImageNet→category mapping and the threshold value sit undecided *in this document*. *Fix:* Add an Open Questions section with 2–3 entries (mapping rule, default threshold, default backend) plus a `[NOTE FOR PM]` on FR-A2 marking the mapping as delegated-but-uncertain.
- **low** — Backend trade-off stated without what's given up (§2.3 FR-A2) — "selectable backend" offers two options; the custom CNN's label-pipeline cost and the default selection are unstated. *Fix:* One sentence: default `mobilenet` (zero-shot, no training data), `custom-cnn` requires a user-labelled training folder.

## Substance over theater — strong

No personas, no vision boilerplate, no innovation/differentiation section — and for a single-operator academic CLI (shape fit, below) that absence is correct, not a gap. The content that is present is earned: NFRs are product-specific bounds, not "scalable/secure/reliable" copy — "must work **without TensorFlow installed** (pure stdlib)" (§2.4 NFR-A1), "Path-traversal-safe category names — only sanitized, allow-listed" (NFR-A2). The five categories in §2.2 are domain-specific ("Absurd, unhinged, cursed screenshots"), and §4's out-of-scope list names concrete technologies with a reason tied to the defense context ("will be discussed in defense, not built"). No furniture found; no findings.

## Strategic coherence — adequate

The thesis is inherited rather than argued — the lab reference mandates the shape, and the PRD is coherent around it: §2.1 problem ("Manual sorting is tedious") → FR-A1..A8 → §2.5 ACs → §3 traceability forms one arc, and MVP scope kind is unambiguous problem-solving. The weakness is metric choice: the acceptance criteria validate *file-handling* behavior (dry-run counts, allow-list, collisions, TF-absent pytest) but nothing validates the *classification* thesis — no measure of whether an image lands in the right category, and no counter-metric guarding the obvious escape hatch (dump everything into `unsorted` by lowering confidence and every AC still passes).

### Findings
- **medium** — Success criteria don't validate the classification thesis (§2.5 AC 1–5) — All five ACs verify plumbing (moves, collisions, skips, pytest); none verifies correct categorization, and no `unsorted`-rate counter-metric exists. *Fix:* Add one AC/SM on a small labelled sample (e.g. "≥7 of 10 known images land in their expected category") and a counter-metric bounding the `unsorted` share.

## Done-ness clarity — adequate

Six of eight FRs are engineer-testable as written: FR-A4/A5 name the mechanism and the exact collision form (`meme-1.jpg`), FR-A6/A7 have observable outputs, FR-A8 enumerates exit codes, FR-A1 lists the six extensions. §2.5 gives five concrete ACs — more than many PRDs of this size. But the rubric warns this is the dimension story creation leans on hardest, and it bends in three places: FR-A2's core transformation (image → one of five categories) has no defined mapping or accuracy condition; FR-A3's "confidence threshold" is used but never valued; and FR-A2/FR-A8 have no AC coverage at all.

### Findings
- **high** — FR-A2's central operation is undefined in the PRD (§1 "classifies meme templates / reaction styles"; §2.3 FR-A2) — "MobileNetV2 (pretrained on ImageNet)" cannot emit `gym-memes`/`cat-memes`/etc. without a label→category mapping, and none is specified here; the custom CNN is specified only as layer *names* ("Conv2D → MaxPooling2D → Flatten → Dense, categorical cross-entropy") with no input size, units, or training-data source. The mapping appears only downstream (`system-architecture.md` §2.3, "Dev Agent TODO"). An engineer cannot state "done" for the product's primary FR from this document. *Fix:* Specify the mapping rule (ImageNet class → category, default `unsorted` on unmatched/low-confidence) and one testable condition per backend, or explicitly delegate with a `[NOTE FOR PM]`.
- **medium** — "Confidence threshold" has no value and no AC exercises it (§2.3 FR-A3; §2.5) — "anything below the confidence threshold goes to `unsorted`" leaves the default and range unstated; no AC covers the below-threshold path. *Fix:* State the default (config constant, flag-overridable per NFR-A4) and add an AC: "an image scoring below threshold lands in `unsorted` with reason logged."
- **medium** — AC coverage gaps for FR-A2 and FR-A8 (§2.5 vs §2.3) — Nothing accepts "both backends selectable and produce category + confidence" or "exit codes 0/1/2 behave as specified"; architecture §2.3 already relies on exit code 2 ("Missing TensorFlow … → exit code 2 (FR-A8)"). *Fix:* Add ACs: `--backend` switch accepted and honored; missing TF → exit 2.
- **low** — NFR-A3 "does no damage" is an adjective (§2.4) — Unbounded; "damage" is undefined. *Fix:* Bound it: "re-run produces an identical tree; zero writes outside the output root."

## Scope honesty — thin

§4 is the strongest scope work in the PRD — an explicit Out of Scope list where it does real work, distinguishing lab-reference knowledge from build scope ("YOLOv8, webcam, Haar cascades … discussed in defense, not built"), corroborated by §3's traceability row. But the rubric's other honesty instruments are entirely absent: no `[ASSUMPTION]` tags, no `[NOTE FOR PM]`, no Open Questions, no Assumptions Index. Several material inferences are left for the reader to make silently — the default output location and recursive flag default (FR-A1 "optionally recursive"), where custom-CNN training labels come from, and whether text/OCR reading of memes is in scope at all (the §2.2 categories describe visual style, but memes are text-heavy and the question is never posed). For a low-stakes case study some of this is forgivable; total absence of a mechanism is not, because the unresolved items were in fact resolved elsewhere.

### Findings
- **medium** — Omissions are inferred, not flagged (whole PRD; §2.3–§2.4) — No `[ASSUMPTION]`/Open Questions/Assumptions Index while reader must infer threshold default, output-dir default, recursion default, training-data source, and OCR stance. *Fix:* Add an Assumptions Index with 3–4 inline `[ASSUMPTION: …]` tags and an Open Questions section (overlaps the decision-readiness fix — one section serves both).
- **low** — Out of Scope omits the classifier-quality boundary (§4) — Lists webcam/YOLO/mobile/web UI but not "no labelled training dataset provided; no minimum accuracy target" — both silently assumed. *Fix:* One line each in §4.

## Downstream usability — adequate

This PRD is chain-top (feeds `system-architecture.md` and `bmad-plan.md`, both of which cite "FR IDs throughout"), so traceability matters more than for a standalone doc, and it mostly delivers: FR-A1..A8 and NFR-A1..A4 are contiguous and unique; every ID in §3's traceability table resolves (FR-A2, FR-A4, and "Out of scope §4" all exist); each section reads standalone without "see above"; sibling cross-refs (`system-architecture.md`, `../../spam-detector/docs/`, root `PROMPTS_LOG.md` → INIT-001) all resolve on disk. What's missing is a glossary, and with it the definition of "confidence threshold" that FR-A3 depends on — an extractor pulling FR-A3 alone gets an undefined parameter. No UJs, correctly (see shape fit).

### Findings
- **medium** — No glossary; key domain nouns under-defined and drifting (§2.3 FR-A3; §2.1 vs data layout) — "confidence threshold" is used but never defined; PRD says "user-specified input folder" (§2.1) while the architecture fixes `data/inbox/` and `data/organized/` (§2.1 module map). *Fix:* Add a 5-term glossary (category, backend, confidence threshold, inbox/input folder, organizer) and align §2.1 wording with the arch paths.
- **low** — ACs lack IDs though the architecture cites them by ID (§2.5; `system-architecture.md:80` "(AC-4)") — PRD numbers them 1–5 with no prefix, so the cross-doc reference only resolves by position. *Fix:* Rename to `AC-A1..AC-A5`.

## Shape fit — strong

The shape matches the product: a single-operator, academic, CLI capability spec with professor-defense traceability needs — problem, categories, FRs, NFRs, ACs, lab traceability, explicit out-of-scope — and that is precisely the shape it takes. UJs with named protagonists and personas would be overhead here, and their absence is deliberate calibration rather than under-formalization; the §3 traceability table is justified by the named Q&A defense rather than by template momentum. Brownfield concerns don't apply (greenfield repo), and the PRD correctly distinguishes build scope from lab "reference knowledge." No findings.

## Mechanical notes

- **ID continuity:** FR-A1..A8 and NFR-A1..A4 contiguous, unique, no duplicates or gaps. All cross-refs in §3 resolve (`FR-A2`, `FR-A4`, "Out of scope §4"). Only break: ACs unnumbered as IDs while `system-architecture.md:80` cites "AC-4" (see Downstream usability, low).
- **Glossary:** None present; drift between PRD's "input folder" (§2.1) and arch's `inbox/`; "confidence threshold" undefined (see Downstream usability, medium).
- **Assumptions Index roundtrip:** N/A — no inline `[ASSUMPTION]` tags exist to index (this absence is itself a Scope honesty finding).
- **UJ protagonist naming:** N/A — no UJs, appropriate for capability-spec shape.
- **Required sections:** Present for this product type/stakes: Overview, Problem, FRs, NFRs, Acceptance, Traceability, Out of Scope. Absent: Open Questions, Assumptions, Vision/thesis statement (acceptable at this stake level; Overview substitutes).
- **External refs verified:** `../spam-detector/docs/` and `../PROMPTS_LOG.md` both resolve from repo root; header metadata (Status, Date, source-of-truth pointer) complete.
