---
title: 'Story 1.3: Reconcile the CLI surface to PRD 2.1'
type: 'feature'
created: '2026-10-02'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `cli.py` argparse drifts from PRD section 2.1 and AD-14: the output flag is `--output-dir` (PRD: `-o/--output`), recursion is `--no-recursive` default-on (PRD: `-r` off by default), `--threshold` accepts 0/negative/over-1 values at parse time (PRD valid range (0, 1]), and `--fixture`, `--train`, `--model-path` are missing entirely — so PRD-documented commands fail verbatim.

**Approach:** Rewrite the argparse surface to the PRD-frozen flags with every default imported from `config.py` (no literals), validate threshold shape in argparse, and add a TF-free test asserting the exact flag set, defaults, drift-name absence, and threshold rejection — pure surface change, no lifecycle/report behavior touched (Stories 1.4, Epics 2–4 own the rest).

</frozen-after-approval>

## Implementation Notes

- 2026-10-02: rewrote argparse to PRD-frozen surface — `-o/--output`,
  `-r/--recursive` (off default), `--backend/--threshold/--dry-run/--fixture/`
  `--train/--model-path/--verbose` + positional inbox; threshold shape validated
  by `_threshold()` in argparse (exit 2 on 0/out-of-range); all defaults from
  `config.py`; `run()` uses new attrs with a compat shim for old names.
  New `tests/test_cli_surface.py` (8 tests). Verified: 39 passed
  (17 organizer + 7 config + 15 surface); `--help` lists frozen flags;
  `-t 0` exits 2; `main.py data/inbox --dry-run` exits 0 on empty inbox;
  stdlib-only imports clean.

## Review Triage Log

- 2026-10-02 (step-oneshot inline, no subagent runtime): blind-hunter
  N = min(floor(sqrt(8) + 1), 10) = 3 candidates traced; edge-case enumeration
  over flag renames + threshold validator + new-flag defaults; verification-gap
  trace over 39-test suite. Verdicts:
  - `false` — `-r` flip breaks existing callers: `run()` reads new attrs with
    a compat shim for old `output_dir`/`no_recursive` namespaces; organize
    path unchanged; dry-run on empty inbox exits 0.
  - `false` — `--train/--fixture/--model-path` parsed but unused (dead flags):
    intended stub surface for Epics 2–4 (lifecycle/train/report own behavior);
    parse-only in 1.3 is the spec, not a gap.
  - `false` — argparse exit 2 collides with backend-unavailable exit 2:
    AD-8 owns this split (shape=2 in argparse, backend-down=2 in run);
    threshold rejection verified at parse time before any side effect.
  - `low → rejected` — compat shim adds temporary branching: removed in 1.4
    when `run()` lifecycle is rewritten; keeps this diff surface-only.
- Result: no patch, no HALT, nothing deferred. ACs verified: `--help` exact;
  drift names rejected; `-t 0/>1` exits 2; 39 passed.
