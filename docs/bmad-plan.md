# BMAD Plan — `meme-classifier/`

**Method:** BMAD (Breakthrough Method for Agile AI-Driven Development)
**Project scope:** `meme-classifier/` (Image Detection — Project A)
**Sibling project:** `spam-detector/` carries its own copy of this plan, scoped to Project B
**Conventions:** kebab-case for all folders · snake_case for all Python files (PEP 8) · append-only `PROMPTS_LOG.md` at root

---

## 1. Agent Personas

| Persona | Responsibility | Primary Outputs |
|---|---|---|
| **PM Agent** | Define specs, user stories, acceptance criteria, scope control | `docs/product-requirements.md` |
| **Architect Agent** | System design, module boundaries, model/tech decisions, risk register | `docs/system-architecture.md` |
| **Dev Agent** | Clean, modular, typed implementation; unit tests | Source modules + `tests/` |
| **QA Agent** | Adversarial code review, edge-case attacks, defense prep | Test hardening, review notes, Q&A defense sheet |

The Tech Lead (human-directed) orchestrates phase transitions and owns `PROMPTS_LOG.md` hygiene.

---

## 2. Phases & Status Board — Project A

| # | Phase | Persona | Deliverable | Status |
|---|---|---|---|---|
| 0 | Kickoff & scaffolding | Tech Lead | Project tree, `PROMPTS_LOG.md`, README stubs | **Done** (INIT-001) |
| 0b | BMAD runtime install | Tech Lead | One `bmad-method` instance per project folder: `_bmad/` + 72 skills → `.agents/skills` + 72 commands → `.opencode/commands`; modules `bmm, bmad-loop, bmb, cis, tea, wds` (`gds`/game-dev **excluded**) | **Done** (INIT-002) |
| 0c | Docs relocated into project | Tech Lead | PRD, architecture, and this plan moved from parent `docs/` into `meme-classifier/docs/` so this instance's agents can scan them | **Done** (INIT-003) |
| 1 | Requirements | PM Agent | PRD + acceptance criteria | **Done** (INIT-001 output) |
| 2 | System design | Architect Agent | Architecture doc + module contracts | **Done** (INIT-001 output) |
| 4 | Implementation — meme-classifier | Dev Agent | MobileNetV2 + custom CNN organizer (+ `--train` lifecycle) | Done (Stories 4.1/4.2; 4.3 closes docs + demo verification) |
| 5 | Adversarial review | QA Agent | Edge-case tests, review fixes, security pass | Pending |
| 6 | Defense prep | QA Agent | Demo script, professor Q&A sheet | In progress (Story 4.3: demo paths verified, OQ-1/OQ-2 recorded) |

> Phase **3** (Implementation — spam-detector) belongs to the sibling project and is tracked in
> `spam-detector/docs/bmad-plan.md`.

**Phase transition rule:** a phase is Done only when (a) its artifacts exist, (b) all prompts are logged, (c) Tech Lead signs off.

---

## 3. Definition of Done (per phase)

1. **PM:** every lab-reference requirement traced to an FR ID; acceptance criteria testable.
2. **Architect:** every module has a single responsibility; no circular imports; data flow documented.
3. **Dev:** `python -m compileall` clean; `pytest` green; no `print` debugging; type hints on public APIs; docstrings on public functions.
4. **QA:** adversarial cases covered (empty input, corrupt file, path traversal, colliding filenames); review comments resolved or documented.

---

## 4. Prompt Logging Protocol

- Every user → AI prompt gets a unique ID `<PHASE>-<NNN>` in **root** `PROMPTS_LOG.md`.
- Prompts are logged **verbatim** with date, persona, artifacts, and status.
- Re-prompts and corrections are new entries (never overwrite old ones).
- ID prefixes: `INIT`, `PM`, `ARCH`, `DEV`, `QA`.

---

## 5. Known Risks (Project A)

| Risk | Impact | Mitigation |
|---|---|---|
| No labeled meme dataset provided | Custom CNN cannot train out of the box | MobileNetV2 ImageNet backend with label→category mapping as zero-shot default; CNN trains on user-labeled folders |
| TensorFlow not installed in lab env | meme-classifier backends unavailable | Organizer/CLI logic is pure stdlib and fully testable without TF |
| Folder naming conflict (spec said `meme_classifier`) | Non-compliance either way | kebab-case folders enforced per explicit convention; inner Python modules snake_case (PEP 8 / import validity) |
| `project_knowledge` only scans `<project>/docs` | Parent-level docs invisible to this instance's agents | All project docs now live in this folder (INIT-003) |
