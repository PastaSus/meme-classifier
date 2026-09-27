# PRD v2.0 → Architecture Spine Reconciliation

**Source:** `docs/product-requirements.md` (Final v2.0), read in full.
**Target:** `ARCHITECTURE-SPINE.md` (draft, 2026-09-27).
**Date:** 2026-09-27.

## Coverage summary

| PRD item | In spine | Where |
| --- | --- | --- |
| FR-A1 scan/extensions/recursion; missing dir → exit 1 | Yes | Capability map; AD-8 |
| FR-A2 backends behind one interface | Yes | AD-4, AD-10, capability map |
| FR-A3 confidence + threshold default 0.45 → `unsorted` | Partial | AD-10, conventions row (range stated, validation not owned) |
| FR-A4 move / FR-A5 collision suffix | Yes | AD-7/AD-9, conventions (`stem-N.suffix`) |
| FR-A6 dry-run backend-less → `unsorted` + warning, exit 0 | Yes | AD-8 |
| FR-A7 report after **every** run incl. empty input; errors refused-vs-failed | Yes | AD-12 ("printed after every run, including empty input") |
| FR-A8 exit codes 0/1/2 semantics | Yes | AD-8 (matches PRD exactly) |
| FR-A9 `--train` / `--model-path` | Partial | AD-11 (flow yes; data contract no) |
| NFR-A1 stdlib organizer | Yes | AD-4 |
| NFR-A2 allow-list / path-traversal | Yes | AD-9 |
| NFR-A3 idempotent, no writes outside output root | Partial | capability map + operational envelope (conflicts with AD-11) |
| NFR-A4 CLI flags only, incl. `--model-path` | Yes | AD-3, AD-11 (absent from capability-map table, but bound) |
| NFR-A5 Python 3.13 / TF 2.21.x / uv, TF-free tests | Yes | Stack row, AD-4 |
| Quiet: report-after-every-run | Yes | AD-12 |
| Quiet: exit-code semantics | Yes | AD-8 |
| Quiet: threshold range validation | **No** | see Gap 2 |
| Quiet: fixture / accuracy obligations | **No** | see Gap 3 |
| Quiet: `--train` data contract | **No** | see Gap 1 |

## Gaps

1. **FR-A9 `--train` data contract dropped** — AD-11 says only "any user-labeled category tree"; the PRD's concrete contract (`<root>/<category>/*.jpg`, artifact written to `--model-path` default `models/custom-cnn.keras`, ~10 labeled images per category assumption) is not specified as a rule.

2. **Threshold range validation unowned** — PRD FR-A3 requires `--threshold` valid in (0, 1]; the spine states the range as a conventions fact ("confidence float in (0, 1], default 0.45") but no AD assigns validation of out-of-range input or its error/exit behavior to any module.

3. **Fixture / accuracy obligations under-specified** — AD-12 allows "optional fixture accuracy" and the seed mentions `tests/fixtures/labeled/`, but there is no flag/mechanism for supplying a labelled fixture at run time, and neither AC-A6's ≥6/10 floor nor AC-A7's ≤80% `unsorted` counter-metric appears anywhere (Deferred carries only OQ-1's accuracy floor, not AC-A7).

4. **Contradiction: NFR-A3 "zero writes outside output root" vs AD-11** — the operational envelope claims "output confined to the tree under `--output` (NFR-A3)" while AD-11 writes the CNN artifact to `--model-path` (`models/`, outside `--output`) and the conventions row allows the ImageNet weight download to write a cache; the spine repeats the PRD's internal conflict without resolving it.

5. **Wrong AD citation for NFR-A3 row** — the capability map attributes idempotent re-filing to "scan `exclude=` output root + AD-5 suffixing", but AD-5 is the append-only prompt-log rule; collision suffixing is FR-A5, governed by AD-7/AD-9 per the FR-A4/FR-A5 row.

## Contradictions checked and cleared

- Exit-code semantics (PRD FR-A8/AC-A8/AC-A9) match AD-8 exactly; AD-7's "exit stays 0" applies to single-file predict failures, not load-stage unavailability — no conflict with exit `2`.
- Dry-run backend-less behavior (FR-A6) matches AD-8.
- Threshold routing / unmapped-label rule (FR-A3) matches AD-10.
- PRD's Python 3.13 + TF 2.21.x (NFR-A5) matches the Stack row.
- No spine rule contradicts FR-A1, FR-A4, FR-A5, NFR-A1, or NFR-A2.
