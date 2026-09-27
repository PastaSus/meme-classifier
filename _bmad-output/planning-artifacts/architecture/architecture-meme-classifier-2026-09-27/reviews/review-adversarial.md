# Adversarial Review — Architecture Spine (feature altitude)

**Lens:** adversarial (spine attack: compliant story-pairs that still build incompatibly)
**Target:** `_bmad-output/planning-artifacts/architecture/architecture-meme-classifier-2026-09-27/ARCHITECTURE-SPINE.md` (draft, 2026-09-27)
**Context read:** `docs/product-requirements.md` (Final v2.0), `docs/system-architecture.md` (Baseline v1.0), `reconcile-prd.md`, code sweep (`main.py`, `cli.py`, `organizer.py`, `classifier.py`, `config.py`, `conftest.py`, `tests/test_organizer.py`)
**Date:** 2026-09-27

## Verdict

The spine's ADs are individually reasonable but none is airtight at the seams: 20 story-pair conflicts survive a literal reading of every rule (3 critical, 9 high, 6 medium, 2 low), because ownership of shared entities (`ClassificationResult`, `OrganizeReport` reasons, threshold plumbing, model-path constant), write-scope, and exit-code timing are each left to two ADs that disagree or to no AD at all.

## Story key (the units one level down)

| ID | Story | Core scope |
| --- | --- | --- |
| S1 | mobilenet backend | FR-A2 MobileNetV2 load/predict, label→category mapping (Deferred owner), AD-4/AD-10 |
| S2 | dry-run / report | FR-A6, FR-A7, `--fixture`, refused-vs-failed, AD-8, AD-12 |
| S3 | custom-cnn train | FR-A9, `--train`, `--model-path`, AD-11 |
| S4 | exit-code acceptance | FR-A8, AC-A4, AC-A8/AC-A9 test story |
| S5 | fixture / AC-A6 | `tests/fixtures/labeled/`, accuracy floor test |
| S6 | organizer idempotency | NFR-A3, AC-A10, collision/scan-exclude story |

## Does each AD's Rule truly prevent its stated divergence?

| AD | Stated prevention | Verdict | Why |
| --- | --- | --- | --- |
| AD-1 | hyphenated modules / convention drift | **Partial** | Governs *names*, never roots or owners of created folders (`models/`, `tests/fixtures/`); the three-root envelope is prose (L2). |
| AD-2 | package/`src/` restructurings | **Fails as a preventer** | Permits unbounded new flat root modules while AD-6's graph has five nodes — no slot for a shared types module (H7). |
| AD-3 | duplicated constants drifting apart | **Partial** | The tunable list is a closed enumeration (categories, extensions, threshold, backends, default paths); mapping table, fixture root, weights fall outside it (M4), and it collides head-on with AD-11 (H8). |
| AD-4 | TF leaking into organizer/tests | **Partial** | Achieves the import firewall, but pins `get_classifier(name)` / `load`/`predict` without owning the threshold hand-off (C2), bans Pillow from fixture tooling (M5), and never names the `ClassificationResult` owner (H7). |
| AD-5 | destroyed audit trail | **Partial** | Protects content; path `../PROMPTS_LOG.md` is CWD-unanchored (L1). |
| AD-6 | import cycles | **Partial** | Prevents cycles among five named modules; says nothing about a sixth shared module two stories may each create (H7). |
| AD-7 | three-way corrupt-file divergence | **Fails in part** | Moves the *decision* to `cli.run` but parks the *reason* in the log — colliding with AD-12's single-source report (C1); `unsorted` vs AD-9's reject still yields two dispositions for an invalid category (H6). |
| AD-8 | exit-code drift; env-dependent dry-run | **Partial** | Codes are crisp, but weight-fetch timing (H3), the general dry-run no-write property (H2), `--train` interaction (C3, M2), path-flag validation and argparse's exit `2` (H9) are all unowned. |
| AD-9 | two category lists diverging | **Fails its stated goal** | The Rule makes the organizer *reject* the divergent label (skip, exit 0) instead of preventing divergence; outcome contradicts AD-10/FR-A2 `unsorted` (H6). |
| AD-10 | threshold logic re-implemented per backend | **Fails** | The rule text already contradicts the swept code (`cli.py:134-136` routes in `cli`); it provides no seam for the `--threshold` flag through AD-4's factory (C2). |
| AD-11 | hard-coded model paths; incompatible training inputs | **Partial** | Path flow is clear; "Nothing else references a model path" contradicts AD-3/conventions (H8); no ordering, dry-run, or exit-code interaction (C3, M2). |
| AD-12 | divergent report shapes / fixture plumbing / exit logic | **Partial** | Shape is clear, but "printed after every run" is unimplementable on the exit-1/exit-2 paths where no report exists (H1); "cli only renders" blocks cli-side fixture reading (M1); refused-vs-failed collides with the `skipped` aggregate (H5). |

## Findings

Severity tags: `critical` > `high` > `medium` > `low`. Every finding names its story-pair.

---

### C1 — `critical` — pair: S1 mobilenet × S2 dry-run/report — predict-failure reason lives in the log, not the report

- **location:** AD-7 (spine:81) vs AD-12 (spine:111); `OrganizeJob` at `organizer.py:26-32`
- **trigger_condition:** S1 obeys AD-7 to the letter — a corrupt/unreadable file is converted in `cli.run` to `OrganizeJob(category="unsorted", confidence=0.0)` with the reason passed to `logger.warning` (`cli.py:129-132`), and `OrganizeJob` has no reason field to carry it further. S2 obeys AD-12 to the letter — it builds "errors with reasons" from `MoveRecord.detail`/`STATUS_SKIPPED`, which only organizer-stage failures ever populate.
- **guard_snippet:** Tighten AD-7: "the predict-failure reason is attached to the job (new `OrganizeJob.reason: str` field) and surfaces in `OrganizeReport.errors`; logging is optional, never the sole carrier." Assign the field's owner (organizer defines, cli fills).
- **potential_consequence:** AC-A4's "reason recorded" fails silently; the report shows corrupt files as `moved` successes under `unsorted` with an empty errors section, while AD-12 claims the report is the single source of run output.

### C2 — `critical` — pair: S1 mobilenet × S2 dry-run/report — no compliant path exists to hand `--threshold` to the classifier

- **location:** AD-3 (spine:48), AD-4 (spine:54), AD-10 (spine:99), AD-8 (spine:87); current routing at `cli.py:134-136`
- **trigger_condition:** AD-10 requires routing "decided once, inside the classifier layer"; AD-4 pins `get_classifier(name)` and the `load`/`predict` ABC; AD-3 makes the CLI flag "the only override surface"; AD-8 puts validation at parse time. S1 can satisfy all four only by inventing an optional kwarg on the factory or ABC (e.g. `get_classifier(name, threshold=…)`) — one of at least three literal readings (ctor attribute, `predict(path, threshold=…)` parameter, cli-side check preserved per AD-10's organizer-scoped final clause). S2, editing the same loop for backend-down job synthesis, preserves the seeded cli-side check.
- **guard_snippet:** New AD or tightened AD-10 + AD-4: "`BaseClassifier.__init__(…, threshold: float)` (or a single `predict` parameter — pick one) is the sole threshold hand-off; `cli.run` passes `args.threshold` and must not re-route; `get_classifier(name, threshold)` keeps its one-arg call valid."
- **potential_consequence:** Two compliant stories fork the ABC seam incompatibly; worst case the flag becomes dead (config-only threshold, violating AD-3's override promise) or routing runs twice with divergent test expectations.

### C3 — `critical` — pair: S3 custom-cnn train × S2 dry-run/report — `--train` writes files while dry-run promises zero writes; train exit codes unowned

- **location:** AD-11 (spine:105), AD-8 (spine:87), operational envelope (spine:160), NFR-A3 capability row (spine:177)
- **trigger_condition:** S3 obeys AD-11 literally — `--train` writes the artifact to `--model-path` (`models/custom-cnn.keras`) unconditionally. No AD states "dry-run performs zero writes" (AD-8's dry-run clause covers only the unavailable-backend case), so S2's no-write guarantee rests on FR-A6 alone, and the spine still carries the unresolved NFR-A3-vs-AD-11 contradiction flagged in `reconcile-prd.md` Gap 4. Neither AD defines an exit code for train failures, a train run with a missing inbox, or `--dry-run --train` precedence.
- **guard_snippet:** Tighten AD-11: "`--train` writes the artifact only when `--dry-run` is absent; under `--dry-run` training is skipped with a warning. Train failure exit codes map to FR-A8 (bad root → 1, model/TF failure → 2); `--train` runs before scan and does not require an inbox." Reconcile NFR-A3 with an explicit `models/` exception.
- **potential_consequence:** A demo or AC-A10 idempotency check run with both flags mutates the repo during a "no writes" run; QA can never say which exit code a training error produces.

### H1 — `high` — pair: S2 dry-run/report × S1 mobilenet — report demanded on exit paths where no `OrganizeReport` exists

- **location:** AD-12 (spine:111) vs AD-8 (spine:87); early returns at `cli.py:108-110` and `cli.py:115-123`
- **trigger_condition:** AD-12 says the report is "printed after every run, including empty input" and `cli` "only renders it"; AD-8 requires backend load *before* organizing, so on exit `2` `organize()` never runs and no report object exists; the same holds on the missing-dir exit `1` (scan raises first). S2 must therefore either construct a report in `cli` (breaking "cli only renders") or render nothing (breaking "every run"); S1 is free to `return 2` immediately, as the seeded code does.
- **guard_snippet:** Tighten AD-12: "`cli.run` always renders a report before returning — it calls `organizer.empty_report()` (organizer-owned factory) on the empty-input, exit-1, and exit-2 paths; cli never instantiates `OrganizeReport` directly." Or scope AD-12: "every run that reaches the organize step."
- **potential_consequence:** FR-A7/AC-A1-style assertions fail on exactly the flagship demo paths (TF missing, empty inbox); two stories ship contradictory render points.

### H2 — `high` — pair: S2 dry-run/report × S6 organizer idempotency — "dry-run writes nothing" is in no AD

- **location:** AD-8 (spine:87), AD-12 (spine:107-111), conventions row (spine:119); `organizer.py:185`, `tests/test_organizer.py:96-107`
- **trigger_condition:** S6 wants to pre-create allow-listed category folders (AC-A2) or pre-resolve output-root state for idempotency — an AD-compliant move, since no rule forbids mkdir during planning. S2 relies on FR-A6's zero-write promise (`assert not out.exists()`), which no AD encodes. Both stories pass every AD literally and still break each other's acceptance criteria.
- **guard_snippet:** Tighten AD-8: "Under `--dry-run`, `cli.run` and `organizer.organize` perform zero filesystem mutations — no `mkdir`, no `makedirs`, no cache-priming; planned destinations are computed against a virtual tree."
- **potential_consequence:** AC-A1 ("folder is untouched") fails depending on which story lands first; dry-run stops being a safe demo mode.

### H3 — `high` — pair: S1 mobilenet × S4 exit-code acceptance — weight-fetch timing decides exit `2` vs exit `0`

- **location:** AD-8 (spine:87), AD-7 (spine:81), demo-ops row (spine:122)
- **trigger_condition:** AD-8 binds "backend load happens once in `cli.run`, before organizing" but never binds *when weights are fetched*. S1 may fetch ImageNet weights inside `load()` (offline failure → exit `2`, compliant) or defer the download to first `predict()` (each file fails → AD-7 converts to `unsorted`, exit `0`, also compliant). S4's AC-A8/AC-A9 tests assume one of the two.
- **guard_snippet:** Tighten AD-8: "Backend availability — including weight/model fetch — is resolved entirely inside `load()`; no network or model I/O may occur in `predict()`; any `load()` failure follows the exit-2 / dry-run-0 matrix."
- **potential_consequence:** The demo-ops offline risk (first run downloads ~14 MB) becomes run-shape-dependent: the same offline machine exits `2` or silently files everything to `unsorted` with exit `0`, defeating AD-8's stated prevention of environment-dependent dry-run/exit drift.

### H4 — `high` — pair: S2 dry-run/report × S1 mobilenet — two owners for the backend-down fallback disposition

- **location:** AD-8 (spine:87), AD-10 (spine:99), AD-4 (spine:54)
- **trigger_condition:** AD-8 has `cli.run` synthesize "all files planned to `unsorted`" when the backend is unavailable in dry-run — a category decision made outside the classifier layer. AD-10 says routing is decided once in the classifier layer. S1 may comply more fully by registering a `null`/fallback backend in `config.MODEL_BACKENDS` (AD-4's factory validates against that tuple; AD-3 keeps names in config — both letter-compliant), while S2 complies by synthesizing jobs in `cli`. Each story implements the same path with a different owner; the config route also adds a third entry to `--backend` choices (`cli.py:50`), changing the PRD FR-A2 surface.
- **guard_snippet:** Tighten AD-8 (or AD-10): "The backend-down fallback is implemented only in `cli.run` as job synthesis; no fallback backend is registered in `config.MODEL_BACKENDS` and `--backend` choices stay exactly `config.MODEL_BACKENDS` minus any fallback."
- **potential_consequence:** Two implementations of one behavior, a widened CLI surface, and double-counted `unsorted` jobs if both land.

### H5 — `high` — pair: S2 dry-run/report × S4 exit-code acceptance — refused-vs-failed split collides with the `skipped` aggregate and per-category counts

- **location:** AD-12 (spine:111), AD-8 (spine:87), conventions row (spine:119); `organizer.py:64-70` (`counts_by_category` skips only `STATUS_SKIPPED`), `tests/test_organizer.py:120-141`
- **trigger_condition:** AD-12 demands refused vs failed be distinguished — S2 introduces a second status (e.g. `STATUS_REFUSED`). `counts_by_category()` then counts refused records as category placements unless also updated; existing tests pin `report.skipped == 1` for *both* a rejected category and a failed move. AD-8 only guarantees exit `0` for "reported skips", so if refused is no longer a skip its exit-code treatment is undefined. S4's AC-A4/AC-A8 assertions depend on which reading wins.
- **guard_snippet:** Tighten AD-12: "`OrganizeReport` exposes `refused` and `failed` counters; both remain excluded from `counts_by_category()`; AD-8's exit-0 guarantee covers refused, failed, and skipped alike (rename the clause to 'any reported non-move')."
- **potential_consequence:** Per-category counts silently include not-moved files, breaking AC-A6/AC-A7 arithmetic, or refused files lose their exit-0 guarantee.

### H6 — `high` — pair: S1 mobilenet (mapping) × S6 organizer allow-list — invalid category is *rejected* (skip, exit 0), not routed to `unsorted`

- **location:** AD-9 (spine:93) vs AD-10 (spine:99); `organizer.py:164-171`, FR-A2/§2.2 (`docs/product-requirements.md:50,56`)
- **trigger_condition:** AD-9's Rule makes the organizer "reject everything else" — `sanitize_category` raises, the record becomes `STATUS_SKIPPED`, the file stays in the inbox, exit stays `0` (AD-8). AD-10/FR-A2 say anything unmapped or invalid routes to `unsorted`. S1 owns the mapping (Deferred, spine:182); a typo there, or any later edit to `config.CATEGORIES`, makes S1's outputs "valid to the classifier, rejected by the organizer". Both stories obey their ADs; the disposition for the same defect differs by story.
- **guard_snippet:** Tighten AD-9: "Classifier-layer output is normalized once in `classifier` (member check against `config.CATEGORIES`); any non-member becomes `category='unsorted'` with the raw label recorded as the reason *before* it reaches `organizer`. `organizer.sanitize_category` remains a pure path-traversal guard for defensive re-validation only and must not be the primary disposition path."
- **potential_consequence:** AD-9's stated prevention ("a mapping emitting a label the organizer rejects") is not prevented — files silently stop being organized, exit `0`, report shows them as errors/skips while the accuracy story reports a different failure mode.

### H7 — `high` — pair: S1 mobilenet × S3 custom-cnn train — `ClassificationResult` shape and module are unowned; AD-6's graph has no shared-types slot

- **location:** AD-2 (spine:42), AD-6 (spine:66), AD-10 (spine:99); `classifier.py:26-34`
- **trigger_condition:** No AD names the owner, fields, or home of `ClassificationResult`. S1 wants `mapped: bool` / `top5` / a relocated dataclass in a new flat root module (`results.py` — permitted by AD-2's "modules live flat at repo root"). S3 wants `class_index` / `logits` metadata for the CNN path. AD-6's Rule enumerates edges among exactly five modules; a sixth module is neither placed by the diagram nor forbidden by the letter, so each story may create its own.
- **guard_snippet:** New AD or tightened AD-6: "`ClassificationResult` and `OrganizeJob` are defined in `classifier.py` / `organizer.py` respectively and are never relocated or duplicated; new shared types go into `config.py` or are not shared (no new root module may be imported by more than one of `{cli, classifier, organizer}`)." Field additions require both stories to extend the same class, not fork it.
- **potential_consequence:** Two dataclasses with the same name at the seam, or a `cli` import that breaks when one story's module is renamed; review cannot tell which shape is authoritative.

### H8 — `high` — pair: S3 custom-cnn train × flag/config story — model-path constant has two mutually exclusive legal homes

- **location:** AD-11 (spine:105) vs AD-3 (spine:48) + conventions rows (spine:120)
- **trigger_condition:** AD-11 says "Nothing else references a model path." AD-3 + the conventions row ("every flag maps to a `config.py` name", "default paths … defined once in `config.py`") require the `--model-path` default to live in `config.py`. S3, obeying AD-11's letter, defines `DEFAULT_MODEL_PATH` beside the backend in `classifier.py`; the flag/config story, obeying AD-3's letter, defines it in `config.py`. Both cite the spine; the two constants can drift.
- **guard_snippet:** Rewrite AD-11: "`config.DEFAULT_MODEL_PATH` is the only literal model path; `classifier` receives it as a constructor argument and never names `models/…` itself; no module other than `config` contains the string `custom-cnn.keras`."
- **potential_consequence:** `--model-path` default and the trainer's write target diverge; the tool trains one file and loads another, which is AD-11's stated prevention exactly.

### H9 — `high` — pair: S2 dry-run/report (`--fixture`) × S3 custom-cnn train (`--model-path`) — path-flag validation collides with FR-A8's exit codes

- **location:** AD-8 (spine:87), AD-12 (spine:111); `cli.py:47-60` (`type=` only, no validation)
- **trigger_condition:** AD-8 routes flag validation to argparse ("usage errors exit per argparse default" — argparse exits `2`), while FR-A8/AC-A8 reserve `2` for backend-unavailable and `1` for filesystem errors. A nonexistent `--fixture` root or `--model-path` directory is a filesystem error: S2 validating it with an argparse `type=` callable exits `2`; S3 validating it in `run()` (catching `OSError` → `1`, as `cli.py:154-159` already does) exits `1`. Both cite AD-8; AD-8's split never classifies path-existence checks, and its blessing of argparse's default already overloads code `2`.
- **guard_snippet:** Tighten AD-8: "argparse owns *value-shape* validation only (`--threshold` in (0,1], choices); *path existence* is validated in `cli.run` before side effects and maps to FR-A8 (`1`); argparse's default exit `2` is disambiguated in AC-A8 as 'usage error', distinct from 'backend unavailable', or argparse errors are re-mapped to `2` with an explicit usage banner."
- **potential_consequence:** AC-A8 becomes unfalsifiable — a test asserting exit `2` passes for the wrong reason; the same bad path yields different codes depending on which story added the flag.

### M1 — `medium` — pair: S2 dry-run/report × S5 fixture/AC-A6 — fixture reading locus and the deferred accuracy floors

- **location:** AD-12 (spine:111), Deferred (spine:182), paradigm table "Owns" (spine:26); seed `tests/fixtures/labeled/` (spine:154)
- **trigger_condition:** AD-12 puts placement accuracy inside `OrganizeReport` while "`cli` only renders it" — so reading the fixture tree must land in `organizer.py` (not in the paradigm's "Owns" list) or violate render-only. Meanwhile AC-A6's ≥6/10 floor and AC-A7's ≤80% `unsorted` live in open OQ-1 (Deferred), so S5 must invent numbers S2's calibration later changes.
- **guard_snippet:** Tighten AD-12: "`organizer.read_fixture_labels(root) -> dict[Path, str]` (stdlib) supplies expected labels; accuracy is computed inside `organize()` when `fixture_root` is passed; `cli` only passes the root through. Move the floors from OQ-1 into a named config constant (`ACCURACY_FLOOR`) so tests read AD-3's single source."
- **potential_consequence:** Fixture logic splits across two modules; the accuracy test and the report disagree on the floor, and AD-3 ("every flag maps to a config name") has no constant to map `--fixture` to.

### M2 — `medium` — pair: S3 custom-cnn train × S2 dry-run/report — position of `--train` inside `run()` unowned

- **location:** AD-8 (spine:87), AD-11 (spine:105), AD-12 (spine:111)
- **trigger_condition:** AD-8 fixes only "load before organizing". S3 may run training before the scan (train-only invocation works with no/missing inbox — then AD-8's missing-dir → `1` never fires) or after the scan (train-only runs still require an inbox). AD-12's "report after every run" may or may not include train runs; AD-11 is silent on both.
- **guard_snippet:** Tighten AD-8/AD-11: "Order in `run()`: parse → train (if `--train`, returns before scan; missing *input dir* still exits `1` only when no `--train`) → scan → load backend → organize → render report. A train-only run renders a report with zero records."
- **potential_consequence:** `--train` and missing-input-dir exit codes depend on story order; the report appears or not depending on which story owns the early return.

### M3 — `medium` — pair: PRD-literal flag story × code-literal flag story — no AD binds the CLI surface to the PRD

- **location:** AD-3 (spine:48), AD-8 (spine:87), conventions (spine:120); `cli.py:41-70` vs `docs/product-requirements.md:39-40`
- **trigger_condition:** PRD §2.1 specifies `-o/--output` and recursion **off** by default with `-r` to enable; the code ships `--output-dir` and `--no-recursive` (recursion on by default). No AD names flags, spellings, or defaults, so a story transcribing the PRD literally and a story preserving the code both obey every AD while defining mutually exclusive argparse arguments — and the recursion default flips silently.
- **guard_snippet:** New AD or AD-3 extension: "The argparse surface (flag names, aliases, defaults, recursion default) is fixed by `docs/product-requirements.md` §2.1; existing code differences are reconciled in a dedicated story before feature work; every flag has exactly one `config.py` default."
- **potential_consequence:** Two stories produce conflicting parser definitions; graders following the PRD get different behavior than the README/demo path.

### M4 — `medium` — pair: S1 mobilenet (mapping) × flag/config story — label→category mapping placement unowned

- **location:** AD-3 (spine:48), Deferred (spine:182); current home `classifier.py:55-73`
- **trigger_condition:** Deferred assigns the mapping to S1 as a "build-time artifact" but never says *where*. AD-3's closed tunable list omits it; AD-4 keeps classifier-owned data inside `classifier.py`; AD-1 permits `data/label-map.json` (kebab folder ✓). S1 may ship any of the three; a config-hardening story reading AD-3 broadly moves it to `config.py`. Both compliant → two sources of label→category truth.
- **guard_snippet:** Tighten AD-3 (add mapping to the enumeration) or Deferred: "The label→category mapping is a single `config.CATEGORIES`-keyed structure in `config.py`; `classifier` reads it, never re-declares it; no on-disk mapping file exists."
- **potential_consequence:** Mapping edits land in two places; AD-9's member check passes while one copy routes a label to a renamed category — the divergence AD-3/AD-9 were written to prevent.

### M5 — `medium` — pair: S5 fixture tooling × S1 mobilenet — AD-4's Pillow ban has no fixture-tooling exemption

- **location:** AD-4 (spine:54)
- **trigger_condition:** AD-4: "Only `classifier.py` may import TensorFlow/NumPy/Pillow." Validating that fixture images actually decode (S5) needs Pillow. Every compliant reading forces S5 to either skip validation, live inside `classifier.py` (wrong owner), or violate AD-4 — while S1 legitimately holds the only Pillow import. Conversely a root-level `make_fixtures.py` obeys AD-1/AD-2 but not AD-4.
- **guard_snippet:** Tighten AD-4: "`Pillow` may be imported in `classifier.py` and in a root-level `tools_*.py` / `tests/` fixture helper; `TensorFlow`/`NumPy` remain confined to `classifier.py`; `organizer.py`, `cli.py`, `config.py` stay fully stdlib (NFR-A1)."
- **potential_consequence:** Fixture generation is unbuildable under a literal reading, or an agent "fixes" it by pulling Pillow into `organizer.py`, weakening the QA firewall the AD exists to protect.

### M6 — `medium` — pair: S3 binary-cross-entropy variant × S2 report — binary output has no top-1-of-mapped-label confidence

- **location:** AD-10 (spine:99); `docs/product-requirements.md:57` (binary *or* categorical, verbatim)
- **trigger_condition:** AD-10 defines confidence as "top-1 probability of a mapped label" and routes by `score < threshold`. A lab-compliant binary (single sigmoid) custom CNN has no per-category top-1: S3 may return 0/1 confidences and a positive/negative pseudo-label, while S2's report/accuracy math assumes five-way softmax probabilities. Each obeys its own ADs; the confidence scale and threshold behavior are incompatible.
- **guard_snippet:** Tighten AD-10: "Backends must expose a five-element distribution over `config.CATEGORIES` (softmax or normalized); a binary artifact must be rejected at `load()` with an availability error (exit `2`), or `ClassificationResult` gains an explicit `scale` field the report renders."
- **potential_consequence:** Threshold, accuracy, and the ≤80% `unsorted` metric become meaningless for one backend; the same run reports different confidence semantics per story.

### L1 — `low` — pair: S1 mobilenet × any second AI-assisted story — prompt-log path is CWD-relative and PRD calls it "root"

- **location:** AD-5 (spine:60); `docs/product-requirements.md:5`; actual file `../PROMPTS_LOG.md` (workspace root, outside the repo)
- **trigger_condition:** AD-5's `../PROMPTS_LOG.md` resolves against the process CWD; the PRD says "root `PROMPTS_LOG.md`". Two stories launched from different working directories append to different files while each believes it complied.
- **guard_snippet:** Tighten AD-5: "Append to the absolute path `<workspace-root>/PROMPTS_LOG.md` (repo parent); resolve once at session start; never create a second log inside the repo."
- **potential_consequence:** The audit trail splits across two files; a grader reading only one sees gaps in an append-only record that cannot be repaired without violating AD-5.

### L2 — `low` — pair: S3 custom-cnn train × S5 fixture — AD-1 governs folder *names*, not folder *roots*

- **location:** AD-1 (spine:36), operational envelope (spine:160)
- **trigger_condition:** AD-1 binds "all file/folder creation" but rules only on case. S3 creates `models/`, S5 creates `tests/fixtures/labeled/`, S6 touches `data/organized/` — the three-root write envelope lives in prose (envelope paragraph), not in any Rule, so a story can add a fourth write root while obeying AD-1 to the letter.
- **guard_snippet:** Tighten AD-1 (or promote the envelope): "All writes are confined to `--output` tree, `models/`, and the uv/Keras cache; any new on-disk folder must be named in an AD before a story creates it."
- **potential_consequence:** Write scope drifts story by story — the exact class of problem NFR-A3 and AD-11 are already fighting about (see C3).

## Recommended new or tightened ADs (derived from the findings)

1. **AD-13 — Run lifecycle & report reachability:** ordering of `train → scan → load → organize → render`, report rendering on every exit path via an organizer-owned empty-report factory, weight fetch confined to `load()` (C3, H1, H3, M2).
2. **AD-14 — Write-scope & dry-run atomicity:** zero mutations under `--dry-run` across all stories; explicit `models/` carve-out resolving NFR-A3 vs AD-11 (C3, H2, L2).
3. **AD-15 — Shared-contract ownership:** single owner and single home for `ClassificationResult`, `OrganizeJob` (+`reason`), `OrganizeReport` counters (refused/failed/skipped), and the label→category mapping; no new root module imported by two layers (C1, H5, H7, M4).
4. **AD-16 — Threshold & flag-validation seam:** one hand-off signature for `--threshold`; argparse owns shape-only validation, `cli.run` owns path validation, usage errors disambiguated from exit `2` (C2, H9).
5. **Tighten AD-9/AD-10:** invalid category is normalized to `unsorted` in the classifier layer; organizer reject is defense-in-depth only (H6).

## Findings as JSON

```json
[
  {"lens":"adversarial","severity":"critical","story_pair":"S1 mobilenet x S2 dry-run/report","location":"AD-7 (spine:81) vs AD-12 (spine:111); organizer.py:26-32","trigger_condition":"AD-7 parks the predict-failure reason in the log with no OrganizeJob.reason field while AD-12 makes OrganizeReport the single source of errors-with-reasons; both stories letter-compliant.","guard_snippet":"AD-7 tightened: reason attaches to OrganizeJob.reason and surfaces in OrganizeReport.errors; logging optional, never sole carrier.","potential_consequence":"Corrupt files reported as moved successes with an empty errors section; AC-A4 'reason recorded' fails."},
  {"lens":"adversarial","severity":"critical","story_pair":"S1 mobilenet x S2 dry-run/report","location":"AD-3/AD-4/AD-8/AD-10; cli.py:134-136","trigger_condition":"No AD owns how --threshold reaches the classifier: AD-10 forbids cli-side routing, AD-4 pins get_classifier(name) and load/predict, AD-3 makes the flag the only override; two stories can extend the seam differently.","guard_snippet":"One hand-off signature (e.g. BaseClassifier.__init__(threshold) or get_classifier(name, threshold)); cli passes args.threshold and never re-routes.","potential_consequence":"Forked ABC signatures fail to merge, or --threshold goes dead while config-only routing violates AD-3."},
  {"lens":"adversarial","severity":"critical","story_pair":"S3 custom-cnn train x S2 dry-run/report","location":"AD-11 (spine:105), AD-8 (spine:87), envelope (spine:160)","trigger_condition":"AD-11 mandates writing the artifact unconditionally; no AD encodes dry-run zero-writes or exit codes/order for --train; NFR-A3 vs AD-11 contradiction unresolved.","guard_snippet":"AD-11 tightened: --train writes only without --dry-run; train failures map to FR-A8; explicit NFR-A3 models/ exception.","potential_consequence":"Repo mutated during a no-writes run; train error exit codes undefined for QA."},
  {"lens":"adversarial","severity":"high","story_pair":"S2 dry-run/report x S1 mobilenet","location":"AD-12 (spine:111) vs AD-8 (spine:87); cli.py:108-110,115-123","trigger_condition":"'Report printed after every run' vs load-before-organize exit 2 and scan-raise exit 1: no OrganizeReport exists on those paths, and cli 'only renders'.","guard_snippet":"AD-12 tightened: cli renders an organizer-owned empty_report() before every exit code; cli never instantiates OrganizeReport.","potential_consequence":"FR-A7/AC-A1 fail on the flagship TF-missing and empty-inbox demos."},
  {"lens":"adversarial","severity":"high","story_pair":"S2 dry-run/report x S6 organizer idempotency","location":"AD-8 (spine:87); organizer.py:185; tests/test_organizer.py:96-107","trigger_condition":"No AD says dry-run performs zero writes; AD-8's dry-run clause covers only the backend-down case, so a pre-creating mkdir story is AD-compliant.","guard_snippet":"AD-8 tightened: under --dry-run cli and organizer perform zero filesystem mutations; destinations computed on a virtual tree.","potential_consequence":"AC-A1 'folder untouched' fails depending on story order."},
  {"lens":"adversarial","severity":"high","story_pair":"S1 mobilenet x S4 exit-code acceptance","location":"AD-8 (spine:87), AD-7 (spine:81), demo-ops (spine:122)","trigger_condition":"AD-8 never binds when weights are fetched; fetch-in-load (exit 2) and fetch-in-predict (AD-7 per-file unsorted, exit 0) are both letter-compliant.","guard_snippet":"AD-8 tightened: all network/model I/O resolved inside load(); predict() must not fetch; any load() failure follows the exit-2/dry-run-0 matrix.","potential_consequence":"Offline machine exits 2 or silently files everything unsorted with exit 0; AC-A8/AC-A9 drift."},
  {"lens":"adversarial","severity":"high","story_pair":"S2 dry-run/report x S1 mobilenet","location":"AD-8 (spine:87), AD-10 (spine:99), AD-4 (spine:54)","trigger_condition":"AD-8 has cli synthesize unsorted jobs (category decision outside classifier) while AD-10 says routing happens once in the classifier; a config-registered null backend satisfies AD-4/AD-3 instead.","guard_snippet":"AD-8 tightened: fallback is cli-side job synthesis only; no fallback name added to config.MODEL_BACKENDS or --backend choices.","potential_consequence":"Two implementations of one path, widened CLI surface, double-counted unsorted jobs."},
  {"lens":"adversarial","severity":"high","story_pair":"S2 dry-run/report x S4 exit-code acceptance","location":"AD-12 (spine:111), AD-8 (spine:87); organizer.py:64-70; tests/test_organizer.py:120-141","trigger_condition":"AD-12's refused-vs-failed split creates a status counts_by_category does not exclude and report.skipped no longer aggregates; AD-8's exit-0 clause covers only 'skips'.","guard_snippet":"AD-12 tightened: refused and failed counters both excluded from counts_by_category; AD-8 exit-0 guarantee renamed to cover refused, failed, and skipped.","potential_consequence":"Per-category counts include not-moved files (breaks AC-A6/AC-A7 math) or refused files lose exit 0."},
  {"lens":"adversarial","severity":"high","story_pair":"S1 mobilenet mapping x S6 organizer allow-list","location":"AD-9 (spine:93) vs AD-10 (spine:99); organizer.py:164-171","trigger_condition":"AD-9 makes organizer reject off-list categories (skip, exit 0, file stays) while AD-10/FR-A2 route invalid labels to unsorted; mapping typo or CATEGORIES rename diverges by story.","guard_snippet":"AD-9 tightened: classifier normalizes and member-checks against config.CATEGORIES, converting non-members to unsorted with reason before reaching organizer; sanitize stays a path-traversal guard only.","potential_consequence":"Files silently stop being organized with exit 0; AD-9's stated prevention is unprevented."},
  {"lens":"adversarial","severity":"high","story_pair":"S1 mobilenet x S3 custom-cnn train","location":"AD-2 (spine:42), AD-6 (spine:66), AD-10 (spine:99); classifier.py:26-34","trigger_condition":"ClassificationResult owner/fields/home unassigned; AD-2 allows unlimited flat root modules while AD-6's graph names five nodes, so each story can fork or relocate the shared type.","guard_snippet":"AD-6 tightened: ClassificationResult and OrganizeJob stay in classifier.py/organizer.py; no new root module may be imported by more than one of cli/classifier/organizer.","potential_consequence":"Two same-named dataclasses at the seam; cli imports break when one story renames its module."},
  {"lens":"adversarial","severity":"high","story_pair":"S3 custom-cnn train x flag/config story","location":"AD-11 (spine:105) vs AD-3 (spine:48) + conventions (spine:120)","trigger_condition":"'Nothing else references a model path' directly contradicts 'default paths and every flag map to config.py' - two legal homes for DEFAULT_MODEL_PATH.","guard_snippet":"AD-11 rewritten: config.DEFAULT_MODEL_PATH is the only literal; classifier receives it as an argument; no other module contains 'custom-cnn.keras'.","potential_consequence":"Train writes one artifact, inference loads another - AD-11's own stated prevention."},
  {"lens":"adversarial","severity":"high","story_pair":"S2 dry-run/report (fixture flag) x S3 custom-cnn train (model-path flag)","location":"AD-8 (spine:87); cli.py:47-60","trigger_condition":"AD-8 sends flag validation to argparse (exit 2) while FR-A8 reserves 1 for filesystem errors; path-existence checks unclassified, and argparse's default 2 already equals backend-unavailable.","guard_snippet":"AD-8 tightened: argparse owns value-shape only; path existence validated in cli.run before side effects and mapped to exit 1; usage errors disambiguated from backend-unavailable.","potential_consequence":"AC-A8 unfalsifiable - exit-2 tests pass for the wrong reason; same bad path yields different codes per story."},
  {"lens":"adversarial","severity":"medium","story_pair":"S2 dry-run/report x S5 fixture/AC-A6","location":"AD-12 (spine:111), Deferred (spine:182)","trigger_condition":"Fixture reading must land outside cli ('only renders') but organizer's Owns list lacks it; accuracy floors live in open OQ-1 so the test story invents numbers calibration later changes.","guard_snippet":"AD-12 tightened: organizer.read_fixture_labels supplies expected labels; accuracy computed inside organize(); floors moved to a config constant (ACCURACY_FLOOR).","potential_consequence":"Fixture logic splits across modules; test and report disagree on the floor; --fixture has no config.py default."},
  {"lens":"adversarial","severity":"medium","story_pair":"S3 custom-cnn train x S2 dry-run/report","location":"AD-8 (spine:87), AD-11 (spine:105), AD-12 (spine:111)","trigger_condition":"No AD orders --train within run() or says whether train-only runs scan, require an inbox, or render a report.","guard_snippet":"AD-8/AD-11 tightened: order parse -> train (returns before scan; missing input dir exits 1 only without --train) -> scan -> load -> organize -> render.","potential_consequence":"Exit codes and report presence for --train depend on which story owns the early return."},
  {"lens":"adversarial","severity":"medium","story_pair":"PRD-literal flag story x code-literal flag story","location":"AD-3/AD-8; cli.py:41-70 vs product-requirements.md:39-40","trigger_condition":"No AD binds flag spellings/defaults to the PRD: -o/--output vs --output-dir, -r (recursion off) vs --no-recursive (on) - both stories AD-compliant and mutually exclusive.","guard_snippet":"New AD: argparse surface (names, aliases, defaults, recursion default) fixed by PRD section 2.1; reconcile existing code first; each flag has one config.py default.","potential_consequence":"Conflicting parser definitions; PRD-following graders see different behavior than the demo path."},
  {"lens":"adversarial","severity":"medium","story_pair":"S1 mobilenet mapping x flag/config story","location":"AD-3 (spine:48), Deferred (spine:182); classifier.py:55-73","trigger_condition":"Deferred assigns mapping ownership but not location; AD-3's closed tunable list omits it, so config.py, classifier.py, and a data/ JSON are all letter-compliant homes.","guard_snippet":"AD-3 extended: label->category mapping added to the tunable enumeration as a config.py structure; classifier reads it, never re-declares; no on-disk mapping file.","potential_consequence":"Two sources of label->category truth; AD-9 member check passes while one copy routes to a stale category."},
  {"lens":"adversarial","severity":"medium","story_pair":"S5 fixture tooling x S1 mobilenet","location":"AD-4 (spine:54)","trigger_condition":"AD-4 bans Pillow outside classifier.py with no fixture-tooling exemption; validating fixture images needs Pillow, so every compliant reading forces S5 to skip validation or violate AD-4.","guard_snippet":"AD-4 tightened: Pillow allowed in classifier.py and a root-level tools_*/tests fixture helper; TensorFlow/NumPy remain classifier-only; organizer/cli/config fully stdlib.","potential_consequence":"Fixture generation unbuildable under literal reading, or an agent pulls Pillow into organizer.py and weakens the QA firewall."},
  {"lens":"adversarial","severity":"medium","story_pair":"S3 binary-cross-entropy variant x S2 report","location":"AD-10 (spine:99); product-requirements.md:57","trigger_condition":"PRD allows binary OR categorical cross-entropy, but AD-10 defines confidence as top-1 probability of a mapped label - a single sigmoid has no five-way top-1.","guard_snippet":"AD-10 tightened: backends expose a five-element distribution over config.CATEGORIES; binary artifacts rejected at load() with availability error (exit 2) or ClassificationResult gains an explicit scale field.","potential_consequence":"Threshold, accuracy, and unsorted-share metrics meaningless for one backend; confidence semantics differ per story."},
  {"lens":"adversarial","severity":"low","story_pair":"S1 mobilenet x any second AI-assisted story","location":"AD-5 (spine:60); product-requirements.md:5","trigger_condition":"AD-5's ../PROMPTS_LOG.md is CWD-relative while the PRD calls it root; different launch directories append to different files.","guard_snippet":"AD-5 tightened: append to absolute <workspace-root>/PROMPTS_LOG.md (repo parent), resolved once at session start; never create a second log in-repo.","potential_consequence":"Audit trail splits across two files; append-only rule forbids repairing the gap."},
  {"lens":"adversarial","severity":"low","story_pair":"S3 custom-cnn train x S5 fixture","location":"AD-1 (spine:36), envelope (spine:160)","trigger_condition":"AD-1 binds all folder creation but rules only on case; the three-root write envelope is prose, so a fourth write root is AD-compliant.","guard_snippet":"AD-1 tightened: all writes confined to --output tree, models/, and the uv/Keras cache; any new on-disk folder must be named in an AD first.","potential_consequence":"Write scope drifts story by story - the same fight as NFR-A3 vs AD-11 (C3)."}
]
```
