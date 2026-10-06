---
title: 'Story 4.3: Demo readiness and OQ calibration'
type: 'feature'
created: '2026-10-04'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '704a84b'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The tool is fully implemented but not defense-ready: three docs still claim backends raise `NotImplementedError`, OQ-1 floors await Tech Lead calibration sign-off, OQ-2's demo-scope decision is unrecorded, and no verified AC-A1..A11 pass is recorded.

**Approach:** Verify the full suite plus manual demo paths (dry-run, offline exit-2/fallback, train→inference loop), sync stale prose in README, system-architecture, data/README, bmad-plan board and the AGENTS.md pitfall line, then apply the human's OQ-1/OQ-2 decisions (floors change only on explicit sign-off; otherwise first-pass values stand with pending-real-data rationale recorded).

**Decisions (human, 2026-10-04):** OQ-1 — keep `ACCURACY_FLOOR=0.6` / `UNSORTED_SHARE_FLOOR=0.8`; real calibration pending labeled real memes (synthetic fixtures cannot measure mapping quality). OQ-2 — live-train demoed (seconds, offline-safe) with a pre-built artifact as fallback.

## Boundaries & Constraints

**Always:** Every AC-A1..A11 keeps at least one automated test; verification runs recorded in Implementation Notes; floor values change only on explicit Tech Lead sign-off; OQ-2 decision recorded in docs either way; the 4-2 deferred docs entry is consumed here.

**Never:** No invented calibration numbers; no behavior/code changes beyond docs and calibration constants (tool is feature-complete); no committed `.keras`/weights; no AGENTS.md restructuring (one pitfall-line truth update only; block refresh stays with project-context).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| FULL_PASS | `uv run --with pytest pytest -q` | entire suite green, TF-gated tests run-or-skip cleanly | N/A |
| DEMO_PATHS | manual CLI runs (dry, offline, train loop) | dry-run plans with warning exit 0; cold/rometfail exit 2 non-dry; train→custom-cnn files images | N/A |
| DOCS_SYNC | stale prose locations | NotImplementedError claims replaced with implemented behavior + pointers | N/A |
| OQ_APPLY | human OQ-1/OQ-2 answers | floors updated + sign-off recorded, or rationale recorded with first-pass kept | N/A |

</frozen-after-approval>

## Code Map

- `README.md:70`, `docs/system-architecture.md:61-71,80`, `docs/bmad-plan.md:32-34`, `data/README.md:3`, `AGENTS.md:33` — stale prose updates; reuse implemented behavior as source of truth.
- `config.py:52-53` — floors change only per OQ-1 answer, else untouched.
- Verification: full suite + manual CLI demo paths; no new test files expected (coverage complete; add only if a demo path exposes a hole).

## Tasks & Acceptance

**Execution:**
- [x] docs sync -- replace NotImplementedError-era prose + plan board + data/README -- defense reads true docs
- [x] verification pass -- suite green + manual demo paths recorded -- AC-A1..A11 demonstrable
- [x] OQ-1/OQ-2 -- apply human answers -- calibration and scope decided by the owner, not invented

**Acceptance Criteria:**
- Given the complete tool, when the suite and manual demo paths run, then all green with results recorded and offline behavior verified
- Given the OQ-1 answer, when applied, then floors are either updated with sign-off or kept with pending-real-data rationale
- Given the OQ-2 answer, when applied, then the demo scope is recorded in docs

## Implementation Notes

- 2026-10-04: docs sync — README status table now Done (both backends + `--train`);
  system-architecture §2.3 statuses Implemented, `BackendUnavailable` (not
  `NotImplementedError`) with dry-run fallback, §2.4 AC-A4 reason-recorded wording;
  bmad-plan Phase 4 Done / Phase 6 In progress; data/README OQ-2 demo-scope note;
  AGENTS.md pitfall line only (block refresh stays with project-context);
  PRD §2.6 OQ-1/OQ-2 decided; config floors untouched, comment records OQ-1
  rationale + sign-off rule; `.gitignore` guards `models/`/`*.keras`;
  4-2 deferred docs entry consumed by this story's sync (ledger entry retained
  append-only per workflow rule; 3-1 entry left for its owner).
- 2026-10-04: OQ-1 applied — `ACCURACY_FLOOR=0.6` / `UNSORTED_SHARE_FLOOR=0.8` kept
  per human decision; real calibration pending labeled real memes.
- 2026-10-04: OQ-2 applied — live `--train` demoed, pre-built artifact fallback;
  recorded in PRD §2.6 + data/README.
- 2026-10-04: AC-A1..A11 coverage confirmed — every AC has ≥1 automated test
  (A1 ten-file dry-run, A2 allow-list filing, A3 collision suffix, A4 corrupt→unsorted
  with reason, A5 TF-free suite, A6/A7 floor asserts, A8 exit-code matrix,
  A9 dry-run fallback, A10 idempotency byte-identity, A11 train→inference e2e);
  no new tests added.

## Spec Change Log

## Review Triage Log

- Edge-case-hunter and verification-gap layers reported no findings.
- `false` — `.gitignore` needs a `.gitkeep` for `models/`: `train_labeled_model` creates parents (`mkdir parents=True`), so fresh clones work with nothing to document.
- `false` — empty Change/Triage headings: the template's specified pre-review state; triage rows land with this pass.
- `false` — matrix Error Handling all N/A: rows describe verification checks, not fallible operations; a failing suite means fix the failure (the workflow itself).
- `low → rejected` — data/README lacks a demo mini-manual: the demo script + Q&A sheet are Phase 6's chartered work (still Pending); duplicating them here scatters ownership.
- `false` — architecture table omits TF version/mapping/threshold detail: sync means consistency with implementation and spine (achieved); detail expansion was never chartered.
- `false` — README Tests section unsynced: verified it contains only the bare command, no counts — nothing to synchronize.
- `low → rejected` — OQ sign-off lacks a Tech Lead name: single-human project, decision captured in-session with date + rationale; authorship traceable via session and git history.
- `low → patched` — manual demo runs unreproducible: host re-ran all three paths and recorded exact commands + outcomes above.

### Review Findings (code review 2026-10-06; layers: blind-hunter, edge-case-hunter, verification-gap, acceptance-auditor)

- [x] [Review][Decision] Spec header says done, tracker says review — spec line 5 `status: 'done'` vs `sprint-status.yaml` `4-3: review` / `epic-4: in-progress`. Close-out call needed: mark story `done` now, or keep open. → Resolved 2026-10-06: marked done (no high/medium blockers).
- [x] [Review][Patch] bmad-plan Phase 4 marked Done while 4-3 still in review [docs/bmad-plan.md:32-34] → Resolved 2026-10-06 by close-out; statement now true, no edit needed.
- [x] [Review][Patch] README Tests section has bare command only, no count/timing to match AGENTS.md [README.md:73-78] → Applied 2026-10-06.
- [x] [Review][Defer] Defense-facing doc completeness (mapping-table location, MobileNet weight source/offline behavior, threshold value in arch/data README) [docs/system-architecture.md, data/README.md] — deferred: Phase 6 owns defense-facing completeness (demo script + Q&A sheet).

Rejected:
- `false` — .gitignore `models/` unanchored / `*.h5` missing: the tool only ever writes one `.keras` path (`train_labeled_model` tmp+replace); no stray artifact can occur.
- `rejected` — spec Change Log empty / no AC→test table: fix would edit the spec under review; coverage is enumerated in Implementation Notes.
- `rejected` — manual-run logs/versions not retained: fix would edit the spec under review; commands + outcomes + dates recorded, TF pinned in PRD NFR-A5.
- `false` — OQ-1 floors comment-only guard / no follow-up ticket: keeping first-pass values with pending-real-data rationale was the explicit human OQ-1 decision, recorded in spec + PRD §2.6.
- `false` — AGENTS.md two-line change vs one-line charter: both hunks are truthful updates (test count 17→158 recorded in Implementation Notes); no restructuring occurred.

## Verification

**Commands:**
- `uv run --with pytest pytest -q` -- expected: full suite green
- 2026-10-04: `uv run --with pytest pytest -q` → 158 passed (TF-gated tests ran).
- 2026-10-04 manual demo paths (temp dirs, cleaned after): dry-run fallback
  (custom-cnn, missing artifact) → exit 0, 3 planned to unsorted, zero writes;
  same setup non-dry → exit 2, inbox untouched; `--train` on 8 images
  (2 categories) → artifact saved, custom-cnn inference filed 2/2 correctly,
  inbox drained. No `.keras`/`models/` left in repo.
- 2026-10-04 (host verification): suite re-run → 158 passed; floors confirmed
  unchanged (0.6/0.8); repo holds no `.keras`/`models/`; fixed two misses —
  data/README recursion default corrected (off unless `-r`) and AGENTS.md test
  count updated (158 tests, ~15s).
- 2026-10-04 (host re-ran all demo paths; temp dirs cleaned after):
  `py main.py <3-jpg-inbox> --dry-run -o <out>` (TF-free) → exit 0,
  `planned: 3 | moved: 0`, no `out/` created; same without `--dry-run` →
  exit 2, inbox intact, no `out/`; `uv run python main.py <missing-inbox>
  --train <10-img-copy-of-fixture> --model-path <tmp>/custom-cnn.keras` →
  exit 0, `Training complete: 10 samples across 5 categories`; then
  `--backend custom-cnn --model-path <artifact> -r` on that tree → exit 0,
  `moved: 10`, notably all 10 placed in their own labeled categories
  (10/10 fixture accuracy on the trained backend), inbox drained.
