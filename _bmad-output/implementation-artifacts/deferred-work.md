- source_spec: `D:\Python Projects\meme-classifier/_bmad-output/implementation-artifacts/spec-3-1-collision-free-filing-fr-a4-fr-a5.md`
  summary: Decide what dry-run should plan when two jobs share a basename (currently both plan the same destination since dry-run reserves no names).
  evidence: Real behavior confirmed by review of organizer.py:180-184 — dry-run calls unique_destination without creating directories, so same-name jobs duplicate the planned destination; the preview contract belongs to Story 3.4.
- source_spec: `D:\Python Projects\meme-classifier/_bmad-output/implementation-artifacts/spec-4-2-custom-cnn-backend-via-model-path-fr-a2-nfr-a4.md`
  summary: Sync stale NotImplementedError-era prose (AGENTS.md known-pitfalls line, README backend section, docs/system-architecture.md) with the implemented custom-cnn body.
  evidence: Review of the 4-2 diff confirmed the backend now loads/predicts while three docs still state backends raise NotImplementedError; Story 4.3 already owns the docs-sync pass so this folds into it rather than scattering doc edits across stories.

## Deferred from: code review of spec-4-3-demo-readiness-and-oq-calibration (2026-10-06)
- source_spec: `_bmad-output/implementation-artifacts/spec-4-3-demo-readiness-and-oq-calibration.md`
  summary: Defense-facing doc completeness — mapping-table location, MobileNetV2 weight source/offline behavior, and threshold value surfaced in system-architecture.md / data/README.md for defense readability.
  evidence: Code review 2026-10-06 (blind-hunter); deferred because Phase 6 owns defense-facing completeness via the demo script + professor Q&A sheet.
