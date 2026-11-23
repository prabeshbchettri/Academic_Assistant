# Graph Report - Academic_Assistent  (2026-11-23)

## Corpus Check
- Corpus is ~23,794 words - fits in a single context window. You may not need a graph.

## Summary
- 798 nodes · 1949 edges · 39 communities (27 shown, 12 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 222 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Workflow Orchestration Core
- Google API Integrations
- Document Parsing & Normalization
- Database & Repositories
- Report Generation & Export
- Architecture Docs & Concepts
- Home Page & Preferences
- Assignment Category Config
- Validation & Formula Evaluation
- Final Lab Category Config
- Report Sections Schema
- App Shell & Workflow Worker
- Application Entrypoint & LLM
- Desktop UI Widgets
- Review & Edit Page
- Settings & Config Tests
- Processing Progress Page
- Initial Lab Category Config
- Formatting & Layout Config
- Lab Sections Schema
- Settings Page
- History Page
- Rubric Entry Schema
- Word Limits Schema
- Calculations Section Limits
- Conclusion Section Limits
- Objective Section Limits
- Observations Section Limits
- Procedure Section Limits
- RAG Config
- References Section Limits
- Run Script
- Project Root

## God Nodes (most connected - your core abstractions)
1. `ReportContent` - 34 edges
2. `LLMProvider` - 33 edges
3. `MockProvider` - 29 edges
4. `MainWindow` - 28 edges
5. `HomePage` - 27 edges
6. `AssignmentRepository` - 26 edges
7. `WorkflowState` - 26 edges
8. `build_academic_workflow()` - 25 edges
9. `CategoryConfig` - 24 edges
10. `RawInput` - 24 edges

## Surprising Connections (you probably didn't know these)
- `Nine-Step Assignment Generation Workflow` --semantically_similar_to--> `Student End-to-End Workflow Guide`  [INFERRED] [semantically similar]
  README.md → docs/STUDENT_GUIDE.md
- `Human Approval Gate Before Export` --semantically_similar_to--> `Mandatory Human-in-the-Loop Approval`  [INFERRED] [semantically similar]
  docs/STUDENT_GUIDE.md → plan.md
- `Read-Only Google OAuth Scope Set` --semantically_similar_to--> `Google OAuth Least-Privilege Desktop Flow`  [INFERRED] [semantically similar]
  docs/STUDENT_GUIDE.md → plan.md
- `Evaluator` --uses--> `ReportContent`  [INFERRED]
  ai/evaluator.py → models/report.py
- `SectionGenerator` --uses--> `Citation`  [INFERRED]
  ai/generator.py → models/report.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Per-Category System/Generation/Evaluation Prompt Sets** — ai_prompts_assignment_system_prompt, ai_prompts_assignment_generation_prompt, ai_prompts_assignment_evaluation_prompt, ai_prompts_initial_lab_system_prompt, ai_prompts_initial_lab_generation_prompt, ai_prompts_initial_lab_evaluation_prompt, ai_prompts_final_lab_system_prompt, ai_prompts_final_lab_generation_prompt, ai_prompts_final_lab_evaluation_prompt [EXTRACTED 1.00]
- **Generate-Evaluate-Retry-Review Loop** — plan_langgraph_workflow, plan_retry_policy, plan_deterministic_checks, plan_semantic_evaluation, plan_human_in_the_loop [INFERRED 0.95]
- **Academic Integrity Guardrails** — plan_missing_info_placeholder, plan_prompt_injection_defense, plan_safe_ast_calculations, plan_human_in_the_loop [INFERRED 0.85]

## Communities (39 total, 12 thin omitted)

### Community 0 - "Workflow Orchestration Core"
Cohesion: 0.07
Nodes (34): Classifier, Evaluator, SectionGenerator, LLMProvider, MockProvider, chunk_text(), RagRetriever, CategoryConfig (+26 more)

### Community 1 - "Google API Integrations"
Cohesion: 0.06
Nodes (24): InputPage, build_classroom_service(), download_drive_file(), list_courses(), list_coursework(), list_coursework_materials(), build_gmail_service(), get_message_content_and_attachments() (+16 more)

### Community 2 - "Document Parsing & Normalization"
Cohesion: 0.07
Nodes (22): sanitize_external_input(), wrap_untrusted_data(), add_markdown_paragraph(), format_inline_markdown(), BaseFileParser, ParsedDocument, DocxParser, FileTooLargeError (+14 more)

### Community 3 - "Database & Repositories"
Cohesion: 0.10
Nodes (23): run_cli_generation(), get_db_path(), get_engine(), get_session(), init_db(), run_migrations(), AssignmentTable, AuditLogTable (+15 more)

### Community 4 - "Report Generation & Export"
Cohesion: 0.08
Nodes (19): DocxGenerator, escape_latex(), sanitize_math(), LatexGenerator, markdown_to_latex(), PdfExporter, SourceType, Citation (+11 more)

### Community 5 - "Architecture Docs & Concepts"
Cohesion: 0.05
Nodes (47): Assignment Section Evaluation Prompt, Assignment Section Generation Prompt, Assignment System Prompt, [1], [2] Numbered Citation Convention, Final Lab Section Evaluation Prompt, Final Lab Section Generation Prompt, IEEE Style and Structured Schema Requirement, Final Lab System Prompt (+39 more)

### Community 6 - "Home Page & Preferences"
Cohesion: 0.09
Nodes (15): AppPreferences, category_for_document_type(), DocumentDefaults, is_profile_complete(), load_preferences(), preferences_path(), save_preferences(), StudentProfile (+7 more)

### Community 7 - "Assignment Category Config"
Cohesion: 0.04
Nodes (48): max, min, category, max, min, display_name, formatting, citation_style (+40 more)

### Community 8 - "Validation & Formula Evaluation"
Cohesion: 0.10
Nodes (19): evaluate_arithmetic(), extract_and_evaluate_formulas(), safe_eval(), UnsafeExpressionError, FormattingConfig, load_category_config(), MarginConfig, preload_all_configs() (+11 more)

### Community 9 - "Final Lab Category Config"
Cohesion: 0.06
Nodes (32): category, display_name, formatting, citation_style, font, font_size, heading_numbering, line_spacing (+24 more)

### Community 10 - "Report Sections Schema"
Cohesion: 0.06
Nodes (31): max, min, max, min, max, min, max, min (+23 more)

### Community 11 - "App Shell & Workflow Worker"
Cohesion: 0.15
Nodes (4): MainWindow, WorkflowWorker, RawInput, test_ui_main_window_smoke()

### Community 12 - "Application Entrypoint & LLM"
Cohesion: 0.14
Nodes (5): GeminiProvider, configure_logging(), main(), build(), test_main_imports()

### Community 14 - "Review & Edit Page"
Cohesion: 0.29
Nodes (3): ReviewPage, DocumentPreviewWidget, HumanDecision

### Community 15 - "Settings & Config Tests"
Cohesion: 0.31
Nodes (4): Settings, test_defaults_do_not_require_env(), test_google_client_path_resolves_against_project_root(), test_storage_paths()

### Community 17 - "Initial Lab Category Config"
Cohesion: 0.18
Nodes (10): category, display_name, prompts, evaluation, generation, system, references, min_count (+2 more)

### Community 18 - "Formatting & Layout Config"
Cohesion: 0.18
Nodes (11): formatting, citation_style, font, font_size, heading_numbering, line_spacing, margins_inches, bottom (+3 more)

### Community 19 - "Lab Sections Schema"
Cohesion: 0.20
Nodes (10): max, min, max, min, max, min, apparatus, discussion (+2 more)

### Community 23 - "Rubric Entry Schema"
Cohesion: 0.50
Nodes (4): rubric, description, id, weight

### Community 24 - "Word Limits Schema"
Cohesion: 0.50
Nodes (4): max, min, word_limits, total

### Community 25 - "Calculations Section Limits"
Cohesion: 0.67
Nodes (3): max, min, calculations

### Community 26 - "Conclusion Section Limits"
Cohesion: 0.67
Nodes (3): max, min, conclusion

### Community 27 - "Objective Section Limits"
Cohesion: 0.67
Nodes (3): max, min, objective

### Community 28 - "Observations Section Limits"
Cohesion: 0.67
Nodes (3): max, min, observations

### Community 29 - "Procedure Section Limits"
Cohesion: 0.67
Nodes (3): max, min, procedure

### Community 30 - "RAG Config"
Cohesion: 0.67
Nodes (3): rag, collections, enabled

### Community 31 - "References Section Limits"
Cohesion: 0.67
Nodes (3): max, min, references

## Knowledge Gaps
- **7 isolated node(s):** `academic-ai`, `Google Classroom Course and Assignment Fetching`, `MockProvider`, `Gemini Model Resolution and Fallback Chain`, `Tesseract OCR Fallback for Scanned PDFs` (+2 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 218 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `HomePage` connect `Home Page & Preferences` to `Database & Repositories`, `App Shell & Workflow Worker`, `Desktop UI Widgets`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `ReportContent` (e.g. with `Evaluator` and `SectionGenerator`) actually correct?**
  _`ReportContent` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `academic-ai`, `Google Classroom Course and Assignment Fetching`, `MockProvider` to the rest of the system?**
  _7 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Workflow Orchestration Core` be split into smaller, more focused modules?**
  _Cohesion score 0.0696969696969697 - nodes in this community are weakly interconnected._
- **Why does `MainWindow` connect `App Shell & Workflow Worker` to `Google API Integrations`, `Home Page & Preferences`, `Application Entrypoint & LLM`, `Desktop UI Widgets`, `Review & Edit Page`, `Processing Progress Page`, `Settings Page`, `Resume & Review Handlers`, `History Page`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `LLMProvider` (e.g. with `Classifier` and `Evaluator`) actually correct?**
  _`LLMProvider` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Should `Google API Integrations` be split into smaller, more focused modules?**
  _Cohesion score 0.05868544600938967 - nodes in this community are weakly interconnected._