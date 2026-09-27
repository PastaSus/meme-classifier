# Rubric Review — ARCHITECTURE-SPINE.md (meme-classifier, 2026-09-27)

**Reviewer:** rubric walker (good-spine checklist)
**Subject:** `_bmad-output/planning-artifacts/architecture/architecture-meme-classifier-2026-09-27/ARCHITECTURE-SPINE.md` (draft, 2026-09-27)
**Context read:** `docs/product-requirements.md` (Final v2.0), `docs/system-architecture.md` (Baseline v1.0), `docs/bmad-plan.md`, `reconcile-prd.md`, brownfield `main.py` / `cli.py` / `config.py` / `organizer.py` / `classifier.py`, `requirements.txt`, `.gitignore`, live environment (`uv --version`, `py -0`, `uv run python -V`, PyPI JSON for tensorflow/uv/numpy), `AGENTS.md`.

**Verdict: Needs revision — a strong, mostly enforceable spine (AD-1..AD-12 fix the structural divergence points and ratify the flat brownfield layout) undermined by three high findings: an undecided-then-contradicted recursion default, an environments dimension that is asserted rather than provisioned, and an AD-4 rule broad enough to forbid the tests the PRD requires.**

---

## Checklist assessment

| Checklist item | Result |
| --- | --- |
| Fixes the real divergence points for epics/stories, misses none | **Partial** — layout, config SSOT, ML seam, dependency direction, category authority, threshold routing, exit codes, report shape, training artifact flow are all fixed; recursion default, error-report taxonomy, and exit-code precedence are missed (F1, F4, F5). |
| Every AD's Rule enforceable and actually prevents its stated divergence | **Partial** — AD-1/2/3/5/6/9/10/11 enforceable and on-point; AD-4 overreaches (F3); AD-8 and AD-12 rules leave ordering/encoding underspecified so their stated divergences can still occur (F4, F5). |
| Nothing under Deferred could let two units diverge | **Mostly OK** — mapping content, hyperparameters, CI, packaging are single-owner or non-code; but the manifest/undo deferral cites a non-existent "PRD M4" and clashes with AD-12's "single source of run output" (F7). |
| Named tech verified-current | **Partial** — TensorFlow 2.21.0 confirmed latest on PyPI with a `cp313-win_amd64` wheel; uv 0.12.1 matches the installed binary (PyPI latest 0.12.19); Python "3.13 project-local via uv" is unprovisioned and unverified (F2). |
| Ratifies rather than contradicts the brownfield codebase | **Mostly OK** — AD-1/2/6 match `main.py`/`cli.py`/`config.py`/`organizer.py`/`classifier.py` exactly; recursion default (F1) and the empty-input early return (F4) contradict or silently override existing behavior. |
| Covers PRD FR-A1..A9 / NFR-A1..A5 | **Mostly OK** — all bound in frontmatter; NFR-A4 has no capability-map row (F8); recursion default inside FR-A1 undecided (F1). |
| Every dimension decided / deferred / open question | **Partial** — deployment & operations are consciously owned (Host row, Operational envelope, Demo ops, packaging/manifest deferrals), but the environment-provisioning half of *deployment & environments* is neither decided nor declared deferred (F2), and PRD OQ-2 is never carried (F11). |

---

## Findings

### F1 — HIGH — Recursion default is undecided and the spine ratifies two contradictory sources
**Cites:** Design Paradigm / Capability map row "FR-A1 scan / extensions / recursion"; AD-3.
PRD §2.1 and FR-A1 set *recursion off by default*, enabled by `-r` (`[ASSUMPTION: recursion defaults to off]`, PRD:40). Brownfield `cli.py:67-70` ships the inverse: recursion **on** by default with a `--no-recursive` flag, and `organizer.scan_images(recursive=True)` (`organizer.py:83`). The spine's capability map assigns FR-A1's recursion to `organizer.scan_images` under AD-3/AD-9 and never states the default, the flag name, or which source wins. This is a classic story-level split: a scan story and a CLI story will each implement a different flag contract, and neither can be called wrong from the spine. Fix: add an explicit rule (flag `-r/--recursive`, default off per PRD) and mark the brownfield `--no-recursive` inversion as a change, not a ratification.

### F2 — HIGH — "Deployment & environments" is asserted, not decided: Python 3.13 via uv does not exist in this repo
**Cites:** Stack table ("Python 3.13 (project-local via uv; system 3.14 untouched)"); Capability map "NFR-A5 environment … uv project config (build phase)"; Operational envelope.
Verified in-environment: there is **no `pyproject.toml`, `uv.lock`, or `.python-version`**; `uv run python -V` resolves to **3.12.13**, bare `py` is **3.14**, and `py -0` shows no 3.13 interpreter registered. PRD NFR-A5 and AGENTS.md disagree with each other (3.13 vs 3.14) and with both. So the Stack row states as fact a decision that exists nowhere in the repo, while the actual provisioning decision is buried in a capability-map cell ("build phase") and is absent from the **Deferred** list — an undeclared deferral. Two units (e.g. the test-config story and the TF-install story) can legitimately target 3.12, 3.13, or 3.14; TF 2.21 has no cp314 wheel, so the wrong choice fails at install time. Fix: decide `requires-python`/`.python-version` in the spine (or move it into Deferred explicitly) and restate the Stack row as target-vs-current.

### F3 — HIGH — AD-4's Rule forbids the tests the PRD and the baseline architecture require
**Cites:** AD-4 ("`organizer.py`, `cli.py`, `config.py`, and `tests/` stay stdlib-clean").
The stated divergence — TF imports leaking so QA dies on TF-less machines — is real, but the rule as written makes *all* of `tests/` TF-free. AC-A6 (fixture placement accuracy), AC-A11 (`--train` produces a loadable artifact) and `docs/system-architecture.md` §3 ("backends — mapping table coverage, threshold → `unsorted` … TF needed? **Yes**") require TF-dependent tests. As written, a reviewer enforcing AD-4 rejects the very tests the acceptance criteria demand, and a Dev story and a QA story will read the rule oppositely — a self-inflicted divergence. Fix: scope AD-4 to the organizer/CLI/scan test slice (NFR-A1, AC-A5) and name a separate TF-optional backend test slice.

### F4 — MEDIUM — AD-8 does not fully order exit-code precedence, and contradicts current empty-input behavior
**Cites:** AD-8; AD-12 ("printed after every run, including empty input").
Three unresolved orderings: (a) empty inbox + unavailable backend — `cli.run` returns `0` at `cli.py:108-110` *before* the backend load AD-8 mandates ("load once, before organizing"), so exit is 0 vs 2 depending on which sentence a story follows; (b) missing input dir + `--dry-run` is implied 1 but never stated relative to the dry-run 0 branch; (c) a batch-wide filesystem failure (unwritable output root) surfaces as per-file *reported skips* which AD-8 says "never change exit 0", while PRD FR-A8/AC-A8 says filesystem errors → 1. AD-8 also narrows PRD's "1 = runtime/filesystem error (e.g. missing input dir)" to only the missing-dir case. Fix: publish an explicit precedence order (parse → scan/dir → backend load → per-file) and state the batch-failure disposition.

### F5 — MEDIUM — AD-12's error taxonomy ("refused vs failed") has no structure, and AD-7's reason has no home
**Cites:** AD-12; AD-7; Consistency Conventions "Errors & logging".
AD-12 promises per-run "errors with reasons (refused vs failed distinguished)" but names no field, status enum, or counter — while brownfield `OrganizeReport` exposes only `moved/planned/skipped` plus a free-text `detail` (`organizer.py:46-70`, refusal at `:166-171` vs failure at `:191-202`). AD-7 separately requires that a corrupt image be *moved to `unsorted` with a logged reason* (AC-A4), which is neither a refusal nor a move failure — so its reason can plausibly land as an `error` record, a `moved` record with a note, or a `skipped` record, depending on which story gets there first. The stated divergence ("stories inventing divergent report shapes") is therefore not prevented. Fix: pin the record fields/status values and say explicitly where the predict-failure reason is counted.

### F6 — MEDIUM — Operational envelope silently relaxes PRD NFR-A3's "zero writes outside the output root"
**Cites:** Operational envelope ("Writes stay inside three roots: … `models/` … uv/Keras weight cache"); AD-11; Capability map NFR-A3 row.
PRD NFR-A3 (and AC-A10's test author) says *zero writes ever occur outside the output root*; AD-11 requires writing `models/custom-cnn.keras`, and the conventions row allows a first-run weight download into a cache outside the repo. The spine resolves this genuine PRD-internal conflict by fiat inside a descriptive paragraph — no AD binds it, no open question flags it. A QA story writing NFR-A3 literally will fail AC-style assertions the architecture has already licensed. Fix: promote the three-root write budget to an AD (or record it as an explicit PRD-conflict open question) so both the AD-11 story and the idempotency story test the same contract.

### F7 — MEDIUM — Deferred "Run manifest / undo (PRD M4)" cites a milestone that does not exist and collides with AD-12
**Cites:** Deferred bullet 3; AD-12.
`docs/product-requirements.md` (Final v2.0) contains no "M4" and no milestone section at all (grep: no hits). The deferral is therefore an orphan reference, and it is the only signal about who owns undo/manifest — while AD-12 declares `OrganizeReport` "the single source of run output". If a later story adds a manifest, it needs a rule for how it coexists with AD-12; "revisit if QA needs traceability" gives no anchor. Fix: re-cite to the correct PRD item (or drop the citation) and note the AD-12 interaction in the deferral.

### F8 — LOW — NFR-A4 has no Capability → Architecture Map row
**Cites:** Capability → Architecture Map (rows FR-A1..A9, AC-A6/7, NFR-A1/A2/A3/A5 only).
NFR-A4 (all config via CLI flags, incl. `--model-path`) is bound in frontmatter and by AD-3/AD-11, so it is not *unowned* — but the map the checklist uses for PRD coverage omits it, so a reader auditing NFR-A1..A5 row-by-row finds a hole. Add an NFR-A4 → `cli.build_parser` / AD-3 row.

### F9 — LOW — Stack currentness claims are inconsistent
**Cites:** Stack table.
TensorFlow's "2.21.0 verified latest stable on cp313, 2026-09-27" checks out (PyPI `tensorflow` latest = 2.21.0, `cp313-win_amd64` wheel present). But `uv 0.12.1` is the installed binary, not current (PyPI latest 0.12.19), and `numpy >=1.24` is a floor that resolves to 2.5.3 — a floor presented in a version table reads as a verified pin. Either label the column "floor (installed)" or pin exact versions for reproducible defense demos.

### F10 — LOW — Entry-layer contract wording does not match the code it ratifies
**Cites:** Design Paradigm table, row "Entry `main.py` — `SystemExit(main())` only".
`main.py:12` uses `sys.exit(main())`. Semantically equivalent, but a ratification table should quote the artifact it ratifies; a story "fixing" it to match the spine would be churn. Cosmetic.

### F11 — LOW — PRD OQ-2 is never carried into the spine
**Cites:** Deferred; AD-11.
PRD OQ-2 (live `--train` demo vs architecture-only) is the sibling of OQ-1, which the spine *does* carry (AD-12, fixture floors). OQ-2 decides whether AD-11 needs demo-grade ergonomics (timeouts, progress output, smoke-train on fixture) or only architectural conformance. The spine's only nod is the hyperparameters deferral. Add OQ-2 to Deferred/Open so the custom-cnn story knows which bar applies.

### F12 — LOW — Companion `reconcile-prd.md` is stale against the spine it reconciles
**Cites:** `reconcile-prd.md` Gaps 1–3 and Gap 5 (same folder as the spine).
Gaps 1 (train data contract), 2 (threshold validation) and 3 (fixture/accuracy) are all now addressed in the current spine (AD-11, AD-8's argparse clause, AD-12's `--fixture`), and Gap 5's wrong "AD-5 suffixing" citation has become "AD-3, conventions". Gap 4 (NFR-A3 vs AD-11) survives — see F6. Left as-is, a downstream reader treats resolved gaps as open work. Re-run or annotate the reconcile artifact.

### F13 — LOW — Exit code 2 is overloaded (usage error vs backend unavailable)
**Cites:** AD-8 final sentence.
The spine deliberately disclaims argparse's default exit 2 for usage errors ("FR-A8's code contract applies after a successful parse"), so this is a *decision*, not silence — but PRD FR-A8/AC-A8 define 2 solely as "backend unavailable", and a demo typo and a genuine backend failure now exit identically. Worth one line in the report contract (or a distinct usage-error behavior) so the defense Q&A answer is stable.

---

## What the spine gets right (for the record)

- **AD-1/AD-2/AD-6** exactly ratify the brownfield: flat root modules, no `src/`/`__init__.py`, `main → cli → {classifier, organizer} → config` with `organizer`/`classifier` meeting only in `cli` — verified against all five modules and `conftest.py`.
- **AD-3** is a genuine anti-drift rule with an enforceable surface (one `config.py`, flags only) and matches `config.py`'s actual contents (`CATEGORIES`, `IMAGE_EXTENSIONS`, `MODEL_BACKENDS`, `CONFIDENCE_THRESHOLD = 0.45`, `MAX_COLLISION_SUFFIX`).
- **AD-7/AD-8/AD-9/AD-10** close the exact divergences the PRD validation caught (corrupt-file disposition, exit-code drift, two category lists, threshold logic duplicated per backend), and AD-8's dry-run/backend-unavailable matrix matches FR-A6/AC-A9 verbatim.
- **AD-11** carries the full `--train` data contract (`<root>/<category>/*.jpg`, ~10/category, `models/custom-cnn.keras`), closing reconcile Gap 1.
- **Deployment & operations are not silent**: Host row ("no deploy target"), Operational envelope, Demo ops weight-cache pre-warm, and explicit deferrals for packaging/CI/manifest give the altitude's operational dimension real coverage — the exception is environment *provisioning* (F2).

## Recommended fix order

1. F1 (recursion default) and F2 (interpreter pin) — both block story authorship today.
2. F3 (AD-4 test scope) — otherwise QA/Dev read the spine as contradictory.
3. F4, F5, F6 (exit precedence, report taxonomy, write budget) — one AD edit each.
4. F7–F13 — cheap text corrections in the same pass; re-run `reconcile-prd.md` afterwards.
