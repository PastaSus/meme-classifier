# Demo Script — Meme & Reaction Image Organizer (defense, ~10 min)

Verified 2026-10-06 on the committed sample data (11 inbox memes, 9-image
`data/demo-labeled/` tree). All commands assume the repo root. Never run bare
`python` (broken Store stub) — use `py` or `uv run python`.

## Setup (night before)

1. `uv sync` — dependencies in place.
2. Confirm `data/inbox/` holds 11 memes and `data/demo-labeled/` holds 9 in 4
   category folders (`git status --short` clean is the check).
3. Pre-cache MobileNetV2 weights (first load downloads ~14 MB): run Act 1 once
   with internet. After that the whole demo is offline-safe.
4. Fallback artifact (OQ-2): if live `--train` is risky in the room, pre-build
   `models/custom-cnn.keras` beforehand via Act 2 and carry the file — it is
   gitignored, so it travels separately, never in the repo.

## Act 1 — zero-shot preview (2 min, works even with TF uninstalled)

```bash
py main.py data/inbox --dry-run
```

Say: *"FR-A6 — a preview that touches nothing and survives a broken
environment."* Expected (verified): `Scanned 11`, `planned: 11 | moved: 0`,
exit 0. Point at two lines:

- `grumpy-cat.jpg → cat-memes 79.5%` — zero-shot catches what the 15-label
  mapping covers (tabby → cat-memes).
- Everything else → `unsorted` with a reason (`unmapped label 'comic_book'`,
  `confidence 0.08 < 0.45`) — the tool says *I don't know* instead of guessing.

## Act 2 — teach it: live `--train` (2 min)

```bash
cp -r data/demo-labeled /tmp/demotrain
py main.py --train /tmp/demotrain --model-path /tmp/custom-cnn.keras
```

Say: *"FR-A9 — the lab CNN trains on folders I label myself."* Expected
(verified): `Training custom-cnn on 9 image(s) ... (epochs=5, batch=16,
image=64x64)` → `Training complete: 9 samples across 4 categories`, exit 0,
seconds, offline. Train on the **copy** — training never touches the inbox,
but inference (Act 3) drains its input, and the committed tree must stay
pristine for the professor's own run.

## Act 3 — inference with your own model (3 min)

```bash
cp -r data/demo-labeled /tmp/demoinfer
cp data/inbox/distracted-boyfriend.jpg data/inbox/drake.jpg /tmp/demoinfer/chaotic-screenshots/
py main.py /tmp/demoinfer -r -b custom-cnn --model-path /tmp/custom-cnn.keras -o /tmp/demoout --fixture /tmp/demoinfer
```

Say: *"Nine taught, two strangers."* Expected (verified): `moved: 11`,
`Fixture accuracy: 10/11 (90.9%)`, exit 0. Raise the two honest points
before the professor does:

- `buff-doge.png → chaotic-screenshots 49%` — 9 samples and 5 epochs
  memorize, they don't understand; the white background fooled it. More
  labeled data fixes this (see Q&A).
- Drake + Distracted Boyfriend land in `chaotic-screenshots` — custom-cnn
  knows only 4 categories, so strangers go to the *nearest*, never
  `unsorted`. Contrast with mobilenet (Act 1), which routes unknowns to
  `unsorted` by design. Different backends, different honesty policies.

## Act 4 — the safety net (2 min)

```bash
py main.py data/inbox -b custom-cnn               # exit 2, inbox untouched
py main.py data/inbox -b custom-cnn --dry-run     # exit 0, 11 planned to unsorted + warning
py main.py data/nonexistent                       # exit 1 + zeroed report
```

Say: *"FR-A8 — every failure mode has a number, and a report prints before
every return, even the failures."* Show `data/organized/` was never created
by the dry runs.

## Reset after rehearsal

Real runs **move** files (inbox drains). Restore from git — the committed
trees are the pristine source:

```bash
git checkout -- data/inbox        # restore files drained by a real run
git clean -fd data/organized      # remove demo output (tracked .gitkeep stays)
git status --short data/          # expect clean
```

Prefer rehearsing on `/tmp` copies (Acts 2–3 above do exactly this) so the
committed trees stay pristine.

## If the room has no internet / no TensorFlow

- Act 1 still works (`--dry-run` plans everything to `unsorted`, exit 0).
- Acts 2–3 need TF + the fallback artifact from Setup step 4.
- Act 4 is the star: it *demonstrates* the offline behavior deliberately.
