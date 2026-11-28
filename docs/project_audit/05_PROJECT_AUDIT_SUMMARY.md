# 05 — Project Audit Summary

> Read-only audit. **No project file was modified, deleted, renamed, or refactored.** The only files created are the six audit documents plus the copied Graphify artifacts under `docs/project_audit/`.

## 1. Scope and method

- **Repository**: `C:\Users\LENOVO\Desktop\AI_PROJECTS\Academic_Assistent`
- **Excluded from audit**: `.venv/`, `.git/`, caches (`__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`), `graphify-out/`, `.freebuff/`, `dist/`, `build/`.
- **Secrets policy**: `.env` and `credentials.json` were confirmed to exist but **contents were not read or printed**. Storage databases were not opened.
- **Methods**: direct file reads, targeted `grep`/PowerShell searches, YAML/code cross-checks, and the Graphify knowledge graph (AST + semantic extraction).
- **Verified vs inferred**: all structural claims below are VERIFIED unless explicitly marked INFERRED/Graphify-derived.

## 2. Totals

| Metric | Count |
|---|---|
| Files inventoried (excluding exclusions above) | **143** |
| Files considered relevant to the project | **143** |
| Graphify corpus files | **128** |
| Graphify graph | **1153 nodes / 2664 edges / 79 communities** |
| Python source modules | 71 |
| Test files | 18 (+5 `.gitkeep`) |
| Prompt `.txt` files (primary) | **9** |
| Duplicate/misnamed prompt files | 2 (`names.java`, `names1.java`) |
| YAML prompt-bearing configs | 3 (`assignment`, `initial_lab`, `final_lab`) |
| Embedded prompts in code | 1 (`ai/classifier.py`; evaluator system prompt also inline) |
| LaTeX files | **4** (`report.tex.j2`, `references.bib.j2`, `latex_generator.py`, `latex_escape.py`) |
| Document-generation modules | **8** |
| Formatting config blocks | **3** (one per category YAML) |
| Config/env/dependency files | **17** |

## 3. Priority breakdown

| Priority | Count | Meaning |
|---|---|---|
| **CRITICAL** | **29** | Core runtime: entry point, workflow, AI engine, providers, document export, schema, settings, DB, main UI |
| **HIGH** | **53** | Important UI, integrations, models, tests, prompts, templates, packaging |
| **MEDIUM** | **40** | Supporting docs, secondary scripts, styles, preferences |
| **LOW** | **21** | Meta docs, placeholders, `.gitkeep`, duplicate prompt files, minor config |
| **Total** | **143** | |

## 4. Top files to review first

| Rank | File | Why |
|---|---|---|
| 1 | `plan.md` | Authoritative design and conventions |
| 2 | `configs/schema.py` | Contract every category config must satisfy |
| 3 | `configs/assignment.yaml` / `initial_lab.yaml` / `final_lab.yaml` | Sections, word limits, rubric, formatting |
| 4 | `ai/prompts/*.txt` (9) | Directly shape AI output |
| 5 | `ai/generator.py` | Section generation + prompt binding |
| 6 | `ai/evaluator.py` | Deterministic + semantic pass/fail |
| 7 | `document/templates/latex/report.tex.j2` | Primary PDF layout (hard-coded formatting) |
| 8 | `document/latex_generator.py` | Template binding, escaping, data injection |
| 9 | `workflow/graph.py` + `workflow/nodes.py` | The 11-node pipeline and its side effects |
| 10 | `ai/llm/factory.py` + `ai/llm/nvidia.py` | Provider selection and API behavior |
| 11 | `app/settings.py` + `.env.example` | Runtime configuration surface |
| 12 | `app/ui/workers.py` | Background execution of the workflow |
| 13 | `models/report.py` + `models/evaluation.py` | Data contracts across the system |
| 14 | `document/docx_generator.py` + `document/pdf_exporter.py` | Output generation and fallback chain |
| 15 | `pyproject.toml` | Dependencies and toolchain |

## 5. Key findings

### Architecture (verified)
- The app is a **local-first PySide6 desktop application** with a **LangGraph** workflow of 11 nodes and a **SQLite** checkpointer.
- AI is behind a small `LLMProvider` interface; the factory selects **NVIDIA NIM** in production and **Mock** offline. `GeminiProvider` remains as **legacy, unselected** code.
- Rules live in **YAML category configs**; instructions live in **file-based prompts**; appearance lives in **LaTeX/DOCX templates**. This separation is clean and is the main reason formatting can be audited independently of AI behavior.
- Export is **PDF-first with fallbacks**: Tectonic → XeLaTeX → LibreOffice, plus native DOCX generation.

### Documentation drift (verified)
- `README.md` and `docs/STUDENT_GUIDE.md` still describe **Gemini**; the runtime uses **NVIDIA NIM**.
- `docs/08_TECHNICAL_DEBT_AND_IMPROVEMENTS.md` contains some pre-NVIDIA and now-resolved items; treat it as historical context, not current truth.

### Formatting divergence (verified)
- `configs/*.yaml::formatting` drives **DOCX only**. The **LaTeX/PDF path ignores it** and hard-codes margins (left 1.25 in), line spacing (1.25), and Times New Roman 12 pt. Changing YAML formatting will not change the PDF.

### Dead / unused assets (verified)
- `document/templates/academic_base.docx` — **0 bytes, unused**.
- `document/templates/latex/references.bib.j2` — **0 bytes, unused** (manual `thebibliography` is used instead).
- `names.java` and `names1.java` — **byte-identical prompt text** misnamed as Java; not used at runtime.
- `ai/llm/gemini.py` — not reachable from the factory.

### Risks worth attention (verified/documented)
- Prompt files fail **silently** to generic fallbacks if missing (`ai/generator.py`, `ai/evaluator.py`).
- No prompt/report version trace; reports are not reproducible against the prompt that produced them.
- LaTeX `logo_path` is injected into `\includegraphics` with only backslash normalization — path characters can break compilation or inject TeX.
- Prompt-injection redaction is a short literal regex; paraphrased injections are not caught.
- Pre-existing working-tree state before this audit: **`ai/llm/nvidia.py` was already modified (`M`)** and **`tests/unit/test_nvidia_provider.py` was already untracked (`??`)**; neither was touched by the audit.

## 6. Files not inspected (and why)

| Item | Reason |
|---|---|
| `.env` | Contains secrets; existence confirmed only |
| `credentials.json` | Contains OAuth secrets; existence confirmed only |
| `storage/academic_ai.db`, `storage/workflow_checkpoints.db` | Runtime databases; not opened |
| `storage/credentials.json`, tokens | Secrets; not read |
| `storage/outputs/`, `logs/`, `rag/`, `references/` | Generated runtime artifacts; not audited |
| `uv.lock` | Lock file; spot-checked only |
| `document/assets/tu_logo.png` | Binary image; referenced but content not audited |
| `.venv/`, `dist/`, `build/` | Excluded by design |
| `.git/` | Version-control internals; excluded |
| `graphify-out/` | Generated graph; summarized, not hand-inspected line by line |

## 7. Recommended next actions (no changes made)

1. Reconcile docs with the NVIDIA migration (`README.md`, `STUDENT_GUIDE.md`, `docs/08`).
2. Decide the fate of the four dead assets (empty DOCX/bib, duplicate `.java`) — **do not delete without owner approval**.
3. Make prompt loading fail loudly (or log a warning) instead of silently using fallbacks.
4. Align LaTeX formatting with YAML, or document that PDF formatting is intentionally fixed.
5. Sanitize/validate `logo_path` before `\includegraphics`.
6. Add a prompt/config hash to persisted reports for reproducibility.
7. Confirm whether `GeminiProvider` and `google-genai` are still intended; otherwise mark deprecated.

## 8. Artifact index

| Document | Contents |
|---|---|
| `00_COMPLETE_FILE_INVENTORY.md` | 143-file inventory, counts, exclusions, uninspected files |
| `01_MANUAL_REVIEW_CHECKLIST.md` | Phased checkbox review order |
| `02_PROMPT_AND_INSTRUCTION_AUDIT.md` | Prompt inventory, wiring, variables, risks |
| `03_LATEX_AND_DOCUMENT_FORMATTING_AUDIT.md` | Formatting controls, divergences, dead hooks |
| `04_FILE_DEPENDENCY_MAP.md` | Verified dependencies, Mermaid diagrams, orphans |
| `05_PROJECT_AUDIT_SUMMARY.md` | This summary |
| `06_GRAPHIFY_PROJECT_KNOWLEDGE_GRAPH.md` | Graph method, stats, communities, limitations |
| `graphify/graph.json` | Canonical machine graph |
| `graphify/graph.html` | Interactive graph viewer |
| `graphify/GRAPH_REPORT.md` | Human-readable Graphify report |

## 9. Confirmation

No source file, prompt, template, dependency, or configuration was modified. Pre-existing working-tree state (left untouched): `ai/llm/nvidia.py` (`M`) and untracked `tests/unit/test_nvidia_provider.py` (`??`). The audit created only `docs/project_audit/`; the `graphify-out/` changes are generated graph artifacts from the mandatory Graphify update.
