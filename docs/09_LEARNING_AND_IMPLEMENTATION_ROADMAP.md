# 09 — Learning and Implementation Roadmap

This document is for a developer who has to understand, run, and safely improve the project. It
assumes Python 3.12 and basic familiarity with Qt, Pydantic, and LLM APIs.

## 1. Mental model in one page

```text
UI (PySide6)
  -> RawInput + category
  -> WorkflowWorker (QThread)
  -> LangGraph graph (11 nodes, SQLite checkpointer)
       normalize -> classify -> load_config -> check_missing_info
       -> retrieve_references -> generate_content -> evaluate_output
       -> (regenerate_failed loop) -> human_review -> export -> persist
  -> artifacts: DOCX + LaTeX + PDF + metadata.json
  -> SQLite: assignments, generated_documents, audit_logs
```

Three ideas unlock the codebase:

1. **The graph is the application.** The UI only starts/resumes the graph and renders interrupts.
   Business logic lives in nodes.
2. **Pydantic models are the contracts.** `RawInput`, `NormalizedInput`, `ReportContent`,
   `EvaluationResult`, and `HumanDecision` cross every layer. Read them before reading services.
3. **There are two renderers.** DOCX and LaTeX are independent translations of `ReportContent`.
   They do not share a layout engine, so they can diverge.

## 2. Reading order

| Order | File | Why |
|---|---|---|
| 1 | `README.md`, `docs/STUDENT_GUIDE.md` | User workflow and intent |
| 2 | `models/assignment.py`, `models/report.py`, `models/evaluation.py` | Data contracts |
| 3 | `workflow/state.py` | The state that flows through the graph |
| 4 | `workflow/graph.py` | Node wiring and conditional edges |
| 5 | `workflow/nodes.py` | The actual behavior of every step |
| 6 | `workflow/routing.py` | Retry and human-decision routing |
| 7 | `configs/schema.py`, `configs/*.yaml` | Rules, limits, rubrics |
| 8 | `ai/generator.py`, `ai/evaluator.py`, `ai/classifier.py` | AI logic |
| 9 | `ai/llm/base.py`, `ai/llm/gemini.py`, `ai/llm/mock.py` | Provider abstraction |
| 10 | `document/docx_generator.py`, `document/latex_generator.py`, `document/pdf_exporter.py`, `report.tex.j2` | Output pipeline |
| 11 | `database/models.py`, `database/repositories.py`, `database/db.py` | Persistence |
| 12 | `app/main.py`, `app/ui/main_window.py`, `app/ui/workers.py` | Entry point and threading |
| 13 | `app/settings.py`, `app/preferences.py` | Configuration |
| 14 | `tests/` | Expected behavior and fixtures |

Read with the debugger or a scratch script, not only by scrolling. A 10-line script that builds a
`RawInput`, runs the graph with `MockProvider`, and prints the final state teaches more than an hour
of reading.

## 3. Core concepts you will need

### 3.1 LangGraph state and reducers

- `WorkflowState` is a `TypedDict`; nodes return partial dicts that are merged into state.
- `node_history` is appended explicitly in each node (there is no reducer annotation).
- Conditional edges read state and return the next node name.
- `interrupt()` pauses the graph and surfaces a payload to the caller.
- The SQLite checkpointer persists state per `thread_id`, which is what makes resume work.

**Exercise:** add a `notes` field to `WorkflowState`, write it in `normalize_node`, and confirm it is
present after `classify_node`. Then try a list field without a reducer and observe that a node return
replaces rather than appends.

### 3.2 Pydantic v2

- Models validate LLM structured output.
- `model_dump(mode="json")` is used to put models into state.
- `model_validate` reconstructs models from state.
- `SecretStr` wraps the API key.

**Exercise:** add a field to `SectionDraft`, update the schema usage, and see where validation fails
if the mock provider does not set it.

### 3.3 Qt threading

- `WorkflowWorker` is a `QThread` subclass; it emits signals instead of touching widgets.
- The UI must never block; the workflow is off-thread, but Google API calls in `InputPage` are not.
- Signals cross threads safely; direct widget calls do not.

**Exercise:** move the Classroom course list call into a `QThread` worker and compare UI
responsiveness with a deliberately slow fake service.

### 3.4 Jinja2 for LaTeX

- `LatexGenerator` uses custom delimiters to avoid clashing with LaTeX braces:
  `block_start_string="\\BLOCK{"`, `variable_start_string="\\VAR{"`, `comment_string="%%"`.
- The template is plain LaTeX with Jinja variables.
- Content is escaped in Python before rendering, not in the template.

**Exercise:** add a `show_abstract` flag to the template and pass it from `render`. Verify the PDF
changes without touching Python string formatting.

### 3.5 SQLModel and SQLite

- SQLModel combines Pydantic and SQLAlchemy.
- `init_db()` creates tables; `run_migrations()` is a placeholder.
- WAL mode improves concurrent read/write behavior.
- The checkpointer uses a separate SQLite file.

**Exercise:** write a repository test that creates an assignment, persists a document, and lists it.
Then inspect the DB with `sqlite3` and compare with the model.

### 3.6 LaTeX toolchain

- Tectonic downloads packages on demand; `--untrusted` restricts shell escape.
- XeLaTeX is needed for `fontspec`.
- LibreOffice is the DOCX fallback.
- TOC requires two passes.
- `fontspec` requires the named font to exist.

**Exercise:** run `PdfExporter.export` on a fixture report with Tectonic absent and confirm the
XeLaTeX path, then with both absent and confirm the LibreOffice path.

## 4. How to run and verify

```powershell
uv sync --extra dev --extra google
uv run pytest
uv run ruff check .
uv run mypy .
uv run python -m app.main
```

Offline demo (no API key):

```powershell
uv run python -m app.main --mock
```

CLI smoke run:

```powershell
uv run python -m app.main --cli "Derive the time constant of an RC circuit." --category assignment
```

The mock provider makes the full workflow runnable without network access. Use it to verify plumbing
before debugging AI behavior.

## 5. Debugging playbook

| Symptom | First place to look |
|---|---|
| UI freezes | `app/ui/pages/input_page.py` (Google calls on UI thread) |
| Workflow never resumes | `WorkflowWorker.configure_resume`, `thread_id`, checkpointer file |
| `NameError: SourceType` | `workflow/nodes.py:42` |
| Empty OCR text | `integrations/file_parser/ocr.py:24` (`fitz`) |
| Front page shows "Student" | preferences not injected (see `docs/08` 1.3) |
| PDF is DOCX-converted | Tectonic/XeLaTeX missing; check `pdf_exporter.py` logs |
| PDF formatting ignores YAML | LaTeX template hardcodes values (see `docs/06`) |
| Evaluation always passes | `ai/evaluator.py:163-168` fail-open |
| References look fake | `ai/generator.py:124-139` |
| Edit approval exports unvalidated text | `workflow/routing.py:33` |

Add temporary logging at node boundaries (`node_history`, `retry_count`, `status`) rather than
sprinkling prints through services.

## 6. Implementation roadmap

The order is dependency-driven: correctness first, then trust, then capability, then polish.

### Phase 0 — Make the happy path honest (1–2 days)

| Task | Files | Acceptance |
|---|---|---|
| Fix `SourceType` import | `workflow/nodes.py` | `normalize_node({})` returns instead of raising |
| Fix OCR `fitz` | `integrations/file_parser/ocr.py` | Scanned PDF returns text or a logged, explicit failure |
| Inject preferences into metadata | `app/ui/workers.py` or `workflow/nodes.py` | Generated `FrontPage` uses saved name/roll/institution |
| Remove fabricated references | `ai/generator.py` | No invented citations; explicit missing-reference state |
| Honor PDF engine settings | `document/pdf_exporter.py` | Selected engine is attempted first; metadata records it |
| Evaluator fails closed | `ai/evaluator.py` | Provider exception marks the section failed/unverified |

**Definition of done:** a mock run and a real run both produce a report whose front page matches the
saved profile, with no fabricated references, and a PDF compiled by the selected engine or an
explicit failure.

### Phase 1 — Make evaluation and review meaningful (2–4 days)

| Task | Files | Acceptance |
|---|---|---|
| Pass `user_provided_data` into prompts | `workflow/nodes.py`, `ai/generator.py` | Answer text appears in the rendered prompt |
| Specific retry feedback | `workflow/nodes.py`, `ai/evaluator.py` | Regeneration prompt includes failed criteria/findings |
| Re-evaluate after `EDIT` | `workflow/routing.py` | Edited report cannot export with a failed required section |
| Missing deterministic checks | `ai/evaluator.py` | Total words, `min_count`, placeholders, figures checked |
| Rubric-weighted score | `ai/evaluator.py` | Score is derived, not hardcoded |
| Evaluator injection wrapping | `ai/evaluator.py`, `ai/security.py` | Section body is wrapped like generator input |

**Definition of done:** a report that omits a required section, exceeds a word limit, or contains a
banned phrase cannot reach export without an explicit human override that is recorded.

### Phase 2 — Unify document output (3–5 days)

| Task | Files | Acceptance |
|---|---|---|
| Pass `CategoryConfig` to LaTeX | `document/latex_generator.py`, `report.tex.j2` | YAML font/size/spacing/margins affect the PDF |
| Use `front_page.institution` | `report.tex.j2` | PDF title page matches DOCX and profile |
| Single formatting model | new `document/formatting.py` | DOCX and LaTeX read the same values |
| Figure rendering | both exporters | `FigureData` appears in both outputs |
| Appendix rendering | both exporters | `ReportContent.appendix` appears in both |
| Table de-duplication | `latex_generator.py` | A Markdown table is not rendered twice |
| Wire or delete dead templates | `docx_generator.py`, templates | No unused hook remains |
| PDF smoke test | `tests/integration` | Fixture report produces a non-empty PDF |

**Definition of done:** changing one formatting value changes both DOCX and PDF consistently; a
fixture report with a figure and appendix renders in both formats.

### Phase 3 — Preferences UI and responsiveness (2–3 days)

| Task | Files | Acceptance |
|---|---|---|
| Profile form | `settings_page.py` | Name/roll/group/program/department/semester/section persist |
| Document defaults form | `settings_page.py` | Type/institution/university/campus/department/TOC/citation/notes persist |
| `reload_preferences` implementation | `settings_page.py` | Reopening Settings shows saved values |
| Off-thread Google calls | `input_page.py`, new worker | UI stays responsive during slow calls |
| Cancel wiring | `main_window.py`, `workers.py` | Cancel stops at the next node boundary or is disabled |

**Definition of done:** a student can complete their profile once, import from Classroom without the
UI freezing, and see the profile on the generated front page.

### Phase 4 — AI quality and observability (3–5 days)

| Task | Files | Acceptance |
|---|---|---|
| Token/cost accounting | `ai/llm/gemini.py`, `nodes.py` | Per-run usage stored in metadata and DB |
| Prompt versioning | `ai/generator.py`, `ai/evaluator.py` | Prompt hashes stored with the report |
| Single model config source | `settings.py`, `.env.example`, `settings_page.py`, `gemini.py` | No drift; fallback derived from settings |
| Parallel section generation | `ai/generator.py` | Bounded concurrency, order preserved |
| Real embeddings for RAG | `scripts/index_reference.py`, `ai/retriever.py` | Indexing uses a semantic provider |
| RAG evaluation set | `tests/` or `scripts/` | Retrieval quality is measured before enabling |
| Provider retry with backoff | `ai/llm/gemini.py` | Transient errors retried; permanent errors surfaced |

**Definition of done:** a run reports model, token usage, prompt hashes, and per-node durations; RAG
is either measured and enabled or explicitly disabled with a reason.

### Phase 5 — Persistence and operations (2–4 days)

| Task | Files | Acceptance |
|---|---|---|
| Content-hash deduplication | `nodes.py`, `repositories.py` | Re-import does not duplicate |
| Single-transaction persistence | `nodes.py`, `repositories.py` | No partial history on failure |
| Real migrations | `database/migrations.py` or Alembic | Schema upgrades work on an existing DB |
| Versioned outputs | `nodes.py`, `repositories.py` | Reruns create `v2`, `v3`; history matches files |
| Packaging assets | `pyinstaller.spec` | Frozen build renders the logo |
| CI | new workflow | `ruff`, `mypy`, `pytest` run on push |

**Definition of done:** repeated runs are idempotent or explicitly versioned, the frozen build matches
the dev build, and CI blocks regressions.

### Phase 6 — Product polish (ongoing)

- Update `README.md` status and screenshots.
- Add an artifact open/reveal action after export.
- Add a diff view for `EDIT` decisions.
- Add a "why did this fail?" panel driven by deterministic finding codes.
- Add export presets (assignment, initial lab, final lab, project report).
- Add a template gallery for institutions.

## 7. Testing strategy

### Unit

- Models: validation, defaults, enum behavior.
- Config: YAML validation, caching, invalid input.
- Security: sanitization, wrapping, escaping.
- Calculations: safe AST evaluation, rejected nodes.
- LaTeX: escaping, Markdown conversion, table padding.
- Preferences: round-trip, missing file, corrupt file.

### Integration

- Full graph with `MockProvider`, including missing-info interrupt and resume.
- Retry loop: force a failed evaluation and assert `retry_count` increments and the loop stops at
  `max_retries`.
- Human review: approve, edit, regenerate, reject.
- Persistence: assignment, document, audit rows.
- Export: DOCX exists; PDF exists or a clear failure is recorded.

### UI

- Smoke test each page constructs.
- Signal wiring: start generation, review decision, navigation.
- Preferences form round-trip (once implemented).

### AI regression

- Golden prompt rendering for each category with a fixed `NormalizedInput`.
- Schema conformance for mock outputs.
- Evaluator behavior on a fixed failing report.
- Adversarial injection fixtures.

### Document regression

- Text extraction from the PDF contains expected headings and the student name.
- Page count is within a sane range for a fixture.
- Table and reference text appear exactly once.

## 8. Suggested exercises

1. **Trace a run.** Add a `run_id` to state, log it in every node, and follow one mock run in the
   logs.
2. **Break the evaluator.** Make the mock provider raise; observe the fail-open behavior; fix it and
   add a test.
3. **Change formatting.** Set `font_size: 14` in `final_lab.yaml`; confirm DOCX changes and PDF does
   not; then implement the LaTeX plumbing.
4. **Add a section type.** Add `acknowledgements` to `final_lab.yaml`; update prompts; verify it is
   generated, evaluated, and rendered.
5. **Add a citation field.** Add `doi` to `Citation`; render it in both exporters; verify escaping.
6. **Make RAG real.** Index a small PDF with `GeminiProvider`, enable RAG for one category, and
   compare output with and without retrieval.
7. **Add a new category.** Create `configs/project_report.yaml`, prompts, and a classifier rule; run
   the full graph.

## 9. Anti-patterns to avoid

- Do not add business logic to Qt pages; keep it in nodes/services.
- Do not read preferences or settings inside renderers; pass explicit config.
- Do not hardcode formatting in templates; expose variables.
- Do not catch `Exception` and return success; distinguish "not evaluated" from "passed".
- Do not fabricate content to satisfy a schema; emit a visible placeholder.
- Do not add a second Markdown parser; extend the intermediate model.
- Do not enable RAG without a retrieval evaluation.
- Do not store secrets in `.env` when the keyring is available.

## 10. Definition of a healthy release

- A new student can install, authenticate, import an assignment, generate, review, edit, and export
  without reading source code.
- The front page reflects the saved profile.
- The PDF matches the configured formatting and the DOCX within reasonable tolerance.
- No fabricated references reach the export.
- Failed evaluation cannot be silently approved.
- Every run records model, prompt hashes, token usage, durations, and artifact paths.
- CI runs lint, types, unit, integration, and document smoke tests.
- The README describes the product that actually exists.
