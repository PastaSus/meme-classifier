---
title: 'Story 3.1: Collision-free filing (FR-A4, FR-A5)'
type: 'feature'
created: '2026-10-03'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `organize()` already moves with `makedirs` + `shutil.move` and suffixes collisions via `unique_destination`, but three acceptance paths have no test proof: suffix exhaustion (1000 attempts → `skipped`), only-allow-listed folders ever created, and the stdlib-only module constraint (NFR-A1).

**Approach:** Test-only change — add the three missing proofs to `tests/test_organizer.py` (exhaustion via a monkeypatched cap so no 1001-file fixture is needed; mixed valid/invalid batch asserting only the valid folder appears; AST import check against `sys.stdlib_module_names` plus first-party `config`). No production code changes expected; if any AC fails, fix `organizer.py` minimally instead.

</frozen-after-approval>

## Implementation Notes

- 2026-10-03: AC audit confirmed `organizer.py` already implements every 3-1
  behavior (`makedirs` on demand + `shutil.move`, `unique_destination` suffix
  chain with `MAX_COLLISION_SUFFIX`, `FileExistsError ⊂ OSError` → `skipped`,
  default allow-list `CATEGORIES`, stdlib-only imports) — so this story is
  test-only, no production diff. Added to `tests/test_organizer.py`:
  `test_suffix_exhaustion_is_skipped_not_fatal` (cap monkeypatched to 2,
  asserts `skipped` + "Could not find a free name" detail + source survives),
  `test_only_allow_listed_folders_are_created` (mixed batch → only
  `cat-memes/` appears), and module-level `test_organizer_module_is_stdlib_only`
  (AST import check vs `sys.stdlib_module_names` + first-party `config`).
- Verification: `uv run --with pytest pytest -q` — 79 passed (76 existing + 3
  new).
- Review (blind-hunter, N = min(floor(sqrt(16.74) + 1), 10) = 5 → 9 findings):
  patched 5 findings (4 groups), deferred 1, rejected 2 as false — see Review
  Triage Log. Final suite: 81 passed (76 existing + 5 new).

## Review Triage Log

- `low → patched` — exhaustion proof never pinned the production cap: added
  `assert organizer.MAX_COLLISION_SUFFIX == 1000` before monkeypatching.
- `medium → patched` — intra-batch collision (the cli-shaped single-`organize`
  call with two same-basename jobs) had no proof: added
  `test_intra_batch_collision_is_renamed` (`moved == 2`, `cat.jpg` + `cat-1.jpg`,
  both sources gone).
- `low → patched` — allow-list test passed `allowed=` explicitly and never
  checked outside the output root: dropped the arg (exercises the `None`
  default cli relies on) and asserted `tmp_path` holds only `inbox`/`organized`.
- `low → patched` — stdlib check located `organizer.py` via test-relative path:
  now uses `organizer_mod.__file__`; dynamic-import/transitive coverage deemed
  unnecessary (full-file read confirms neither exists; `config` imports only
  `pathlib`).
- `low → patched` — `unique_destination` filename-shape edges untested: added
  multi-dot (`archive.tar-1.jpg`) and extensionless (`README-1`) cases.
- `defer` — dry-run plans duplicate destinations for same-basename jobs
  (no name reservation in preview): real, but the preview contract belongs to
  Story 3.4 → recorded in `deferred-work.md`.
- `false` — "79 passed contradicts 17-test baseline / 1000-attempts wording":
  the 17-test figure in `AGENTS.md` is stale pre-epic-2 drift (managed block,
  not this story's to fix); "1000 attempts" matches the AC and the code's own
  error message verbatim.
- `false` — spec/sprint still `in-progress` with untracked files: mid-workflow
  state at review time, resolved by this finalize step.

