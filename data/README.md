# `meme-classifier` working data

- **`inbox/`** — drop unorganized meme/reaction images here (or pass any folder as the CLI's
  first positional argument). Nested subfolders are scanned only with `-r`/`--recursive`
  (recursion is off by default).
- **`demo-labeled/`** — 9 sample memes pre-sorted into 4 category folders for the live
  `--train` demo (the same files as `inbox/`, minus the 2 unlabelled extras). Never
  run inference directly on this tree (it would drain it) — copy it first.
- **`organized/`** — created automatically; each run files images into labelled subfolders:

  ```
  organized/
  ├── gym-memes/
  ├── cat-memes/
  ├── chaotic-screenshots/
  ├── wholesome-posts/
  └── unsorted/
  ```

Supported extensions: `.jpg .jpeg .png .gif .bmp .webp` (hidden files/folders are ignored).

> The input and output folders may overlap safely: files already inside `organized/` are
> excluded from scanning.

> Defense demo (OQ-2, 2026-10-04): live `--train` is demoed (seconds, offline-safe on
> small labeled trees) with a pre-built `.keras` artifact as fallback. Training writes
> only to `--model-path` (default `models/custom-cnn.keras`); no weights are committed.
