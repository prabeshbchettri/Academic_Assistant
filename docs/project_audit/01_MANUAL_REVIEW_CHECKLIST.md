# 01 — Manual Review Checklist

> Prioritized, checkbox-based review order. Tick items as you inspect them. Nothing here was executed or modified.
> Review phases are adapted to this repository's actual structure (a local-first PySide6 desktop app with a LangGraph workflow, YAML category configs, file-based prompts, and a LaTeX/DOCX export pipeline).

## Phase 1 — Project understanding (read first, change nothing)

Read in this order so you understand intent before touching rules or code.

- [ ] `plan.md` — the authoritative design: 11-step workflow, phases, risks, prompt conventions.
- [ ] `README.md` — public overview (note: stale; says Gemini / "UI is next").
- [ ] `TECH_STACK.md` — audited technology inventory and "unused/misleading items".
- [ ] `CODE_UNDERSTANDING.md` — full structural map; use as a table of contents for the code.
- [ ] `docs/01_PROJECT_OVERVIEW.md` — feature inventory and production-readiness caveats.
- [ ] `docs/02_PROJECT_STRUCTURE.md` — directory responsibilities.
- [ ] `docs/03_SYSTEM_ARCHITECTURE.md` — six-layer architecture, concurrency, error handling.
- [ ] `docs/04_DATA_FLOW.md` — end-to-end data flow.
- [ ] `docs/05_AI_ENGINEERING_ARCHITECTURE.md` — AI engineering design.
- [ ] `docs/06_DOCUMENT_GENERATION.md` — export pipeline.
- [ ] `docs/07_DATABASE_AND_API.md` — persistence + Google APIs.
- [ ] `docs/08_TECHNICAL_DEBT_AND_IMPROVEMENTS.md` — prioritized debt (partly pre-NVIDIA).
- [ ] `docs/09_LEARNING_AND_IMPLEMENTATION_ROADMAP.md` — roadmap.
- [ ] `docs/10_NVIDIA_NIM_MIGRATION_PLAN.md` — current provider direction.
- [ ] `docs/STUDENT_GUIDE.md` — real user workflow.

**Why first:** these define what the product is supposed to do. Any later change must be measured against them.

## Phase 2 — Project rules and output definition (highest leverage)

These files decide *what* is generated and *how it looks*. Changing them changes output without touching logic.

### 2A. AI prompts and instructions

- [ ] `ai/prompts/assignment_system.txt`
- [ ] `ai/prompts/assignment_generation.txt`
- [ ] `ai/prompts/assignment_evaluation.txt`
- [ ] `ai/prompts/initial_lab_system.txt`
- [ ] `ai/prompts/initial_lab_generation.txt`
- [ ] `ai/prompts/initial_lab_evaluation.txt`
- [ ] `ai/prompts/final_lab_system.txt`
- [ ] `ai/prompts/final_lab_generation.txt`
- [ ] `ai/prompts/final_lab_evaluation.txt`
- [ ] `ai/classifier.py` — embedded classification system prompt (lines ~94–100)
- [ ] `names.java` and `names1.java` — duplicate, misnamed prompt files (decide keep/remove later; do not delete during review)

### 2B. Category rules and formatting

- [ ] `configs/schema.py` — schema and loader that every category config must satisfy.
- [ ] `configs/assignment.yaml` — sections, word limits, formatting, prompt paths, rubric.
- [ ] `configs/initial_lab.yaml`
- [ ] `configs/final_lab.yaml`

### 2C. LaTeX and document formatting

- [ ] `document/templates/latex/report.tex.j2` — primary report layout.
- [ ] `document/templates/latex/references.bib.j2` — empty/unused.
- [ ] `document/templates/academic_base.docx` — empty/unused.
- [ ] `document/latex_generator.py` — template binding + Markdown→LaTeX.
- [ ] `document/latex_escape.py` — escaping/sanitization.
- [ ] `document/docx_generator.py` — DOCX layout.
- [ ] `document/markdown_to_docx.py` — DOCX Markdown subset.
- [ ] `document/pdf_exporter.py` — PDF engine fallback chain.
- [ ] `document/assets/tu_logo.png` — front-page logo asset.

**Why second:** these are the contract for AI output and academic formatting. Review them before judging implementation choices.

## Phase 3 — Core implementation

- [ ] `app/main.py` — entry point (CLI vs GUI).
- [ ] `workflow/graph.py` — the 11-node state machine.
- [ ] `workflow/nodes.py` — every node's behavior.
- [ ] `workflow/routing.py` — retry/human-review routing.
- [ ] `workflow/state.py` — state contract.
- [ ] `workflow/checkpointer.py` — SQLite durability.
- [ ] `ai/generator.py` — section generation.
- [ ] `ai/evaluator.py` — deterministic + semantic evaluation.
- [ ] `ai/classifier.py` — category selection.
- [ ] `ai/calculations.py` — safe arithmetic.
- [ ] `ai/security.py` — injection defenses.
- [ ] `ai/retriever.py` — RAG plumbing.
- [ ] `ai/llm/base.py` — provider interface.
- [ ] `ai/llm/factory.py` — provider selection.
- [ ] `ai/llm/nvidia.py` — production provider.
- [ ] `ai/llm/mock.py` — offline/test provider.
- [ ] `ai/llm/gemini.py` — legacy provider (verify whether still intended).
- [ ] `models/report.py`, `models/evaluation.py`, `models/assignment.py`, `models/workflow.py` — domain contracts.
- [ ] `database/db.py`, `database/migrations.py`, `database/models.py`, `database/repositories.py`.
- [ ] `integrations/normalizer.py`, `integrations/google_auth.py`.
- [ ] `integrations/classroom/client.py`, `integrations/gmail/client.py`.
- [ ] `integrations/file_parser/__init__.py`, `base.py`, `docx.py`, `pdf.py`, `ocr.py`, `text.py`.
- [ ] `app/settings.py`, `app/preferences.py`, `app/logging_config.py`.
- [ ] `app/ui/workers.py`, `app/ui/main_window.py`.
- [ ] `app/ui/pages/*.py` (home, input, processing, review, history, settings).
- [ ] `app/ui/widgets/*.py` (course_card, preview, progress_log, section_editor).
- [ ] `app/ui/styles.qss`.

**Why third:** once rules are understood, review how they are executed and where the real risks live.

## Phase 4 — Configuration and dependencies

- [ ] `pyproject.toml` — dependencies and tool config.
- [ ] `.env.example` — documented environment variables (NVIDIA is current; Gemini is legacy).
- [ ] `.env` — **existence only**; do not expose secrets.
- [ ] `credentials.json` — **existence only**; do not expose secrets.
- [ ] `app/settings.py` — verify defaults match `.env.example`.
- [ ] `pyinstaller.spec` — bundled data files (check logo/assets inclusion).
- [ ] `.gitignore` — confirm secrets/storage are ignored.
- [ ] `.python-version` — Python 3.12 pin.
- [ ] `uv.lock` — dependency lock (spot-check only).
- [ ] `scripts/run.bat`, `scripts/run.sh`, `scripts/build.py`, `scripts/index_reference.py`, `scripts/test_classroom.py`.

**Why fourth:** dependencies and environment define what can run and what is bundled; verify after understanding behavior.

## Phase 5 — Testing and validation

- [ ] `tests/test_imports.py`, `tests/test_settings.py`, `tests/test_classroom_client.py`.
- [ ] `tests/integration/test_workflow.py`, `tests/integration/test_docx_pdf_export.py`.
- [ ] `tests/ui/test_ui_smoke.py`, `tests/ui/test_review_page_status.py`.
- [ ] `tests/unit/test_configs.py`, `test_models.py`, `test_calculations.py`, `test_security.py`.
- [ ] `tests/unit/test_evaluator_fail_safe.py`, `test_generator_user_data.py`, `test_reference_integrity.py`, `test_workflow_nodes.py`.
- [ ] `tests/unit/test_latex.py`, `test_nvidia_provider.py`, `test_ocr_pdf.py`, `test_parsers.py`, `test_gmail.py`, `test_preferences.py`, `test_rag.py`, `test_database.py`.
- [ ] `tests/fixtures/.gitkeep`, `tests/integration/.gitkeep`, `tests/ui/.gitkeep`, `tests/unit/.gitkeep` — confirm fixtures are genuinely empty.

**Why last:** tests tell you what is already protected; read them after you know the intended behavior so you can spot untested risk areas.

## Phase 6 — Generated graph and audit artifacts (reference)

- [ ] `docs/project_audit/06_GRAPHIFY_PROJECT_KNOWLEDGE_GRAPH.md`
- [ ] `docs/project_audit/graphify/GRAPH_REPORT.md`
- [ ] `docs/project_audit/graphify/graph.json` (raw graph; large)
- [ ] `docs/project_audit/graphify/graph.html` (open in a browser)
- [ ] `graphify-out/` (canonical generated graph; original location)

## Suggested order for a first pass (if time-boxed)

1. `plan.md`
2. `configs/schema.py` + the three `configs/*.yaml`
3. The nine `ai/prompts/*.txt`
4. `ai/generator.py` + `ai/evaluator.py`
5. `document/templates/latex/report.tex.j2` + `document/latex_generator.py`
6. `workflow/graph.py` + `workflow/nodes.py`
7. `app/settings.py` + `ai/llm/factory.py` + `ai/llm/nvidia.py`
8. `app/main.py` + `app/ui/workers.py`
9. `models/report.py` + `models/evaluation.py`
10. `pyproject.toml` + `.env.example`
