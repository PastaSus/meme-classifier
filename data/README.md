# `meme-classifier` working data

- **`inbox/`** — drop unorganized meme/reaction images here (or pass any folder as the CLI's
  first positional argument). Nested subfolders are scanned recursively by default.
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
