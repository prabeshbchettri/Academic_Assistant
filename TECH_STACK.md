# Tech Stack — Academic AI (`academic-ai`)

Generated from a full source/config audit after building the Graphify knowledge graph
(798 nodes, 1,949 edges, 39 communities; hubs: `ReportContent`, `LLMProvider`, `MainWindow`,
`HomePage`, `AssignmentRepository`, `WorkflowState`, `build_academic_workflow()`).

**Product shape:** a single-user, local-first **desktop application** (with a headless CLI mode).
There is no web server. "Backend" here means the in-process orchestration/domain layer.

## Status legend

| Status | Meaning |
|---|---|
| **Implemented** | Imported and executed by application code on the normal path. |
| **Implemented (optional)** | Code exists and works, but is gated by a flag/extra and disabled by default. |
| **Configured** | Wired in config/build files, but not exercised on the default path. |
| **Planned** | Only described in `plan.md`/docs, no working code/config. |
| **Not used** | Declared as a dependency but never imported. |

> Note: `.venv/` in this checkout is empty (only `pip`). Dependencies are declared and locked in
> `uv.lock`; the README instructs `uv sync --extra dev --extra google`.

---

## 1. Frontend (Desktop UI)

| Technology | Version | What it does | Where used | Why | Status | Files |
|---|---|---|---|---|---|---|
| **PySide6** (Qt 6 for Python) | `>=6.8` | Native cross-platform desktop widgets, signals/slots, threading | App shell, 6 pages, widgets, worker threads | Native desktop UX, crash-free packaging, no browser runtime | Implemented | `app/ui/main_window.py`, `app/ui/pages/*.py`, `app/ui/widgets/*.py`, `app/ui/workers.py` |
| **Qt QSS** (Qt Style Sheets) | — | CSS-like styling for Qt widgets | Global app stylesheet | Theme without a web stack | Implemented | `app/ui/styles.qss` (loaded in `main_window.py:47`) |
| **Python** | 3.12 (`>=3.12,<3.13`) | UI + application language | Entire codebase | Single-language stack for a local tool | Implemented | `pyproject.toml`, `.python-version` |
| **Qt QThread / Signals** | — | Background workflow + classroom fetching, UI progress | `WorkflowWorker`, `ClassroomCoursesWorker`, progress/review signals | Keep LLM/network work off the UI thread | Implemented | `app/ui/workers.py`, `app/ui/pages/*.py` |
| **QStackedWidget navigation** | — | Manual page routing (index-based) | 6 pages: Home, Input, Processing, Review, History, Settings | Simple wizard-style navigation, no router library needed | Implemented | `app/ui/main_window.py:59+` |
| **State management** | — | Qt signal/slot bus + Pydantic `WorkflowState` + persisted JSON prefs | UI state, workflow state, user preferences | No Redux/React equivalent; desktop event model | Implemented | `app/ui/workers.py`, `workflow/state.py`, `app/preferences.py` |
| **Markdown** | `>=3.6` | Renders Markdown section previews in the UI | Document preview widget | LLM output is Markdown; render it for review | Implemented | `app/ui/widgets/preview.py:3` |
| **Argparse (stdlib)** | — | CLI mode flags (`--cli`, `--mock`, `--title`, `--prompt`, `--category`) | Headless generation path | Test/automation without GUI | Implemented | `app/main.py:77-97` |
| React / Vue / Electron / web frontend | — | — | — | Not present — not a web app | Not used | — |

---

## 2. Backend (Orchestration & Domain Layer)

| Technology | Version | What it does | Where used | Why | Status | Files |
|---|---|---|---|---|---|---|
| **Python** | 3.12 | Application language | Everywhere | — | Implemented | `pyproject.toml` |
| **LangGraph** | `>=0.2` | Stateful agent/workflow graph: nodes, conditional edges, interrupts | 11-node academic workflow, retry loop, human-in-the-loop | Deterministic state machine with resumable HITL | Implemented | `workflow/graph.py`, `workflow/nodes.py`, `workflow/routing.py` |
| **Pydantic v2** | `>=2.9` | Typed domain models + schema-validated LLM output | Assignment, report, evaluation, workflow models | Validation at every LLM boundary | Implemented | `models/*.py`, `configs/schema.py` |
| **pydantic-settings** | `>=2.6` | Env/.env-backed settings with `SecretStr` | App config (models, keys, paths, PDF engines) | Typed config with secret redaction | Implemented | `app/settings.py` |
| **PyYAML** | `>=6.0` | Loads per-category YAML rules | `assignment`, `initial_lab`, `final_lab` configs | Data-driven prompts/rubrics/limits | Implemented | `configs/schema.py`, `configs/*.yaml` |
| **Jinja2** | `>=3.1` | Prompt templating + LaTeX report template rendering | Section generator, evaluator, LaTeX exporter | Single templating engine for prompts and documents | Implemented | `ai/generator.py`, `ai/evaluator.py`, `document/latex_generator.py`, `document/templates/latex/*.j2` |
| **API architecture** | — | No HTTP server; in-process service layer + outbound REST calls | Workflow nodes call services; integrations call Google/Gemini REST APIs | Local single-user app | Implemented | `workflow/nodes.py`, `integrations/*` |
| **Google OAuth 2.0 (installed-app flow)** | `google-auth-oauthlib>=1.2` | Student sign-in, token refresh | Classroom/Gmail/Drive access | Read-only student-scoped access, no password handling | Implemented (`[google]` extra) | `integrations/google_auth.py` |
| **Keyring** | `>=25.0` | OS credential store for OAuth tokens | Token persistence (with 0600 file fallback) | Keep tokens out of plaintext config | Implemented | `integrations/google_auth.py:39-76` |
| **Tenacity** | `>=9.0` | Retry/backoff helper | — | Listed for retries, but retries are hand-rolled in `workflow/routing.py` and `GeminiProvider` | **Not used** | `pyproject.toml:19`, `pyinstaller.spec:22` |
| **FastAPI / Flask / Django** | — | — | — | No web backend exists | Not used | — |

### Authorization model
- OAuth scopes are **read-only Student scopes**: courses, coursework, materials, student submissions, Gmail readonly (`integrations/google_auth.py:24-30`).
- No role-based auth, no multi-user server, no JWT/session layer — single local student.
- Prompt-injection defense: length cap, pattern redaction, random delimiter wrapping (`ai/security.py`).

---

## 3. Database and Storage

| Technology | Version | What it does | Where used | Why | Status | Files |
|---|---|---|---|---|---|---|
| **SQLite** | stdlib | Embedded relational DB | `storage/academic_ai.db`; checkpoints in `storage/workflow_checkpoints.db` | Local-first, zero-install, single file | Implemented | `database/db.py:16-45`, `workflow/checkpointer.py` |
| **SQLModel** | `>=0.0.22` | ORM tables + typed queries | 8 tables: assignments, sources, workflow runs, documents, references, audit log, schema version | Pydantic + SQLAlchemy combined | Implemented | `database/models.py`, `database/repositories.py`, `database/migrations.py` |
| **SQLAlchemy** | transitive via SQLModel | Engine/event layer, pragmas | `PRAGMA journal_mode=WAL`, `synchronous=NORMAL`, `foreign_keys=ON` | Concurrency safety for worker + UI threads | Implemented | `database/db.py:6,35-41` |
| **langgraph-checkpoint-sqlite** | `>=2.0` | Durable workflow checkpoints / resume | `SqliteSaver` per thread | Crash recovery + HITL resume | Implemented | `workflow/checkpointer.py` |
| **ChromaDB** | `>=0.5` (`[rag]` extra) | Local persistent vector store | `storage/rag` collections per course | Grounding/citations without a server | Implemented (optional) — disabled in all 3 category configs, extra not installed here | `ai/retriever.py`, `scripts/index_reference.py`, `configs/*.yaml` (`rag.enabled: false`) |
| **Filesystem storage** | — | Versioned artifacts + inputs/logs | `storage/outputs/<id>/v<n>/`, `storage/inputs`, `storage/references`, `storage/logs`, `storage/credentials` | Simple auditable local layout | Implemented | `app/settings.py:34`, `document/*.py` |
| **Caching** | — | No cache layer (no Redis/Memcached/disk cache) | — | Not needed at this scale | Not present | — |
| PostgreSQL / MySQL / Redis / pgvector | — | — | — | Not present | Not used | — |

---

## 4. AI and Machine Learning

| Technology | Version | What it does | Where used | Why | Status | Files |
|---|---|---|---|---|---|---|
| **google-genai** (Google Gen AI SDK) | `>=1.0` | Gemini API client: structured JSON output, text, embeddings | Classification, section generation, evaluation, RAG embeddings | Native schema-constrained output | Implemented | `ai/llm/gemini.py` |
| **Gemini 2.5 Flash Lite** (`gemini-2.5-flash-lite`) | API | Primary model default | `settings.gemini_model` | Free-tier cost/latency | Implemented (code default) | `app/settings.py:21` |
| **Gemini 2.5 Flash** (`gemini-2.5-flash`) | API | Fallback model | `settings.gemini_fallback_model` + hardcoded chain | Resilience to quota/model changes | Implemented | `app/settings.py:22`, `ai/llm/gemini.py:59,96` |
| **Gemini 2.5 Pro** (`gemini-2.5-pro`) | API | Premium model setting | `settings.gemini_pro_model` | Higher-quality option | Configured (not referenced by provider code) | `app/settings.py:23` |
| **Gemini 3.x Flash / 3.1 Pro** | API | Documented future/preferred models | `.env.example`, `plan.md` | Planned upgrade | **Planned / config-only** — code defaults are 2.5 series | `.env.example:2-4`, `plan.md` |
| **Gemini embeddings** (`gemini-embedding-001`) | API | Text embeddings for RAG | `GeminiProvider.embed()` | Consistent provider, no local model | Implemented (only reached when RAG + Gemini provider active) | `ai/llm/gemini.py:113-122`, `app/settings.py:24` |
| **LangGraph** | `>=0.2` | Agent/workflow framework (graph of nodes, interrupts) | 11-node pipeline | Controlled multi-step generation, not free-form agents | Implemented | `workflow/graph.py` |
| **Provider abstraction (`LLMProvider`)** | — | Interface: structured, text, embed | Swappable Gemini/Mock providers | Testability + offline mode | Implemented | `ai/llm/base.py` |
| **MockProvider** | — | Deterministic offline LLM + embeddings | Tests, UI demo, `--mock`, CLI auto-fallback | No API key needed for dev/CI | Implemented | `ai/llm/mock.py` |
| **RAG pipeline** | — | Chunk (1000/150 overlap) → embed → store → retrieve top-k | `RagRetriever`, `scripts/index_reference.py`, `retrieve_references` node | Ground outputs in course material | Implemented (optional), **disabled** by config | `ai/retriever.py`, `workflow/nodes.py` |
| **Evaluator (LLM-as-judge + rubric)** | — | Weighted rubric scoring via structured output; per-category weights | `evaluate_output` node, retry routing | Quality gate before human review | Implemented | `ai/evaluator.py`, `configs/*.yaml` (`rubric`) |
| **Deterministic validation** | — | Required sections, word limits, banned phrases, placeholder detection | Evaluator pre-checks | Cheap, reproducible checks | Implemented | `ai/evaluator.py` |
| **Safe AST math evaluator** | stdlib `ast` | Whitelisted arithmetic + math functions, no `eval` | Pre-computed formula results fed to prompts | Prevent code execution / arithmetic hallucination | Implemented | `ai/calculations.py` |
| **Prompt-injection defenses** | — | Input cap + redaction + untrusted-data delimiters | All external text into prompts | Harden against poisoned assignments | Implemented | `ai/security.py` |
| PyTorch / TensorFlow / scikit-learn / local LLMs | — | — | — | Not present — no local model inference | Not used | — |
| LangChain (beyond LangGraph), CrewAI, AutoGen | — | — | — | Not present | Not used | — |

---

## 5. Infrastructure and DevOps

| Technology | What it does | Where used | Why | Status | Files |
|---|---|---|---|---|---|
| **PyInstaller** `>=6.10` | Builds a one-folder native desktop app; bundles YAML, prompts, LaTeX templates, QSS | Packaging | Ship without Python install | Configured (build tool; no artifact in repo) | `pyinstaller.spec`, `scripts/build.py` |
| **uv** | Dependency resolution, lockfile, venv, `uv run` | Dev/run workflow | Fast, reproducible Python | Implemented (tooling) | `uv.lock`, `scripts/run.sh`, `scripts/run.bat`, README |
| **Tectonic** (external binary) | XeTeX-based LaTeX compiler, primary PDF engine | `PdfExporter._compile_with_tectonic` | High-quality typeset PDF, self-contained | Implemented (optional, invoked if binary present) | `document/pdf_exporter.py:68-88`, `app/settings.py:30` |
| **XeLaTeX / pdfLaTeX** (external) | Secondary PDF engine | `_compile_with_xelatex` | Fallback typography | Implemented (optional) | `document/pdf_exporter.py:90-112` |
| **LibreOffice headless** (external) | DOCX→PDF fallback | `_compile_with_libreoffice` | Last-resort fidelity fallback | Implemented (optional) | `document/pdf_exporter.py:114-137` |
| **Tesseract OCR** (external) via `pytesseract` | OCR for scanned PDFs | `perform_ocr_if_needed`, scanned-PDF branch | Text from image-only PDFs | Implemented but **currently broken**: `ocr.py:24` uses `fitz.Matrix` while importing `pymupdf`, so it raises and silently returns empty | `integrations/file_parser/ocr.py`, `integrations/file_parser/pdf.py:29-35` |
| **Git / GitHub** | Version control, remote `prabeshbchettri/Academic_Assistant`, branch `main` | Repo | — | Implemented | `.git/` |
| Docker / Podman / Compose | — | — | Not present | Not used | — |
| GitHub Actions / CI/CD | — | — | No `.github/`, no pipeline config | Not used | — |
| Cloud deployment (AWS/GCP/Azure hosting) | — | — | Desktop app; no deployment of own services | Not used | — |
| Cloud services (consumed) | Google Gemini API; Google Classroom/Gmail/Drive REST APIs | LLM + integrations | — | Implemented (external SaaS) | `ai/llm/gemini.py`, `integrations/*` |

---

## 6. Development Tools

| Technology | Version | What it does | Where used | Why | Status | Files |
|---|---|---|---|---|---|---|
| **uv** | — | Package/project manager + lockfile | Install, run, sync extras | Fast reproducible env | Implemented | `pyproject.toml`, `uv.lock` |
| **pytest** | `>=8` | Test runner | 20 test modules (unit/integration/UI) | Standard Python testing | Implemented | `pyproject.toml:49-52`, `tests/**` |
| **pytest-qt** | `>=4.4` | Qt widget testing (`qtbot`) | UI smoke test | Test real PySide6 widgets | Implemented | `tests/ui/test_ui_smoke.py:5` |
| **pytest-cov** | `>=5` | Coverage plugin | — | Coverage measurement | Configured (no `--cov` in `addopts`; run manually) | `pyproject.toml:39` |
| **pytest-mock** | `>=3.14` | `mocker` fixture | — | Convenience mocking | **Not used** — tests use `unittest.mock.MagicMock` | `pyproject.toml:38`, `tests/unit/test_gmail.py:1` |
| **Ruff** | `>=0.7` | Linting/import sorting (`E,F,I,UP,B,SIM`, line 100) | All Python | Fast lint | Configured | `pyproject.toml:54-59` |
| **mypy** | `>=1.11` | Static typing (`py312`, ignores missing imports) | All Python | Type safety | Configured | `pyproject.toml:61-64` |
| **types-pyyaml** | — | Type stubs for PyYAML | Type checking | mypy support | Configured | `pyproject.toml:43` |
| **Python stdlib `logging` + `RotatingFileHandler`** | — | Console + rotating file logs (5 MB × 3) | App-wide; `storage/logs/app.log` | Zero-dependency observability | Implemented | `app/logging_config.py` |
| **Git / GitHub** | — | VCS + remote | Repository | Collaboration/history | Implemented | `.git/` |
| **Serial/make-like scripts** | — | Launch wrappers (`uv run python -m app.main`) | Dev launcher | One-command start | Implemented | `scripts/run.sh`, `scripts/run.bat` |
| Sentry / OpenTelemetry / Prometheus / Datadog | — | — | — | Not present | Not used | — |
| pre-commit / black / isort / flake8 | — | — | — | Ruff covers these roles | Not used | — |

### Test inventory (evidence of implemented test stack)
`tests/test_imports.py`, `tests/test_settings.py`, `tests/test_classroom_client.py`,
`tests/unit/{test_calculations,test_configs,test_database,test_gmail,test_latex,test_models,test_parsers,test_preferences,test_rag,test_security}.py`,
`tests/integration/test_workflow.py`, `tests/integration/test_docx_pdf_export.py`,
`tests/ui/test_ui_smoke.py`.

---

## 7. Document Pipeline (cross-cutting)

| Technology | Version | What it does | Where used | Status | Files |
|---|---|---|---|---|---|
| **python-docx** | `>=1.1` | DOCX creation + parsing | Report export, DOCX input parser | Implemented | `document/docx_generator.py`, `document/markdown_to_docx.py`, `integrations/file_parser/docx.py` |
| **PyMuPDF** | `>=1.24` | PDF text extraction (and page rasterization for OCR) | PDF input parser | Implemented | `integrations/file_parser/pdf.py`, `ocr.py` |
| **Pillow** | `>=10.4` | Image objects for OCR | OCR path | Implemented (reached only via OCR) | `integrations/file_parser/ocr.py:17` |
| **Jinja2 LaTeX template** | `>=3.1` | `report.tex.j2` + `references.bib.j2` rendering | PDF export | Implemented | `document/templates/latex/*` |
| **Custom LaTeX escaping** | — | Escapes user/LLM text, sanitizes math | LaTeX generation | Implemented | `document/latex_escape.py` |
| **Markdown→LaTeX / Markdown→DOCX converters** | — | Hand-rolled converters (subset) | Export | Implemented | `document/latex_generator.py:12`, `document/markdown_to_docx.py` |
| `document/templates/academic_base.docx` | — | DOCX template asset | Bundled in PyInstaller spec | Configured (not loaded by `DocxGenerator`, which builds from scratch) | `document/templates/`, `pyinstaller.spec:7-12` |

---

## 8. Unused / Misleading Items

| Item | Declared in | Finding |
|---|---|---|
| **tenacity** | `pyproject.toml` core deps, `pyinstaller.spec` hidden imports | Zero imports in source. Retry behavior is hand-written (`workflow/routing.py`, `ai/llm/gemini.py`). Safe to remove or implement. |
| **pytest-mock** | `pyproject.toml [dev]` | No `mocker` fixture usage; tests use `unittest.mock`. |
| **Gemini 3.x model IDs** | `.env.example`, `plan.md`, `docs/STUDENT_GUIDE.md` | Not the code defaults (`app/settings.py` uses 2.5-series). Treat as planned/intended config, not active. |
| **ChromaDB RAG** | `pyproject.toml [rag]`, `ai/retriever.py` | Fully coded but `rag.enabled: false` in all category configs and `[rag]` extra is not installed in this checkout. No reference documents indexed. |
| **OCR (Tesseract)** | deps + `ocr.py` | Real bug: `fitz.Matrix` referenced without importing `fitz` → OCR silently never succeeds. |
| **`fitz` hidden import** | `pyinstaller.spec:24` | Code imports `pymupdf`; `fitz` is a legacy PyMuPDF alias. Works only if the alias ships, but inconsistent with source. |
| **classroom_base.docx** | Not referenced in source | No code path loads it; DOCX is generated programmatically. |
| **Docker / CI / cloud deploy** | — | Absent. Any claim of these would be documentation-only. |

---

## 9. Summary by Layer

- **Frontend:** Python 3.12 + PySide6 (Qt 6) desktop UI, QSS styling, QThread workers, QStackedWidget routing, signals/slots state, Markdown preview, argparse CLI.
- **Backend:** In-process Python service layer orchestrated by LangGraph (11 nodes, conditional retry, interrupt-based HITL), Pydantic v2 models, pydantic-settings, PyYAML configs, Jinja2 templating. Auth = Google OAuth 2.0 installed-app flow with read-only student scopes; tokens in OS keyring.
- **Data:** SQLite via SQLModel/SQLAlchemy (WAL) + LangGraph SQLite checkpoints; local filesystem artifact store. Optional ChromaDB vector store (disabled). No cache, no external DB.
- **AI:** Google Gemini via `google-genai` (Flash Lite default → Flash fallback), structured JSON output, Gemini embeddings, optional ChromaDB RAG, rubric-based LLM evaluation + deterministic checks, safe AST math, prompt-injection defenses. Tests use a deterministic MockProvider.
- **Infra/DevOps:** PyInstaller one-folder builds, uv lockfile, external Tectonic / XeLaTeX / LibreOffice / Tesseract toolchain. No containers, no CI/CD, no cloud hosting.
- **Dev tools:** uv, pytest (+qt, +cov), ruff, mypy, stdlib rotating-file logging, Git/GitHub.

### Highest-confidence "actually used" stack
`Python 3.12 · PySide6 · LangGraph · langgraph-checkpoint-sqlite · Pydantic v2 · pydantic-settings · SQLModel/SQLAlchemy · SQLite · google-genai (Gemini 2.5 Flash Lite/Flash) · google-api-python-client · google-auth-oauthlib · keyring · Jinja2 · PyYAML · python-docx · PyMuPDF · Markdown · uv · pytest/pytest-qt · ruff · mypy · PyInstaller`
