# 08 — Technical Debt and Improvements

Severity:

- **P0** — breaks a user-visible path or produces incorrect output.
- **P1** — significant correctness, trust, or maintainability risk.
- **P2** — quality, polish, or scalability issue.

Each item includes evidence, impact, and a concrete fix. Line numbers refer to the current source.

## 1. P0 defects

### 1.1 `SourceType` is not imported in `workflow/nodes.py`

- Evidence: `workflow/nodes.py:42` uses `SourceType.MANUAL`; the import block at `:23-27` imports
  `Category`, `NormalizedInput`, `RawInput` only.
- Impact: the fallback branch in `normalize_node` raises `NameError` when `raw_input` is missing or
  empty. This is the crash path, not the happy path, but it is a real defect.
- Fix: add `SourceType` to the import and add a unit test that calls `normalize_node({})`.

### 1.2 OCR fallback uses undefined `fitz`

- Evidence: `integrations/file_parser/ocr.py:6` imports `pymupdf`; `:24` uses `fitz.Matrix`.
- Impact: `NameError` is caught by the broad `except`, so OCR silently returns `("", False)`. Scanned
  PDFs therefore yield no text and the failure looks like "OCR not available".
- Fix: use `pymupdf.Matrix(zoom, zoom)` (or import `fitz`). Add a test with a rendered PDF page.

### 1.3 Persisted student/document preferences are never injected into the workflow

- Evidence:
  - `app/preferences.py:22-57` defines `StudentProfile` and `DocumentDefaults`.
  - `app/ui/main_window.py:209` loads preferences only for the sidebar label.
  - `app/ui/main_window.py:215-221` passes `raw_input` and `category` to the worker; no preferences.
  - `ai/generator.py:146-148` reads `normalized.metadata["student_profile"]` and
    `["document_preferences"]`, but nothing writes them.
- Impact: the front page always shows `"Student"`, the hardcoded institution/department, the default
  document type, and default TOC behavior. The Settings/Profile values the user saves have no effect
  on generated documents.
- Fix: in `WorkflowWorker.configure_new_run` or `normalize_node`, merge
  `load_preferences().student.model_dump()` and `.document.model_dump()` into
  `raw_input.metadata`. Add an integration test that asserts the generated `FrontPage` contains the
  saved name/roll number.
- Note: this is the single highest-impact product defect because it invalidates a visible feature.

### 1.4 PDF engine setting is ignored

- Evidence: `app/settings.py:29-31` defines `pdf_engine` and `pdf_fallback_engine`;
  `app/ui/pages/settings_page.py:61-66,118-124` edits them;
  `document/pdf_exporter.py:45-52` hardcodes Tectonic → XeLaTeX → LibreOffice.
- Impact: the user's engine choice has no effect. A machine without Tectonic still attempts it first.
- Fix: branch on `settings.pdf_engine` and `settings.pdf_fallback_engine`, with a normalized mapping
  (`system xelatex` → `xelatex`). Record the engine actually used.

### 1.5 Fabricated default references

- Evidence: `ai/generator.py:124-139` inserts two invented citations whenever none are supplied.
- Impact: the generated report contains fake academic sources. This is an academic-integrity and
  trust problem, not a cosmetic one. The evaluator does not check reference authenticity.
- Fix: if no real references exist, either fail the export with a clear message, or emit an explicit
  `[[MISSING: references]]` block. Never silently fabricate.

### 1.6 Evaluator fails open

- Evidence: `ai/evaluator.py:163-168` catches any exception and marks the section passed with score
  0.9.
- Impact: a provider outage, schema mismatch, or prompt bug yields a "passed" evaluation. The human
  review page then shows a false green state.
- Fix: mark the section `passed=False` with an `evaluation_error` issue, or propagate a distinct
  `semantic_passed=None` state. Add a test that simulates a provider exception.

## 2. P1 correctness and trust

### 2.1 LaTeX ignores `CategoryConfig.formatting`

- Evidence: `document/latex_generator.py:203-284` takes only `report` and `output_path`;
  `report.tex.j2` hardcodes `12pt`, Times New Roman, `1.25` stretch, and left `1.25in`.
- Impact: DOCX and PDF diverge; changing YAML formatting only affects DOCX.
- Fix: pass `CategoryConfig` into `LatexGenerator.render`, expose formatting variables to Jinja, and
  replace the hardcoded values.

### 2.2 Hardcoded institution on the PDF title page

- Evidence: `report.tex.j2:122-127` emits literal `Institute of Engineering` instead of
  `front_page.institution`.
- Impact: the PDF title page is wrong for any other institution, and disagrees with the DOCX, which
  uses `front_page.institution`.
- Fix: render `\VAR{front_page.institution}`.

### 2.3 `user_provided_data` never reaches generation

- Evidence: `workflow/nodes.py:95-115` stores the answer in `state["user_provided_data"]`;
  `ai/generator.py:62-78` does not include it in the prompt variables.
- Impact: the student answers the missing-info dialog, but the model never sees the answer.
- Fix: pass `user_provided_data` into `generate_section` and add a prompt variable such as
  `provided_data`. Add a test that asserts it appears in the rendered prompt.

### 2.4 `EDIT` decision skips re-evaluation

- Evidence: `workflow/routing.py:25-35` routes `DecisionType.EDIT` directly to `export`.
- Impact: edited sections are exported without deterministic or semantic checks. A user can remove a
  required section or introduce banned phrases.
- Fix: route `EDIT` back to `evaluate_output` (or a lightweight deterministic-only check), then to
  export when it passes. Guard against infinite loops.

### 2.5 Hardcoded evaluation score

- Evidence: `ai/evaluator.py:182` sets `overall_score=0.92` or `0.55`.
- Impact: the score is not a measurement; it cannot be used for ranking, dashboards, or quality
  gates.
- Fix: aggregate rubric-weighted section scores; keep deterministic findings separate.

### 2.6 Deterministic checks are incomplete

- Evidence: `ai/evaluator.py:36-122` checks required sections, per-section word limits, banned
  phrases, and citation presence. It does not check total word count, `references.min_count`,
  missing placeholders, figure presence, or table integrity.
- Impact: a report can pass while violating its own YAML contract.
- Fix: implement the missing checks and make each finding carry a machine-readable code.

### 2.7 Retry feedback is not specific

- Evidence: `workflow/nodes.py:185` builds a generic feedback string from failed section names.
- Impact: regeneration tends to repeat the same failure.
- Fix: pass the failed rubric criteria, deterministic finding codes, and evaluator suggestions into
  the regeneration prompt.

### 2.8 Evaluator prompt is not injection-wrapped

- Evidence: `ai/evaluator.py:145-152` renders `body_markdown` directly; the generator uses
  `wrap_untrusted_data` (`ai/generator.py:66`).
- Impact: a malicious assignment can inject instructions into the evaluator.
- Fix: wrap the section body and use the same untrusted-data boundary.

### 2.9 Output versioning always writes `v1`

- Evidence: `workflow/nodes.py:235-244` passes version 1.
- Impact: reruns silently overwrite prior artifacts; history rows point at the same files.
- Fix: compute `max(version)+1` from `DocumentRepository.list_by_assignment` or the filesystem.

### 2.10 Preferences UI is not implemented

- Evidence: `app/ui/pages/settings_page.py` edits only API key, model, and PDF engine;
  `reload_preferences` is a no-op (`:93-95`).
- Impact: there is no UI to set the student profile or document defaults, so even after 1.3 is fixed
  the user cannot edit the values in-app.
- Fix: add a profile form (name, roll, group, program, department, semester, section) and a document
  defaults form (document type, institution, university, campus, department, TOC, citation style,
  format notes), persist via `save_preferences`.

### 2.11 Blocking Google calls on the UI thread

- Evidence: `app/ui/pages/input_page.py` calls `list_courses`/`list_coursework`/`search_messages`
  directly in button handlers.
- Impact: the window freezes during network calls; a slow or failed request looks like a hang.
- Fix: move these calls to `QThread`/`QRunnable` workers, as already done for the workflow.

### 2.12 Cancel button is not connected

- Evidence: `app/ui/pages/processing_page.py` exposes `cancel_requested`; `main_window.py` does not
  connect it to the worker.
- Impact: the cancel button does nothing.
- Fix: connect it to a cooperative cancellation flag checked by the worker between nodes, or disable
  the button and label it honestly.

## 3. P1 architecture and data

### 3.1 Unused tables and repositories

- Evidence: `source_records` and `workflow_runs` tables exist; `WorkflowRunRepository` and
  `models/workflow.py` are not used by nodes.
- Impact: dead schema increases migration burden and misleads readers.
- Fix: either write them from the workflow (recommended for auditability) or remove them.

### 3.2 No deduplication by content hash

- Evidence: `AssignmentRepository.get_by_hash` exists but is never called.
- Impact: re-importing the same Classroom assignment creates duplicate rows and duplicate runs.
- Fix: call `get_by_hash` before `create`, or add a unique index on `content_hash`.

### 3.3 Partial persistence

- Evidence: `workflow/nodes.py:250-290` (`persist_node`) commits assignment, document, and audit
  separately.
- Impact: a mid-way failure leaves inconsistent history.
- Fix: use one session/transaction across the three writes, or an explicit compensation step.

### 3.4 Migrations are a placeholder

- Evidence: `database/migrations.py` only bumps `schema_versions`.
- Impact: any schema change will break existing databases.
- Fix: adopt Alembic or implement ordered DDL migrations keyed by version.

### 3.5 Version and path coupling

- Evidence: output path is built from `assignment_id` and `version` in `nodes.py`; the PDF exporter
  derives paths from the DOCX parent.
- Impact: moving or renaming artifacts breaks metadata and history.
- Fix: store relative paths in the DB and resolve against `settings.storage_dir`.

### 3.6 Dual Markdown parsers

- Evidence: `document/markdown_to_docx.py` and `document/latex_generator.py:75-189` implement
  separate Markdown subsets.
- Impact: the same body renders differently in DOCX and PDF (e.g. LaTeX headings are unnumbered,
  DOCX headings are numbered; math handling differs).
- Fix: parse once into an intermediate block model, then render to DOCX and LaTeX from that model.

### 3.7 Figures and appendix are modeled but not rendered

- Evidence: `models/report.py:48-58` (`FigureData`) and `:79` (`appendix`); neither exporter uses
  them.
- Impact: the data contract promises capability the product does not deliver.
- Fix: render figures (`\includegraphics`, DOCX `add_picture`) and appendices, or remove the fields.

### 3.8 Dead template hooks

- Evidence: `DocxGenerator` accepts `template_path` but never uses it
  (`document/docx_generator.py:33-44`); `document/templates/academic_base.docx` and
  `references.bib.j2` are unused.
- Impact: misleading extension points; a maintainer may edit them expecting an effect.
- Fix: wire them or delete them. If BibTeX is not planned, remove `references.bib.j2`.

## 4. P1 AI engineering

### 4.1 Model configuration drift

- Evidence: defaults in `app/settings.py:17-34` are `gemini-2.5-*`; `.env.example` and the Settings
  combo box use `gemini-3.6-flash`/`gemini-3.5-flash`/`gemini-3.1-pro-preview`; the Gemini provider
  fallback list hardcodes `gemini-2.5-flash` and `gemini-2.5-flash-lite`
  (`ai/llm/gemini.py:59,96`).
- Impact: the selected model may not exist or may silently fall back; behavior differs by install.
- Fix: one source of truth (settings), validate model names, derive the fallback list from settings,
  and make the UI list configurable.

### 4.2 `GEMINI_PRO_MODEL` is unused

- Evidence: declared in `app/settings.py:20`; no references elsewhere.
- Impact: dead configuration suggests a capability that is not implemented.
- Fix: use it for evaluation (a reasonable split: flash-lite for drafting, pro for evaluation) or
  remove it.

### 4.3 No token/cost accounting

- Evidence: no usage capture in `ai/llm/gemini.py`.
- Impact: cannot estimate cost, detect runaway retries, or optimize prompts.
- Fix: read `response.usage_metadata`, accumulate per run, and store in `metadata.json` and the DB.

### 4.4 No prompt/version trace

- Evidence: prompts are read from files at call time; no hash or version is stored with the report.
- Impact: a report cannot be reproduced or audited against the prompt that produced it.
- Fix: store SHA-256 of each prompt file and the model name in report metadata.

### 4.5 RAG is effectively non-functional

- Evidence: `rag.enabled: false` in all configs; `scripts/index_reference.py` uses `MockProvider`
  whose `embed` is SHA-256 pseudo-vectors (`ai/llm/mock.py:110-119`).
- Impact: enabling RAG with the current script retrieves meaningless neighbors.
- Fix: index with `GeminiProvider` (or Chroma's default embedding), add a retrieval evaluation set,
  and enable per category only after measured quality.

### 4.6 Sequential generation and evaluation

- Evidence: `ai/generator.py:110-121` and `ai/evaluator.py:140-168` loop sequentially.
- Impact: latency grows linearly; a 10-section final lab makes ~20 calls serially.
- Fix: parallelize independent section calls with a bounded worker pool, preserving order. Evaluate
  in parallel too.

### 4.7 No output schema for full-report generation

- Evidence: each section is a separate `SectionDraft` call; there is no whole-report structured
  call.
- Impact: cross-section consistency depends on the short prior-sections summary.
- Fix: add a final consistency pass (terminology, notation, cross-references) or generate an outline
  first and pass it to every section.

### 4.8 Mock embeddings mislead tests

- Evidence: `ai/llm/mock.py:110-119`.
- Impact: RAG tests pass while measuring nothing semantic.
- Fix: use a deterministic but semantically meaningful test embedder, or label mock RAG tests as
  plumbing-only.

## 5. P1 security and privacy

### 5.1 API key written to `.env` in plaintext

- Evidence: `app/ui/pages/settings_page.py:126-139`.
- Impact: the key is stored unencrypted and may be committed if `.env` is mishandled.
- Fix: store secrets in the OS keyring (the project already depends on `keyring`), keep only
  non-secret settings in `.env`.

### 5.2 OAuth token mirrored to a file

- Evidence: `integrations/google_auth.py:60-76` writes `google_token.json` even when keyring is used.
- Impact: token exposure surface is larger than necessary.
- Fix: write the file only when keyring is unavailable, and restrict permissions.

### 5.3 Prompt-injection redaction is weak

- Evidence: `ai/security.py:9-19` matches a short phrase list.
- Impact: paraphrased injection bypasses it. The wrapper helps, but the model can still be misled.
- Fix: treat all external text as data, add output validation against the schema, and add adversarial
  tests.

### 5.4 Absolute logo path inserted into LaTeX

- Evidence: `document/latex_generator.py:271` and `report.tex.j2:115`.
- Impact: unusual paths (spaces, `#`, `%`, Unicode) can break compilation or inject TeX.
- Fix: copy the logo into the output directory with a safe name and reference the relative filename.

### 5.5 Evaluator injection surface

- See 2.8.

## 6. P2 quality and operations

### 6.1 Packaging omissions

- Evidence: `pyinstaller.spec:7-12` includes YAML, prompts, LaTeX templates, and `styles.qss` but not
  `document/assets/tu_logo.png` or `document/templates/academic_base.docx`.
- Impact: a frozen build cannot render the logo; the unused DOCX template is irrelevant but the logo
  is user-visible.
- Fix: add the assets directory to `datas`; remove `chromadb` from unconditional `hiddenimports` if
  RAG is optional.

### 6.2 README is stale

- Evidence: `README.md` says "Early development... desktop UI and generation workflow are next",
  while both exist.
- Impact: new contributors and users get the wrong impression.
- Fix: update status, features, and the quick-start to reflect the current app.

### 6.3 Test coverage gaps

- Evidence: 30 test functions; no real Gemini test, no PDF compilation failure test, no
  preference-injection test, no evaluator fail-open test, no routing test for `EDIT`.
- Impact: the highest-risk paths are untested.
- Fix: add the tests listed in `docs/09`.

### 6.4 Logging is inconsistent

- Evidence: some modules log with context, others swallow exceptions (`except Exception: pass` in
  UI refresh paths).
- Impact: failures are invisible in support scenarios.
- Fix: log at `warning` with exception info in UI refresh paths; keep user-facing messages separate.

### 6.5 Dead dependency

- Evidence: `tenacity` is declared (`pyproject.toml:21`) and listed in `pyinstaller.spec:22` but not
  used.
- Impact: unnecessary dependency and packaging weight.
- Fix: use it for provider retries with backoff, or remove it.

### 6.6 `markdown` dependency is unused for LaTeX

- Evidence: `markdown` is declared; LaTeX uses a custom parser.
- Impact: minor weight/confusion.
- Fix: either use it or remove it.

### 6.7 No CI configuration

- Evidence: no `.github/workflows` or equivalent.
- Impact: lint/type/test checks depend on the developer remembering.
- Fix: add a CI job for `ruff`, `mypy`, and `pytest` (with a mock-provider integration test).

### 6.8 No performance budget

- Evidence: no timing instrumentation.
- Impact: regressions in generation latency are invisible.
- Fix: record per-node durations in `metadata.json`.

## 7. Top 10 fixes, in order

| # | Fix | Severity | Effort | Why first |
|---|---|---|---|---|
| 1 | Inject student/document preferences into workflow metadata | P0 | S | Restores a promised, visible feature |
| 2 | Remove fabricated default references | P0 | S | Academic integrity |
| 3 | Fix `SourceType` import and OCR `fitz` bug | P0 | XS | Two real crashes/silent failures |
| 4 | Make PDF engine honor settings and record actual engine | P0 | S | Settings currently lie |
| 5 | Make evaluator fail closed / explicit | P0 | S | Prevents false approvals |
| 6 | Pass `user_provided_data` and specific feedback into regeneration | P1 | S | Makes the human loop effective |
| 7 | Pass `CategoryConfig` into LaTeX and remove hardcoded formatting | P1 | M | DOCX/PDF consistency |
| 8 | Re-evaluate after `EDIT` | P1 | S | Prevents unvalidated exports |
| 9 | Implement missing deterministic checks and rubric-weighted score | P1 | M | Makes evaluation meaningful |
| 10 | Implement the preferences UI and move Google calls off the UI thread | P1 | M | Usability and responsiveness |

## 8. Quick wins (under an hour each)

- Add `SourceType` import.
- Replace `fitz.Matrix` with `pymupdf.Matrix`.
- Add `document/assets` to `pyinstaller.spec`.
- Update README status.
- Remove or wire `tenacity`.
- Delete the empty `references.bib.j2` if BibTeX is not planned.
- Add the missing asset path to packaging tests.
- Log the actual PDF engine in `metadata.json`.
- Add `include_toc` to the DOCX front matter consistently.
- Add a test asserting `load_preferences` values reach `FrontPage`.

## 9. What is intentionally out of scope

The following are not defects; they are unimplemented scope:

- automatic Classroom submission;
- multi-user/server deployment;
- real-time collaboration;
- a web UI;
- a database server.

Do not treat their absence as bugs, but do not claim they exist either.
