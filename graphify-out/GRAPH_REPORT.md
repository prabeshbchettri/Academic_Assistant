# Graph Report - Academic_Assistent  (2026-11-28)

## Corpus Check
- 57 files · ~70,656 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1153 nodes · 2664 edges · 79 communities (58 shown, 21 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 288 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Evaluation & Category Config
- LLM Providers & Generator Core
- Input Page & Classroom Selection
- Database Engine & Repositories
- Assignment Category Config
- Prompt Sets & Guardrails
- Calculations & Config Schema
- Document Generation & Preview
- NVIDIA Provider
- NVIDIA Provider Tests
- OCR & PDF Tests
- File Parsing & Markdown-to-DOCX
- Home Page UI
- Report Export & Formatting
- App Shell & Navigation
- DOCX Generator Internals
- File Parser Base & DOCX
- Classifier & Domain Models
- UI Pages & Course Card
- Gemini Provider & Tech Stack
- Evaluation Prompts & Architecture
- Code Understanding & Workflow
- Persistence & Model Config
- Review Page UI
- OCR Fallback
- Preferences
- LaTeX Generator
- PDF Parser & Errors
- Technical Debt & Overview
- Settings & Environment
- Workflow Workers
- Processing Page & Progress
- Assignment Formatting Config
- Initial Lab Config
- Lab Formatting Config
- PDF Test Fakes
- Final Lab Config
- Assignment Section Limits
- Lab Section Limits
- Generation Prompts & Flow
- Security & Sanitization
- Section Editor Widget
- System Architecture & Concurrency
- LaTeX Escaping & Tests
- History Page
- Domain Contracts & State
- Document Preview Widget
- Prompt Config Keys
- Rubric Schema
- Word Limits Schema
- Final Lab Rubric Schema
- Final Lab Word Limits
- Apparatus Limits
- Conclusion Limits
- Error Analysis Limits
- Experimental Data Limits
- Introduction Limits
- Results & Discussion Limits
- Theory Limits
- Calculations Limits
- Conclusion Limits (Lab)
- Objective Limits
- Observations Limits
- Procedure Limits
- RAG Config
- References Limits
- Build Script
- Repositories & SQLite Schema
- Run Script
- BibTeX Template Placeholder
- academic-ai Entry

## God Nodes (most connected - your core abstractions)
1. `MockProvider` - 42 edges
2. `ReportContent` - 42 edges
3. `LLMProvider` - 39 edges
4. `NvidiaProvider` - 30 edges
5. `HomePage` - 28 edges
6. `SectionGenerator` - 28 edges
7. `DocxGenerator` - 28 edges
8. `Citation` - 28 edges
9. `MainWindow` - 27 edges
10. `Evaluator` - 24 edges

## Surprising Connections (you probably didn't know these)
- `7. Document Pipeline (cross-cutting)` --references--> `DocxGenerator`  [INFERRED]
  TECH_STACK.md → document/docx_generator.py
- `1. Frontend (Desktop UI)` --references--> `WorkflowState`  [INFERRED]
  TECH_STACK.md → workflow/state.py
- `Tech Stack — Academic AI (`academic-ai`)` --references--> `WorkflowState`  [INFERRED]
  TECH_STACK.md → workflow/state.py
- `Tech Stack — Academic AI (`academic-ai`)` --references--> `MainWindow`  [INFERRED]
  TECH_STACK.md → app/ui/main_window.py
- `Tech Stack — Academic AI (`academic-ai`)` --references--> `AssignmentRepository`  [INFERRED]
  TECH_STACK.md → database/repositories.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Per-Category System/Generation/Evaluation Prompt Sets** — ai_prompts_assignment_system_prompt, ai_prompts_initial_lab_system_prompt, ai_prompts_final_lab_system_prompt [EXTRACTED 1.00]
- **Academic Integrity Guardrails** — plan_missing_info_placeholder, plan_prompt_injection_defense, plan_safe_ast_calculations, plan_human_in_the_loop [INFERRED 0.85]
- **Generate-Evaluate-Retry-Review Loop** — plan_langgraph_workflow, plan_retry_policy, plan_deterministic_checks, plan_semantic_evaluation, plan_human_in_the_loop [INFERRED 0.95]
- **Eleven-Node Workflow Pipeline** — code_understanding_normalizer, code_understanding_classifier, code_understanding_categoryconfig, docs_05_ai_engineering_architecture_sectiongenerator, docs_05_ai_engineering_architecture_evaluator, code_understanding_two_pause_points, docs_06_document_generation_docxgenerator, docs_06_document_generation_pdfexporter, code_understanding_assignment_repository [INFERRED 0.90]
- **LLM Provider Boundary** — code_understanding_llmprovider_abstraction, docs_05_ai_engineering_architecture_geminiprovider, docs_05_ai_engineering_architecture_mockprovider, code_understanding_classifier, docs_05_ai_engineering_architecture_sectiongenerator, docs_05_ai_engineering_architecture_evaluator, code_understanding_rag_retriever [INFERRED 0.90]
- **Deterministic Safety Guardrails** — code_understanding_deterministic_llm_split, plan_safe_ast_calculations, code_understanding_prompt_injection_defense, code_understanding_normalizer, docs_05_ai_engineering_architecture_evaluator [INFERRED 0.80]
- **ReportContent to DOCX and LaTeX Rendering Pipeline** — docs_06_document_generation_reportcontent, docs_06_document_generation_docxgenerator, docs_06_document_generation_latexgenerator, docs_06_document_generation_pdfexporter, document_templates_latex_report_tex_j2_report_template [EXTRACTED 1.00]
- **Pluggable LLM Provider Abstraction (Gemini, Mock, NVIDIA NIM)** — docs_05_ai_engineering_architecture_llmprovider, docs_05_ai_engineering_architecture_geminiprovider, docs_05_ai_engineering_architecture_mockprovider, docs_10_nvidia_nim_migration_plan_nvidiaprovider, docs_10_nvidia_nim_migration_plan_provider_factory [INFERRED 0.85]
- **Three-State Evaluation Verdict Shared Across All Category Prompts** — ai_prompts_assignment_evaluation_eval_prompt, ai_prompts_initial_lab_evaluation_eval_prompt, ai_prompts_final_lab_evaluation_eval_prompt, docs_05_ai_engineering_architecture_evaluator, docs_08_technical_debt_and_improvements_evaluator_fail_open [INFERRED 0.75]

## Communities (79 total, 21 thin omitted)

### Community 0 - "Evaluation & Category Config"
Cohesion: 0.05
Nodes (58): Evaluator, _format_user_provided_data(), SectionGenerator, MockProvider, DeterministicFinding, EvaluationResult, EvaluationStatus, SectionEvaluation (+50 more)

### Community 1 - "LLM Providers & Generator Core"
Cohesion: 0.07
Nodes (26): LLMProvider, build_llm_provider(), chunk_text(), RagRetriever, main(), run_cli_generation(), main(), test_main_imports() (+18 more)

### Community 2 - "Input Page & Classroom Selection"
Cohesion: 0.06
Nodes (24): InputPage, build_classroom_service(), download_drive_file(), list_courses(), list_coursework(), list_coursework_materials(), build_gmail_service(), get_message_content_and_attachments() (+16 more)

### Community 3 - "Database Engine & Repositories"
Cohesion: 0.12
Nodes (19): get_db_path(), get_engine(), get_session(), init_db(), run_migrations(), AssignmentTable, AuditLogTable, GeneratedDocumentTable (+11 more)

### Community 4 - "Assignment Category Config"
Cohesion: 0.04
Nodes (48): max, min, category, max, min, display_name, formatting, citation_style (+40 more)

### Community 5 - "Prompt Sets & Guardrails"
Cohesion: 0.06
Nodes (35): Assignment System Prompt, IEEE Style and Structured Schema Requirement, Final Lab System Prompt, Initial Lab System Prompt, Human Approval Gate Before Export, Future Explicit Submit-to-Classroom Action, Read-Only Google OAuth Scope Set, PDF Export Toolchain Fallback (Tectonic then LibreOffice) (+27 more)

### Community 6 - "Calculations & Config Schema"
Cohesion: 0.09
Nodes (20): evaluate_arithmetic(), extract_and_evaluate_formulas(), safe_eval(), UnsafeExpressionError, CategoryConfig, FormattingConfig, load_category_config(), MarginConfig (+12 more)

### Community 7 - "Document Generation & Preview"
Cohesion: 0.11
Nodes (11): LatexGenerator, PdfExporter, DecisionType, FigureData, ReportContent, SectionDraft, TableData, utc_now() (+3 more)

### Community 9 - "NVIDIA Provider Tests"
Cohesion: 0.19
Nodes (17): ApiError, _completion(), FakeClient, FakeCompletions, _provider(), Sample, _sdk_kwargs(), test_model_fallback_preserves_thinking_handling() (+9 more)

### Community 10 - "OCR & PDF Tests"
Cohesion: 0.14
Nodes (14): _install_fake_tesseract(), _png(), test_missing_tesseract_reports_structured_failure(), test_mixed_pdf_keeps_native_text_and_ocrs_only_empty_pages(), test_ocr_document_is_closed_on_unexpected_error(), test_ocr_failure_on_one_page_keeps_other_pages(), test_password_protected_pdf_raises_clear_error(), test_pdf_document_is_closed_when_extraction_fails() (+6 more)

### Community 11 - "File Parsing & Markdown-to-DOCX"
Cohesion: 0.17
Nodes (13): add_markdown_paragraph(), format_inline_markdown(), FileTooLargeError, parse_file(), UnsupportedFileError, compute_content_hash(), extract_title(), normalize_input() (+5 more)

### Community 13 - "Report Export & Formatting"
Cohesion: 0.13
Nodes (22): Export Flow, DocxGenerator, DOCX/PDF Formatting Divergence, FrontPage, LatexGenerator, Markdown Conversion Rules, PDF Engine Fallback Chain (Tectonic to XeLaTeX to LibreOffice), PdfExporter (+14 more)

### Community 14 - "App Shell & Navigation"
Cohesion: 0.14
Nodes (3): MainWindow, SettingsPage, test_ui_main_window_smoke()

### Community 16 - "File Parser Base & DOCX"
Cohesion: 0.23
Nodes (4): BaseFileParser, ParsedDocument, DocxParser, TextParser

### Community 17 - "Classifier & Domain Models"
Cohesion: 0.22
Nodes (8): Classifier, Category, ClassificationResult, MissingInfoRequest, NormalizedInput, SourceType, utc_now(), WorkflowRunRecord

### Community 19 - "Gemini Provider & Tech Stack"
Cohesion: 0.13
Nodes (12): GeminiProvider, 2. Backend (Orchestration & Domain Layer), 3. Database and Storage, 4. AI and Machine Learning, 6. Development Tools, 7. Document Pipeline (cross-cutting), 8. Unused / Misleading Items, 9. Summary by Layer (+4 more)

### Community 20 - "Evaluation Prompts & Architecture"
Cohesion: 0.15
Nodes (18): Assignment Evaluation Prompt, Final Lab Evaluation Prompt, Initial Lab Evaluation Prompt, CategoryConfig, Assignment Classifier, Split Composition Root, LLMProvider Abstraction, RagRetriever / ChromaDB Retrieval (+10 more)

### Community 21 - "Code Understanding & Workflow"
Cohesion: 0.14
Nodes (15): CODE_UNDERSTANDING.md — Structural Map, Eleven-Step Workflow Pipeline, Google OAuth Installed-App Flow, Graphify Knowledge Graph Tool, Six-Layer Architecture, SQLite Checkpoint Durability, Two Interrupt Pause Points, Versioned Output Folders (+7 more)

### Community 22 - "Persistence & Model Config"
Cohesion: 0.14
Nodes (17): AssignmentRepository, Persistence Flow, Classifier, GeminiProvider, LLMProvider Protocol, MockProvider, Model Configuration Drift, Retrieval-Augmented Generation (RAG) (+9 more)

### Community 23 - "Review Page UI"
Cohesion: 0.21
Nodes (5): ReviewPage, HumanDecision, _report_dict(), test_review_page_flags_inconclusive_evaluation(), test_review_page_shows_pass_status_for_passed_evaluation()

### Community 24 - "OCR Fallback"
Cohesion: 0.21
Nodes (7): is_ocr_available(), _load_ocr_dependencies(), ocr_pdf_pages(), OcrUnavailableError, perform_ocr_if_needed(), _render_page_image(), 5. Infrastructure and DevOps

### Community 25 - "Preferences"
Cohesion: 0.34
Nodes (12): AppPreferences, category_for_document_type(), DocumentDefaults, is_profile_complete(), load_preferences(), preferences_path(), save_preferences(), StudentProfile (+4 more)

### Community 26 - "LaTeX Generator"
Cohesion: 0.24
Nodes (9): _inline(), _is_table_separator(), markdown_to_latex(), close_list(), flush_paragraph(), open_list(), _prepare_text(), _render_table() (+1 more)

### Community 27 - "PDF Parser & Errors"
Cohesion: 0.18
Nodes (4): PdfParser, PdfPasswordProtectedError, PdfReadError, test_unreadable_pdf_raises_clear_error()

### Community 28 - "Technical Debt & Overview"
Cohesion: 0.18
Nodes (11): Fabricated Placeholder References (Academic-Integrity Risk), File Parser Registry, Input Normalizer and Content Hash, OCR Fallback (Currently Broken), Prompt-Injection Defense, 01 — Project Overview, Feature Inventory and Status, Production-Shaped vs Not Production-Ready (+3 more)

### Community 29 - "Settings & Environment"
Cohesion: 0.31
Nodes (4): Settings, test_defaults_do_not_require_env(), test_google_client_path_resolves_against_project_root(), test_storage_paths()

### Community 30 - "Workflow Workers"
Cohesion: 0.20
Nodes (3): ClassroomCoursesWorker, WorkflowWorker, 1. Frontend (Desktop UI)

### Community 32 - "Assignment Formatting Config"
Cohesion: 0.18
Nodes (11): formatting, citation_style, font, font_size, heading_numbering, line_spacing, margins_inches, bottom (+3 more)

### Community 33 - "Initial Lab Config"
Cohesion: 0.18
Nodes (10): category, display_name, prompts, evaluation, generation, system, references, min_count (+2 more)

### Community 34 - "Lab Formatting Config"
Cohesion: 0.18
Nodes (11): formatting, citation_style, font, font_size, heading_numbering, line_spacing, margins_inches, bottom (+3 more)

### Community 35 - "PDF Test Fakes"
Cohesion: 0.18
Nodes (3): _FakeDoc, _FakePage, test_pdf_document_is_closed_after_extraction()

### Community 36 - "Final Lab Config"
Cohesion: 0.20
Nodes (9): category, display_name, rag, collections, enabled, references, min_count, required (+1 more)

### Community 37 - "Assignment Section Limits"
Cohesion: 0.20
Nodes (10): max, min, max, min, max, min, abstract, methodology (+2 more)

### Community 38 - "Lab Section Limits"
Cohesion: 0.20
Nodes (10): max, min, max, min, max, min, apparatus, discussion (+2 more)

### Community 39 - "Generation Prompts & Flow"
Cohesion: 0.36
Nodes (8): Assignment Generation Prompt, Final Lab Generation Prompt, Initial Lab Generation Prompt, Preference Injection Gap, Generation Flow, Prompt Architecture, SectionGenerator, Untrusted-Data Wrapping and Sanitization

### Community 40 - "Security & Sanitization"
Cohesion: 0.39
Nodes (4): sanitize_external_input(), wrap_untrusted_data(), test_sanitize_external_input(), test_wrap_untrusted_data()

### Community 42 - "System Architecture & Concurrency"
Cohesion: 0.29
Nodes (8): MainWindow, WorkflowWorker, 03 — System Architecture, Concurrency Model, Error Handling and Observability, UI QStackedWidget Routing, Workflow Conditional Routing, PySide6 (Qt 6 for Python)

### Community 43 - "LaTeX Escaping & Tests"
Cohesion: 0.39
Nodes (4): escape_latex(), sanitize_math(), test_latex_escape(), test_sanitize_math()

### Community 45 - "Domain Contracts & State"
Cohesion: 0.40
Nodes (4): LangGraph SQLite Checkpointer, Domain Contracts (RawInput, NormalizedInput, ReportContent, HumanDecision, EvaluationResult), Qt Signal Contracts, WorkflowState

### Community 47 - "Prompt Config Keys"
Cohesion: 0.50
Nodes (4): prompts, evaluation, generation, system

### Community 48 - "Rubric Schema"
Cohesion: 0.50
Nodes (4): rubric, description, id, weight

### Community 49 - "Word Limits Schema"
Cohesion: 0.50
Nodes (4): max, min, word_limits, total

### Community 50 - "Final Lab Rubric Schema"
Cohesion: 0.50
Nodes (4): rubric, description, id, weight

### Community 51 - "Final Lab Word Limits"
Cohesion: 0.50
Nodes (4): max, min, word_limits, total

### Community 52 - "Apparatus Limits"
Cohesion: 0.67
Nodes (3): max, min, apparatus

### Community 53 - "Conclusion Limits"
Cohesion: 0.67
Nodes (3): max, min, conclusion

### Community 54 - "Error Analysis Limits"
Cohesion: 0.67
Nodes (3): max, min, error_analysis

### Community 55 - "Experimental Data Limits"
Cohesion: 0.67
Nodes (3): max, min, experimental_data

### Community 56 - "Introduction Limits"
Cohesion: 0.67
Nodes (3): max, min, introduction

### Community 57 - "Results & Discussion Limits"
Cohesion: 0.67
Nodes (3): max, min, results_and_discussion

### Community 58 - "Theory Limits"
Cohesion: 0.67
Nodes (3): theory, max, min

### Community 59 - "Calculations Limits"
Cohesion: 0.67
Nodes (3): max, min, calculations

### Community 60 - "Conclusion Limits (Lab)"
Cohesion: 0.67
Nodes (3): max, min, conclusion

### Community 61 - "Objective Limits"
Cohesion: 0.67
Nodes (3): max, min, objective

### Community 62 - "Observations Limits"
Cohesion: 0.67
Nodes (3): max, min, observations

### Community 63 - "Procedure Limits"
Cohesion: 0.67
Nodes (3): max, min, procedure

### Community 64 - "RAG Config"
Cohesion: 0.67
Nodes (3): rag, collections, enabled

### Community 65 - "References Limits"
Cohesion: 0.67
Nodes (3): max, min, references

## Knowledge Gaps
- **23 isolated node(s):** `MockProvider`, `ReportContent`, `Initial Lab System Prompt`, `Phased Delivery Plan (0-9)`, `Gemini Model Resolution and Fallback Chain` (+18 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 301 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **21 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Tech Stack — Academic AI (`academic-ai`)` connect `Gemini Provider & Tech Stack` to `LLM Providers & Generator Core`, `Database Engine & Repositories`, `Document Generation & Preview`, `Home Page UI`, `App Shell & Navigation`, `Persistence & Model Config`, `OCR Fallback`, `Workflow Workers`?**
  _High betweenness centrality (0.235) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `MockProvider` (e.g. with `DeterministicFinding` and `EvaluationResult`) actually correct?**
  _`MockProvider` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `MockProvider`, `ReportContent`, `Initial Lab System Prompt` to the rest of the system?**
  _23 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Evaluation & Category Config` be split into smaller, more focused modules?**
  _Cohesion score 0.05054211843202669 - nodes in this community are weakly interconnected._
- **Why does `ReportContent` connect `Report Export & Formatting` to `Domain Contracts & State`, `Evaluation Prompts & Architecture`, `Code Understanding & Workflow`, `Generation Prompts & Flow`?**
  _High betweenness centrality (0.116) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `ReportContent` (e.g. with `Evaluator` and `SectionGenerator`) actually correct?**
  _`ReportContent` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Should `LLM Providers & Generator Core` be split into smaller, more focused modules?**
  _Cohesion score 0.07140538786108407 - nodes in this community are weakly interconnected._