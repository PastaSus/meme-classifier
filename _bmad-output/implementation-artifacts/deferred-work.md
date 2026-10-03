- source_spec: `D:\Python Projects\meme-classifier/_bmad-output/implementation-artifacts/spec-3-1-collision-free-filing-fr-a4-fr-a5.md`
  summary: Decide what dry-run should plan when two jobs share a basename (currently both plan the same destination since dry-run reserves no names).
  evidence: Real behavior confirmed by review of organizer.py:180-184 — dry-run calls unique_destination without creating directories, so same-name jobs duplicate the planned destination; the preview contract belongs to Story 3.4.
