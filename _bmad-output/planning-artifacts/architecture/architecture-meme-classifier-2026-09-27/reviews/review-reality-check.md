# Review — Reality Check (external/ asserted-vs-verified)

- **Target:** `ARCHITECTURE-SPINE.md` (meme-classifier, created/updated 2026-09-27)
- **Lens:** verify every committed decision was web-researched or reality-checked, not asserted from training data — current library/framework versions, technology still exists/fits, live defaults; flag anything out of date that wasn't confirmed against the web, the existing project, or the current starter.
- **Date of review:** 2026-09-27 (same day as the spine)
- **Method:** PyPI JSON API (`pypi.org/pypi/<pkg>/[version]/json`), tensorflow.org install tables, TF GitHub issue/RELEASE.md, keras-team/keras source, `uv`/`py` CLI probes on the actual host, repo file sweep (`requirements.txt`, `docs/`, `config.py`, root tree).

## Verdict

**PASS WITH FINDINGS** — the two load-bearing claims (TF 2.21.0 is latest stable with cp313 wheels; no stable TF for cp314) check out against PyPI, and MobileNetV2/uv-3.13/weight-size claims were verified; but the Stack table's "Python 3.13 (project-local via uv)" is asserted rather than instantiated (the documented command actually runs 3.12.13), and the cp314 claim already has a dated counter-example (2.22.0rc0, five days before the spine's "verified" stamp). No critical findings.

## Findings

| ID | Sev | Claim | Evidence | Recommendation |
| --- | --- | --- | --- | --- |
| RC-1 | **high** | Stack: `Python 3.13 (project-local via uv; system 3.14 untouched)` stated as settled fact. | No `pyproject.toml`, `.python-version`, `uv.lock`, or `.venv` anywhere in/above the repo (checked `ls -a`, parent dirs). Verified live: `uv run --with pytest python -V` inside the repo resolves to **CPython 3.12.13** (uv-managed, no project found) — not 3.13. Nothing in the repo creates or pins 3.13; NFR-A5's row itself defers "uv project config" to *build phase*, contradicting the Stack table's present-tense assertion. | Either soften Stack to "target 3.13, not yet enforced (build phase)" or add `.python-version`/`pyproject.toml` now so the documented `uv run` command matches NFR-A5. Also note 3.12 would silently satisfy `tensorflow>=2.21` (cp312 wheels exist), so the requirement can go unmet without any error. |
| RC-2 | **medium** | PRD/spine: "no stable TF wheel exists for Python 3.14 (verified 2026-09-27)". | **True for stable today** — PyPI `tensorflow` latest = 2.21.0 (uploaded 2026-03-06), wheel set cp310–cp313 only (incl. `cp313-win_amd64`), matching tensorflow.org's install table. **But** `tensorflow 2.22.0rc0` was uploaded **2026-09-22** and already ships `cp314` wheels for win_amd64/linux/mac. So the fact was already qualified-out-of-date at the moment it was stamped "verified", and it expires at 2.22 final. | Add a scope/expiry note: "stable ≤2.21.x has no cp314; 2.22.0rc0 (2026-09-22) does — claim re-check at 2.22 final." Also record that the `<2.22` pin means the project will *not* inherit cp314 support even after release. |
| RC-3 | **medium** | Stack/`requirements.txt`: `numpy >=1.24`. | Confirmed against TF 2.21.0's own PyPI metadata: it requires **`numpy>=1.26.0`** (and TF's tested lock `requirements_lock_3_13.txt` pins `numpy==2.1.3`). The project's floor is looser than the dependency it must coexist with and appears asserted from habit, not checked. Harmless in a full install (pip intersects constraints) but wrong as a stated stack fact; compatibility of the *current* numpy (2.5.3) with TF 2.21 was not confirmable statically (TF declares no upper bound). | Raise floor to `>=1.26` (or pin the TF-tested 2.1.x) and note the version was validated against TF's metadata, not guessed. |
| RC-4 | **low** | Stack: `Pillow >=10.0`, `pytest >=8.0` (and `numpy >=1.24`). | Current PyPI versions are **Pillow 12.3.0**, **pytest 9.1.1**, **numpy 2.5.3** — i.e. floors are 1–2 majors stale. They are lower bounds with no upper cap, so installs resolve current; but a "Stack" table implies researched versions, and neither floor nor current major is footnoted. pytest 9 vs. the repo's `pytest.ini`/`conftest.py` compatibility was not exercised. | Mark the columns explicitly as *minimums* with "current as of 2026-09-27: 12.3.0 / 9.1.1 / 2.5.3", or bump floors. |
| RC-5 | **low** | Stack: `uv 0.12.1 (env/tool runner)`. | Local binary verified: `uv --version` → `0.12.1 (… 2026-07-31)`, so the number is a real snapshot, not invented. But latest uv is **0.12.19**; the table doesn't say the value is an observed host version rather than a project requirement, and the repo has no uv config to pin it. | Label as "host uv (observed)" or drop the patch pin. |
| RC-6 | **low** | Stack table omits `keras`. | TF 2.21.0 requires `keras>=3.12.0`; current keras is **3.15.1**, unbounded — and keras is exactly where the committed API (`tf.keras.applications.MobileNetV2`) lives. The transitive dependency that carries the chosen API is unpinned in both the spine and `requirements.txt`. | Add a `keras >=3.12 (TF-managed)` row or note it as transitive. |

## Claims verified as TRUE (no action)

| Claim | Verification |
| --- | --- |
| TF **2.21.0 is latest stable** with **Python 3.13 wheels** (as of 2026-09-27) | PyPI `tensorflow` info version `2.21.0`; release list shows 2.21.0 (2026-03-06) then `2.22.0rc0` only; wheel filenames include `tensorflow-2.21.0-cp313-cp313-win_amd64.whl` / manylinux / macosx. tensorflow.org install page lists 2.21.0 cp313 for Linux/macOS/Windows. |
| **No stable TF has cp314 wheels** | Same wheel list: cp310–cp313 only; corroborated by TF issue #102890 (uv resolver hint: "wheels … v2.21.0 … cp310, cp311, cp312, cp313"). See RC-2 for the RC caveat. |
| **MobileNetV2 available via `tf.keras.applications`** in TF 2.21 | TF 2.21 requires `keras>=3.12.0`; `keras/src/applications/mobilenet_v2.py` defines `def MobileNetV2(...)` on master; `https://www.tensorflow.org/api_docs/python/tf/keras/applications/MobileNetV2` returns 200 and names the symbol. Fits: zero-shot ImageNet classification as designed. |
| **Python 3.13 + uv-managed interpreter is viable** | `uv python list` shows `cpython-3.13.14-windows-x86_64-none <download available>`; uv 0.12.1 present and working (RC-1 is about enforcement, not availability). |
| First mobilenet run downloads **~14 MB** ImageNet weights, cache **outside the repo** | Weight URL `…/mobilenet_v2/mobilenet_v2_weights_tf_dim_ordering_tf_kernels_1.0_224.h5` → HTTP 200, `Content-Length: 14536120` (≈13.9 MiB); keras source uses `cache_subdir="models"` → `~keras/models`, outside the repo. |
| Spine ↔ project consistency | `requirements.txt` pins match the Stack table verbatim (`tensorflow>=2.21,<2.22`, `numpy>=1.24`, `pillow>=10.0`, `pytest>=8.0`). PRD NFR-A5 matches the spine (3.13 / stable 2.21.x / cp314 note). `config.py` matches spine invariants: threshold `0.45`, six extensions, `MODEL_BACKENDS`, collision cap `1000`, defaults `data/inbox` → `data/organized`. Tree sketch items (`pytest.ini`, `conftest.py`, `docs/`, `requirements.txt`) all exist; `models/` correctly deferred/git-ignored. System Python 3.14.6 untouched — true. |

## Out of scope / not verifiable here

- **Runtime compat of numpy 2.5.x / Pillow 12 / pytest 9 with TF 2.21** — requires an actual install (TF not installed on this host; deliberately not installed for this review).
- **Windows TF wheel behavior (CPU-only)** — no GPU claim is made in the spine, so nothing to falsify.
- **RELEASE.md on `master` showing "Release 2.23.0/2.22.0" headings** — inspected: they are unreleased template entries (`<INSERT …>` placeholders), *not* evidence of newer stable releases; PyPI remains authoritative.
