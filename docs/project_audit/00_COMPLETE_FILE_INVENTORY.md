# 00 — Complete File Inventory

> Read-only audit. No source, prompt, template, config, dependency, or documentation file was modified.
> Generated: 2026-11-28. Project root: `C:\Users\LENOVO\Desktop\AI_PROJECTS\Academic_Assistent`.

## 1. Scope and method

- The entire repository was recursively inspected (source, docs, configs, templates, tests, scripts, build files, hidden files).
- File purposes were verified by reading the file, its imports, and its call sites where possible. Where a relationship could not be verified in code, it is labelled as **suspected** in the companion documents.
- Dependency analysis was produced with the **Graphify** skill (see `06_GRAPHIFY_PROJECT_KNOWLEDGE_GRAPH.md`). The Graphify graph is the canonical machine-derived relationship source; this inventory is the manually verified file list.
- The `.env` file and `credentials.json` were checked for **existence only**; their contents were not read or exposed.

### Excluded from the primary review list (mentioned, not audited)

| Excluded path | Why excluded | Note |
|---|---|---|
| `.venv/` | Virtual environment | Third-party dependencies |
| `.git/` | Version control metadata | Not application content |
| `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/` | Caches | Regenerable |
| `graphify-out/` | Generated knowledge-graph artifacts | Produced by Graphify; reported in doc 06 |
| `storage/` | Local runtime data (`academic_ai.db`, `workflow_checkpoints.db`, `outputs/`, `logs/`, `rag/`, `references/`, `credentials/`) | User data + generated output; gitignored |
| `.freebuff/` | Tool metadata (`project-id`) | Not application code |
| `dist/`, `build/` | Build artifacts (if present) | Regenerable |
| `uv.lock` | Generated lockfile (listed but not reviewed line-by-line) | 351 KB |

## 2. Summary counts

| Metric | Count |
|---|---|
| Files discovered and inventoried (excluding the paths above) | **143** |
| Relevant for manual review | **143** |
| CRITICAL | **29** |
| HIGH | **53** |
| MEDIUM | **40** |
| LOW | **21** |
| Standalone AI prompt files (`.txt`) | **9** |
| Duplicate/misnamed prompt files (`.java`) | **2** |
| Prompt-binding YAML configs | **3** |
| Embedded prompt in Python | **1** (`ai/classifier.py`) |
| LaTeX source/template files | **4** |
| Document-generation / formatting modules | **8** |
| Formatting configuration blocks (YAML) | **3** |
| Configuration / environment files | **17** |
| Test files | **18** (plus 5 `.gitkeep` placeholders) |
| Files represented in the Graphify graph | **128** |

## 3. Complete file inventory

Importance: **CRITICAL** = must inspect before changing the project; **HIGH** = strongly recommended for understanding dependencies; **MEDIUM** = relevant to particular features; **LOW** = supporting or rarely modified.

### 3.1 Root and project-definition files

| No. | File Path | File Type | Purpose | Importance | Manual Review Required |
|---|---|---|---|---|---|
| 1 | `README.md` | Markdown | User-facing overview and quick start. **Stale**: still says Gemini and "desktop UI is next". | HIGH | Yes |
| 2 | `plan.md` | Markdown | Full implementation plan: architecture, 11-step workflow, phases, risks, prompt conventions. Primary design source. | CRITICAL | Yes |
| 3 | `TECH_STACK.md` | Markdown | Audited technology inventory by layer, including "unused/misleading items". | HIGH | Yes |
| 4 | `CODE_UNDERSTANDING.md` | Markdown | 1,158-line structural map of every module, data flow, and defect. | HIGH | Yes |
| 5 | `pyproject.toml` | TOML | Project metadata, dependencies, optional extras (`google`, `rag`, `dev`), pytest/ruff/mypy config. | CRITICAL | Yes |
| 6 | `uv.lock` | Lockfile | Resolved dependency lock (generated). | LOW | Optional |
| 7 | `pyinstaller.spec` | Spec | PyInstaller build spec; bundled data files and hidden imports. | MEDIUM | Yes |
| 8 | `.env.example` | Env template | Documented environment variables (NVIDIA, Google, PDF, logging). | HIGH | Yes |
| 9 | `.env` | Env file | Local secrets/config. **Existence only; contents not read.** | HIGH | Yes (security) |
| 10 | `credentials.json` | Google OAuth client | OAuth desktop-client secret. **Existence only; contents not read.** | HIGH | Yes (security) |
| 11 | `.gitignore` | Git config | Ignores secrets, venv, caches, storage, build output. | MEDIUM | Yes |
| 12 | `.python-version` | Config | Pins Python 3.12. | LOW | Optional |
| 13 | `names.java` | Prompt text (misnamed) | AI-audit prompt ("ROLE: Senior AI Engineer..."). Not Java code. Duplicate of `names1.java`. | LOW | Yes |
| 14 | `names1.java` | Prompt text (misnamed) | Byte-identical duplicate of `names.java`. | LOW | Yes |

### 3.2 AI layer (`ai/`)

| No. | File Path | File Type | Purpose | Importance | Manual Review Required |
|---|---|---|---|---|---|
| 15 | `ai/__init__.py` | Python | Public AI exports: `SectionGenerator`, `Evaluator`, `Classifier`, `build_llm_provider`. | MEDIUM | Yes |
| 16 | `ai/generator.py` | Python | `SectionGenerator`: loads system/generation prompts from category config, generates sections, assembles `ReportContent`. | CRITICAL | Yes |
| 17 | `ai/evaluator.py` | Python | `Evaluator`: deterministic checks + LLM semantic evaluation; loads evaluation prompt; fail-safe to INCONCLUSIVE. | CRITICAL | Yes |
| 18 | `ai/classifier.py` | Python | Rule-based + LLM category classification; contains an **embedded** system prompt. | HIGH | Yes |
| 19 | `ai/calculations.py` | Python | Safe AST arithmetic evaluation / formula checking. | HIGH | Yes |
| 20 | `ai/retriever.py` | Python | `RagRetriever`, `chunk_text` for ChromaDB-backed retrieval. | HIGH | Yes |
| 21 | `ai/security.py` | Python | `sanitize_external_input`, `wrap_untrusted_data` (prompt-injection defense). | HIGH | Yes |
| 22 | `ai/llm/__init__.py` | Python | Provider exports (`LLMProvider`, `build_llm_provider`, providers). | MEDIUM | Yes |
| 23 | `ai/llm/base.py` | Python | `LLMProvider` abstract interface (`generate_text`, `generate_structured`, `embed`). | CRITICAL | Yes |
| 24 | `ai/llm/factory.py` | Python | `build_llm_provider`: Mock for offline/no key, else NVIDIA NIM. | CRITICAL | Yes |
| 25 | `ai/llm/nvidia.py` | Python | `NvidiaProvider`: production NVIDIA NIM provider, model fallback, embeddings, structured output. | CRITICAL | Yes |
| 26 | `ai/llm/mock.py` | Python | `MockProvider`: deterministic offline provider used by tests/CLI. | HIGH | Yes |
| 27 | `ai/llm/gemini.py` | Python | Legacy `GeminiProvider` (google-genai). Not selected by the factory. | HIGH | Yes |
| 28 | `ai/prompts/.gitkeep` | Placeholder | Keeps prompt directory tracked. | LOW | No |
| 29 | `ai/prompts/assignment_system.txt` | Prompt | System prompt for academic assignments. | CRITICAL | Yes |
| 30 | `ai/prompts/assignment_generation.txt` | Prompt | Generation template for academic assignments. | CRITICAL | Yes |
| 31 | `ai/prompts/assignment_evaluation.txt` | Prompt | Evaluation rubric template for academic assignments. | CRITICAL | Yes |
| 32 | `ai/prompts/initial_lab_system.txt` | Prompt | System prompt for initial lab reports. | CRITICAL | Yes |
| 33 | `ai/prompts/initial_lab_generation.txt` | Prompt | Generation template for initial lab reports. | CRITICAL | Yes |
| 34 | `ai/prompts/initial_lab_evaluation.txt` | Prompt | Evaluation rubric for initial lab reports. | CRITICAL | Yes |
| 35 | `ai/prompts/final_lab_system.txt` | Prompt | System prompt for final lab reports. | CRITICAL | Yes |
| 36 | `ai/prompts/final_lab_generation.txt` | Prompt | Generation template for final lab reports. | CRITICAL | Yes |
| 37 | `ai/prompts/final_lab_evaluation.txt` | Prompt | Evaluation rubric for final lab reports. | CRITICAL | Yes |

### 3.3 Application shell and UI (`app/`)

| No. | File Path | File Type | Purpose | Importance | Manual Review Required |
|---|---|---|---|---|---|
| 38 | `app/__init__.py` | Python | Package docstring. | LOW | No |
| 39 | `app/main.py` | Python | Entry point: CLI generation mode or PySide6 GUI launch. | CRITICAL | Yes |
| 40 | `app/settings.py` | Python | Pydantic settings from `.env`; NVIDIA, Google, PDF, storage paths. | CRITICAL | Yes |
| 41 | `app/preferences.py` | Python | Student profile / document defaults persisted to JSON; resolves logo path. | HIGH | Yes |
| 42 | `app/logging_config.py` | Python | Logging setup (file + console). | MEDIUM | Yes |
| 43 | `app/ui/main_window.py` | Python | Main window, sidebar navigation, page routing, worker wiring. | HIGH | Yes |
| 44 | `app/ui/pages/home_page.py` | Python | Landing page: auth card, course grid, quick actions, stats. | HIGH | Yes |
| 45 | `app/ui/pages/input_page.py` | Python | Assignment input: Classroom/Gmail/manual/file selection, course fetch. | HIGH | Yes |
| 46 | `app/ui/pages/processing_page.py` | Python | Progress page during workflow execution. | MEDIUM | Yes |
| 47 | `app/ui/pages/review_page.py` | Python | Human review/approval, evaluation status, edits, regeneration. | HIGH | Yes |
| 48 | `app/ui/pages/history_page.py` | Python | Past runs; open DOCX/PDF/folder. | MEDIUM | Yes |
| 49 | `app/ui/pages/settings_page.py` | Python | API key / model / PDF engine settings UI. | HIGH | Yes |
| 50 | `app/ui/workers.py` | Python | `QThread` workers: Classroom course fetch and workflow execution/resume. | HIGH | Yes |
| 51 | `app/ui/styles.qss` | Qt stylesheet | Application visual theme. | MEDIUM | Yes |
| 52 | `app/ui/widgets/course_card.py` | Python | Course tile widget. | LOW | Yes |
| 53 | `app/ui/widgets/preview.py` | Python | Document preview widget. | MEDIUM | Yes |
| 54 | `app/ui/widgets/progress_log.py` | Python | Progress log widget. | LOW | Yes |
| 55 | `app/ui/widgets/section_editor.py` | Python | Per-section editor with word count and regenerate. | MEDIUM | Yes |

### 3.4 Category configuration (`configs/`)

| No. | File Path | File Type | Purpose | Importance | Manual Review Required |
|---|---|---|---|---|---|
| 56 | `configs/schema.py` | Python | Pydantic schema + loader/cache for category YAML (sections, word limits, formatting, prompts, rubric, RAG). | CRITICAL | Yes |
| 57 | `configs/__init__.py` | Python | Re-exports `CategoryConfig`, `load_category_config`, `preload_all_configs`. | MEDIUM | Yes |
| 58 | `configs/assignment.yaml` | YAML | Academic assignment rules, formatting, prompt paths, rubric, reference minimums. | CRITICAL | Yes |
| 59 | `configs/initial_lab.yaml` | YAML | Initial lab report rules, formatting, prompt paths, rubric. | CRITICAL | Yes |
| 60 | `configs/final_lab.yaml` | YAML | Final lab report rules, formatting, prompt paths, rubric, RAG block. | CRITICAL | Yes |

### 3.5 Document generation (`document/`)

| No. | File Path | File Type | Purpose | Importance | Manual Review Required |
|---|---|---|---|---|---|
| 61 | `document/__init__.py` | Python | Exports `DocxGenerator`, `LatexGenerator`, `PdfExporter`. | LOW | No |
| 62 | `document/docx_generator.py` | Python | Builds DOCX from `ReportContent` + `CategoryConfig`; styles, headers/footers, TOC, front page. | CRITICAL | Yes |
| 63 | `document/latex_generator.py` | Python | Renders `ReportContent` through `report.tex.j2`; Markdown→LaTeX; escapes values. | CRITICAL | Yes |
| 64 | `document/latex_escape.py` | Python | Escapes TeX specials and sanitizes math. | HIGH | Yes |
| 65 | `document/markdown_to_docx.py` | Python | Converts a Markdown subset into DOCX paragraphs/runs. | HIGH | Yes |
| 66 | `document/pdf_exporter.py` | Python | PDF fallback chain: Tectonic → XeLaTeX → LibreOffice; writes metadata. | HIGH | Yes |
| 67 | `document/templates/latex/report.tex.j2` | Jinja2/LaTeX | **Primary academic report template** (title page, colors, sections, bibliography). | CRITICAL | Yes |
| 68 | `document/templates/latex/references.bib.j2` | Jinja2/BibTeX | **Empty (0 bytes), unused.** | LOW | Yes |
| 69 | `document/templates/academic_base.docx` | DOCX | **Empty (0 bytes), unused** base-template hook. | LOW | Yes |
| 70 | `document/assets/tu_logo.png` | Image | Tribhuvan University crest used on front page (LaTeX + preferences). | MEDIUM | Yes |

### 3.6 Database (`database/`)

| No. | File Path | File Type | Purpose | Importance | Manual Review Required |
|---|---|---|---|---|---|
| 71 | `database/__init__.py` | Python | DB package exports. | MEDIUM | Yes |
| 72 | `database/db.py` | Python | Engine/session factory, SQLite pragmas, `init_db`, DB path. | HIGH | Yes |
| 73 | `database/migrations.py` | Python | Minimal versioned DDL migrations. | HIGH | Yes |
| 74 | `database/models.py` | Python | SQLModel tables: assignments, workflow_runs, generated_documents, reference_documents, audit_logs, schema_versions, source_records. | HIGH | Yes |
| 75 | `database/repositories.py` | Python | Repository classes (`AssignmentRepository`, `DocumentRepository`, `AuditLogRepository`, ...). | HIGH | Yes |

### 3.7 Integrations (`integrations/`)

| No. | File Path | File Type | Purpose | Importance | Manual Review Required |
|---|---|---|---|---|---|
| 76 | `integrations/__init__.py` | Python | Package docstring. | LOW | No |
| 77 | `integrations/google_auth.py` | Python | Google OAuth installed-app flow; keyring token storage. | HIGH | Yes |
| 78 | `integrations/normalizer.py` | Python | `normalize_input`: clean text, compute content hash. | HIGH | Yes |
| 79 | `integrations/classroom/__init__.py` | Python | Package docstring. | LOW | No |
| 80 | `integrations/classroom/client.py` | Python | Classroom API: courses, coursework, materials, Drive download. | HIGH | Yes |
| 81 | `integrations/gmail/client.py` | Python | Gmail search + message/attachment extraction. | MEDIUM | Yes |
| 82 | `integrations/file_parser/__init__.py` | Python | Parser registry + `parse_file` (PDF/DOCX/TXT, 25 MB limit). | HIGH | Yes |
| 83 | `integrations/file_parser/base.py` | Python | `BaseFileParser`, `ParsedDocument`. | MEDIUM | Yes |
| 84 | `integrations/file_parser/docx.py` | Python | DOCX parser. | MEDIUM | Yes |
| 85 | `integrations/file_parser/pdf.py` | Python | PyMuPDF PDF parser; password/read errors. | HIGH | Yes |
| 86 | `integrations/file_parser/ocr.py` | Python | Tesseract OCR fallback for scanned PDFs. | HIGH | Yes |
| 87 | `integrations/file_parser/text.py` | Python | Plain-text parser. | MEDIUM | Yes |

### 3.8 Domain models (`models/`)

| No. | File Path | File Type | Purpose | Importance | Manual Review Required |
|---|---|---|---|---|---|
| 88 | `models/__init__.py` | Python | Domain model exports. | MEDIUM | Yes |
| 89 | `models/assignment.py` | Python | `Category`, `SourceType`, `RawInput`, `NormalizedInput`, `ClassificationResult`, `MissingInfoRequest`. | HIGH | Yes |
| 90 | `models/report.py` | Python | `ReportContent`, `SectionDraft`, `Citation`, `FrontPage`, `TableData`, `FigureData`, provenance. | CRITICAL | Yes |
| 91 | `models/evaluation.py` | Python | `EvaluationResult` (fail-safe INCONCLUSIVE default), findings, `HumanDecision`. | CRITICAL | Yes |
| 92 | `models/workflow.py` | Python | Workflow run record model. | MEDIUM | Yes |

### 3.9 Workflow orchestration (`workflow/`)

| No. | File Path | File Type | Purpose | Importance | Manual Review Required |
|---|---|---|---|---|---|
| 93 | `workflow/__init__.py` | Python | Exports `build_academic_workflow`, `WorkflowState`. | MEDIUM | Yes |
| 94 | `workflow/graph.py` | Python | Builds the 11-node LangGraph state machine and edges. | CRITICAL | Yes |
| 95 | `workflow/nodes.py` | Python | All workflow nodes: normalize, classify, load config, missing info, retrieve, generate, evaluate, regenerate, human review, export, persist. | CRITICAL | Yes |
| 96 | `workflow/routing.py` | Python | Conditional routing after evaluation and human review. | HIGH | Yes |
| 97 | `workflow/state.py` | Python | `WorkflowState` TypedDict contract. | HIGH | Yes |
| 98 | `workflow/checkpointer.py` | Python | SQLite LangGraph checkpointer. | HIGH | Yes |

### 3.10 Documentation (`docs/`)

| No. | File Path | File Type | Purpose | Importance | Manual Review Required |
|---|---|---|---|---|---|
| 99 | `docs/01_PROJECT_OVERVIEW.md` | Markdown | Feature inventory, status, production-readiness caveats. | HIGH | Yes |
| 100 | `docs/02_PROJECT_STRUCTURE.md` | Markdown | Directory-by-directory map and responsibilities. | HIGH | Yes |
| 101 | `docs/03_SYSTEM_ARCHITECTURE.md` | Markdown | Six-layer architecture, concurrency, error handling. | HIGH | Yes |
| 102 | `docs/04_DATA_FLOW.md` | Markdown | End-to-end data flow through the workflow. | HIGH | Yes |
| 103 | `docs/05_AI_ENGINEERING_ARCHITECTURE.md` | Markdown | Prompt architecture, deterministic/LLM split, provider boundary. | HIGH | Yes |
| 104 | `docs/06_DOCUMENT_GENERATION.md` | Markdown | DOCX/LaTeX/PDF pipeline, formatting divergence, defects. | HIGH | Yes |
| 105 | `docs/07_DATABASE_AND_API.md` | Markdown | Schema, repositories, Google API usage. | HIGH | Yes |
| 106 | `docs/08_TECHNICAL_DEBT_AND_IMPROVEMENTS.md` | Markdown | Prioritized technical debt (some sections predate NVIDIA migration). | HIGH | Yes |
| 107 | `docs/09_LEARNING_AND_IMPLEMENTATION_ROADMAP.md` | Markdown | Learning/implementation roadmap. | MEDIUM | Yes |
| 108 | `docs/10_NVIDIA_NIM_MIGRATION_PLAN.md` | Markdown | NVIDIA NIM migration plan and provider design. | HIGH | Yes |
| 109 | `docs/STUDENT_GUIDE.md` | Markdown | Real student workflow, scopes, troubleshooting. | MEDIUM | Yes |

### 3.11 Scripts and automation (`scripts/`)

| No. | File Path | File Type | Purpose | Importance | Manual Review Required |
|---|---|---|---|---|---|
| 110 | `scripts/__init__.py` | Python | Package marker. | LOW | No |
| 111 | `scripts/build.py` | Python | PyInstaller build wrapper. | MEDIUM | Yes |
| 112 | `scripts/index_reference.py` | Python | Index reference documents into RAG (uses `MockProvider` by default). | MEDIUM | Yes |
| 113 | `scripts/test_classroom.py` | Python | Manual Classroom read smoke test. | MEDIUM | Yes |
| 114 | `scripts/run.bat` | Batch | Windows launcher. | LOW | Yes |
| 115 | `scripts/run.sh` | Shell | POSIX launcher. | LOW | Yes |

### 3.12 Tests (`tests/`)

| No. | File Path | File Type | Purpose | Importance | Manual Review Required |
|---|---|---|---|---|---|
| 116 | `tests/__init__.py` | Python | Package marker. | LOW | No |
| 117 | `tests/test_imports.py` | Python | Import smoke test. | MEDIUM | Yes |
| 118 | `tests/test_settings.py` | Python | Settings defaults/paths. | MEDIUM | Yes |
| 119 | `tests/test_classroom_client.py` | Python | Classroom pagination client test. | MEDIUM | Yes |
| 120 | `tests/integration/test_workflow.py` | Python | End-to-end workflow with MockProvider + SQLite checkpointer. | HIGH | Yes |
| 121 | `tests/integration/test_docx_pdf_export.py` | Python | DOCX + PDF export integration. | HIGH | Yes |
| 122 | `tests/ui/test_ui_smoke.py` | Python | MainWindow smoke test. | MEDIUM | Yes |
| 123 | `tests/ui/test_review_page_status.py` | Python | Review page evaluation-status rendering. | MEDIUM | Yes |
| 124 | `tests/unit/test_calculations.py` | Python | Safe arithmetic evaluator. | MEDIUM | Yes |
| 125 | `tests/unit/test_configs.py` | Python | Category YAML loading/validation. | HIGH | Yes |
| 126 | `tests/unit/test_database.py` | Python | DB init + repositories. | MEDIUM | Yes |
| 127 | `tests/unit/test_evaluator_fail_safe.py` | Python | Evaluator fail-safe + routing. | HIGH | Yes |
| 128 | `tests/unit/test_generator_user_data.py` | Python | User-provided data injection into prompts. | HIGH | Yes |
| 129 | `tests/unit/test_gmail.py` | Python | Gmail search parsing. | MEDIUM | Yes |
| 130 | `tests/unit/test_latex.py` | Python | LaTeX escaping + generator rendering. | HIGH | Yes |
| 131 | `tests/unit/test_models.py` | Python | Pydantic domain models. | MEDIUM | Yes |
| 132 | `tests/unit/test_nvidia_provider.py` | Python | NVIDIA provider fallback/structured output. | HIGH | Yes |
| 133 | `tests/unit/test_ocr_pdf.py` | Python | OCR fallback + PDF error handling. | MEDIUM | Yes |
| 134 | `tests/unit/test_parsers.py` | Python | File parsers + normalizer. | MEDIUM | Yes |
| 135 | `tests/unit/test_preferences.py` | Python | Preferences persistence. | MEDIUM | Yes |
| 136 | `tests/unit/test_rag.py` | Python | Chunking + retrieval. | MEDIUM | Yes |
| 137 | `tests/unit/test_reference_integrity.py` | Python | Reference provenance / no-fabrication rules. | HIGH | Yes |
| 138 | `tests/unit/test_security.py` | Python | Sanitization / untrusted-data wrapping. | MEDIUM | Yes |
| 139 | `tests/unit/test_workflow_nodes.py` | Python | `normalize_node` unit test. | MEDIUM | Yes |
| 140 | `tests/fixtures/.gitkeep` | Placeholder | Empty fixture dir. | LOW | No |
| 141 | `tests/integration/.gitkeep` | Placeholder | Empty placeholder. | LOW | No |
| 142 | `tests/ui/.gitkeep` | Placeholder | Empty placeholder. | LOW | No |
| 143 | `tests/unit/.gitkeep` | Placeholder | Empty placeholder. | LOW | No |

## 4. Files that could not be (fully) inspected

| File | Reason | Limitation |
|---|---|---|
| `.env` | Contains secrets | Existence verified only; contents intentionally not read |
| `credentials.json` | Google OAuth secret | Existence verified only; contents intentionally not read |
| `storage/*.db`, `storage/outputs/*` | Binary runtime data | Not inspected; excluded as generated/user data |
| `document/templates/academic_base.docx` | 0-byte empty file; Graphify office conversion failed | Cannot be analyzed; confirmed empty and unused |
| `document/templates/latex/references.bib.j2` | 0-byte empty file | Cannot be analyzed; confirmed empty and unused |
| `names.java`, `names1.java` | Not Java; contain prompt prose | Graphify AST reported syntax errors and extracted no symbols |
| `uv.lock` | Generated lockfile | Listed but not reviewed line-by-line |

## 5. Cross-reference

- Prompt/instruction analysis: `02_PROMPT_AND_INSTRUCTION_AUDIT.md`
- LaTeX/document formatting: `03_LATEX_AND_DOCUMENT_FORMATTING_AUDIT.md`
- Dependency map: `04_FILE_DEPENDENCY_MAP.md`
- Prioritized review order: `01_MANUAL_REVIEW_CHECKLIST.md`
- Summary and findings: `05_PROJECT_AUDIT_SUMMARY.md`
- Graphify knowledge graph: `06_GRAPHIFY_PROJECT_KNOWLEDGE_GRAPH.md`
