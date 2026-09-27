---
title: 'Story 1.1: Provision the uv environment'
type: 'chore'
created: '2026-09-27'
status: 'ready-for-dev'
route: 'dispatch'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The repo has no `pyproject.toml`, no `.python-version`, and no lockfile, so nothing pins the PRD-mandated Python 3.13 + TensorFlow 2.21.x stack; today `uv run` resolves 3.12.13 and the committed `requirements.txt` is the only (unlocked) dependency record.

**Approach:** Declare the project uv-native on Python 3.13 with a committed lockfile, keeping the TF-free test path green and the documented setup reproducible from a fresh clone.

## Boundaries & Constraints

**Always:** Work on a conventional story branch (`story/1-1-...`) with small atomic conventional commits; append every AI prompt verbatim to the append-only log at `<workspace-root>/PROMPTS_LOG.md`; keep `organizer.py`, `cli.py`, `config.py` stdlib-only with no new ML imports; leave the flat root layout and `main → cli → {classifier, organizer} → config` direction untouched.

**Never:** Hand-edit the managed `AGENTS.md` block (owned by project-context refresh — log staleness instead); rewrite the CLI surface or README usage examples (Story 1.3 owns those); add new runtime code paths or test fixtures; commit `.venv/`, caches, or downloaded interpreters.

**Decided:** `requirements.txt` is deleted — uv is the single canonical pin source; the README `pip install` line goes with it.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh-clone sync | Clean clone, `uv sync` | Project-local `.venv` on Python 3.13.x, locked deps, system interpreter untouched | N/A |
| TF-absent test run | Synced env, TF not installed, `uv run --with pytest pytest -q` | All 17 tests pass | N/A |
| Offline machine | No network, `uv sync` | No partial state committed; uv reports the failure | Human retries online; repo files unchanged |

</frozen-after-approval>

## Code Map

- `requirements.txt:4-9` -- current pins (`tensorflow>=2.21,<2.22`, `numpy>=1.26`, `pillow>=10.0`, `pytest>=8.0`); reuse exact bounds in `pyproject.toml`
- `README.md:24,31` -- setup section (`pip install -r requirements.txt`); minimal setup-only update, usage examples stay for 1.3
- `pytest.ini`, `conftest.py`, `tests/` -- existing TF-free suite (17 tests); reuse as-is, do not restructure
- `.gitignore` -- already ignores `.venv/`, `__pycache__/`, `.pytest_cache/`; verify, don't extend for this story
- Absent (to create): `pyproject.toml`, `.python-version`, `uv.lock`; no `.venv` exists yet

## Tasks & Acceptance

**Execution:**
- [ ] `pyproject.toml` -- create with `requires-python = ">=3.13,<3.14"` and the four pinned dependencies -- declares the NFR-A5 stack
- [ ] `.python-version` -- create pinning `3.13` -- uv resolves the interpreter project-locally
- [ ] `uv.lock` -- generate via `uv lock` and commit -- re-syncs resolve identically
- [ ] `requirements.txt` -- delete (uv is canonical; README pip line goes with it) -- single source of truth, no dual pin maintenance
- [ ] `README.md` -- update setup section to `uv sync` / `uv run` commands only -- fresh-clone story works verbatim

**Acceptance Criteria:**
- Given a fresh clone, when `uv sync` runs, then a project-local `.venv` on Python 3.13.x is created without touching the system interpreter
- Given the synced env with TensorFlow absent, when `uv run --with pytest pytest -q` runs, then all 17 tests pass
- Given the repo, when inspected, then `pyproject.toml` declares the 3.13 bound plus the four deps and `uv.lock` exists and is committed
- Given two consecutive `uv sync` runs, when compared, then dependency resolution is identical (lockfile-effective)

## Implementation Notes

## Spec Change Log

## Review Triage Log

## Design Notes

TF Windows-wheel risk (non-blocking for approval, binding for implementation): TensorFlow ≥2.11 historically ships no native Windows wheel. If `uv lock` cannot resolve `tensorflow>=2.21,<2.22` on this platform, do NOT silently drop or relax the pin — record the full resolver output in Implementation Notes and stop for a human decision (candidates: WSL2 note, platform-constrained dependency, optional extra). `uv sync` green on this machine is non-negotiable; the pin value itself is PRD-owned.

## Verification

**Commands:**
- `uv sync` -- expected: creates `.venv`, reports Python 3.13.x, exit 0
- `uv run python --version` -- expected: `3.13.x`
- `uv run --with pytest pytest -q` -- expected: `17 passed`
- `git status --short` -- expected: only `pyproject.toml`, `.python-version`, `uv.lock`, `README.md` modified/added plus `requirements.txt` deleted
