# Meme & Reaction Image Organizer

**Project 1 — Image Detection** · University semifinals case study · BMAD-managed
*(see root `PROMPTS_LOG.md` and `docs/`)*

Scans an unorganized folder of images, classifies each one as a **gym meme**, **cat meme**,
**chaotic screenshot**, **wholesome post** (or `unsorted` when uncertain), and automatically
files them into labelled subfolders using Python's `os` and `shutil` modules.

## Categories

| Folder | Meaning |
|---|---|
| `gym-memes` | lifting / fitness humor |
| `cat-memes` | cat templates & reaction cats |
| `chaotic-screenshots` | absurd, cursed screenshots |
| `wholesome-posts` | warm, feel-good content |
| `unsorted` | low-confidence / unrecognized (safety net) |

## Install

```bash
cd meme-classifier
uv sync   # organizer + tests run even WITHOUT tensorflow
```

## Usage

```bash
# dry run — show planned moves, touch nothing
python main.py data/inbox --dry-run

# classify with the default MobileNetV2 backend
python main.py data/inbox -o data/organized

# custom CNN backend, stricter confidence threshold
python main.py path/to/images -b custom-cnn -t 0.6

# exit codes: 0 = success, 1 = filesystem error, 2 = backend unavailable
```

Drop images into `data/inbox/` (subfolders included); results appear under
`data/organized/<category>/`. Colliding filenames are auto-renamed (`cat.jpg`, `cat-1.jpg`) —
existing files are never overwritten.

## Project structure

```
meme-classifier/
├── main.py          # entry point
├── cli.py           # argparse + scan→classify→organize→report orchestration
├── config.py        # categories, extensions, threshold, default paths
├── classifier.py    # BaseClassifier ABC + mobilenet / custom-cnn backends
├── organizer.py     # stdlib-only scanning + shutil.move organization
├── conftest.py      # pytest import bootstrap
├── tests/           # QA suite (organizer — no TensorFlow needed)
├── data/            # inbox/ + organized/ working folders
├── pyproject.toml
├── uv.lock
└── .python-version
```

## Implementation status (BMAD)

| Phase | Persona | Status |
|---|---|---|
| Specs | PM Agent | Done — `docs/product-requirements.md` |
| Design | Architect Agent | Done — `docs/system-architecture.md` |
| Organizer/CLI scaffolding | Tech Lead | Done — fully implemented & tested |
| MobileNetV2 + custom CNN backends | Dev Agent | Done — both backends implemented & tested (`mobilenet` zero-shot ImageNet mapping; `custom-cnn` via `--model-path` artifact from `--train`) |
| Adversarial review | QA Agent | Pending |

## Tests

```bash
cd meme-classifier
uv run --with pytest pytest -q
```
