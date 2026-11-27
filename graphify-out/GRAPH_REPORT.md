# Graph Report - Academic_Assistent  (2026-11-26)

## Corpus Check
- 94 files · ~28,464 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 16 file(s) not represented in the graph (top: (none) 11, .example 1, .qss 1)

## Summary
- 839 nodes · 2054 edges · 52 communities (39 shown, 13 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 238 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f5dd993e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Workflow Orchestration Core
- Google API Integrations
- Document Parsing & Normalization
- Database & Repositories
- Report Generation & Export
- Architecture Docs & Concepts
- Home Page & Preferences
- Assignment Category Config
- CategoryConfig
- formatting
- sections
- App Shell & Workflow Worker
- re
- Review & Edit Page
- settings.py
- Processing Progress Page
- Initial Lab Category Config
- Formatting & Layout Config
- Lab Sections Schema
- preferences.py
- Tech Stack — Academic AI (`academic-ai`)
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
- test_classroom_client.py
- final_lab.yaml
- prompts
- rubric
- word_limits
- apparatus
- conclusion
- error_analysis
- experimental_data
- introduction
- results_and_discussion
- theory

## God Nodes (most connected - your core abstractions)
1. `ReportContent` - 36 edges
2. `LLMProvider` - 34 edges
3. `MockProvider` - 29 edges
4. `CategoryConfig` - 29 edges
5. `MainWindow` - 29 edges
6. `WorkflowState` - 28 edges
7. `HomePage` - 28 edges
8. `AssignmentRepository` - 27 edges
9. `build_academic_workflow()` - 26 edges
10. `DocxGenerator` - 25 edges

## Surprising Connections (you probably didn't know these)
- `7. Document Pipeline (cross-cutting)` --references--> `DocxGenerator`  [INFERRED]
  TECH_STACK.md → document/docx_generator.py
- `Tech Stack — Academic AI (`academic-ai`)` --references--> `ReportContent`  [INFERRED]
  TECH_STACK.md → models/report.py
- `Tech Stack — Academic AI (`academic-ai`)` --references--> `LLMProvider`  [INFERRED]
  TECH_STACK.md → ai/llm/base.py
- `Tech Stack — Academic AI (`academic-ai`)` --references--> `MainWindow`  [INFERRED]
  TECH_STACK.md → app/ui/main_window.py
- `Tech Stack — Academic AI (`academic-ai`)` --references--> `HomePage`  [INFERRED]
  TECH_STACK.md → app/ui/pages/home_page.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Per-Category System/Generation/Evaluation Prompt Sets** — ai_prompts_assignment_system_prompt, ai_prompts_assignment_generation_prompt, ai_prompts_assignment_evaluation_prompt, ai_prompts_initial_lab_system_prompt, ai_prompts_initial_lab_generation_prompt, ai_prompts_initial_lab_evaluation_prompt, ai_prompts_final_lab_system_prompt, ai_prompts_final_lab_generation_prompt, ai_prompts_final_lab_evaluation_prompt [EXTRACTED 1.00]
- **Academic Integrity Guardrails** — plan_missing_info_placeholder, plan_prompt_injection_defense, plan_safe_ast_calculations, plan_human_in_the_loop [INFERRED 0.85]
- **Generate-Evaluate-Retry-Review Loop** — plan_langgraph_workflow, plan_retry_policy, plan_deterministic_checks, plan_semantic_evaluation, plan_human_in_the_loop [INFERRED 0.95]

## Communities (52 total, 13 thin omitted)

### Community 0 - "Workflow Orchestration Core"
Cohesion: 0.07
Nodes (34): Classifier, Evaluator, LLMProvider, GeminiProvider, MockProvider, ClassroomCoursesWorker, WorkflowWorker, Category (+26 more)

### Community 1 - "Google API Integrations"
Cohesion: 0.06
Nodes (21): InputPage, SettingsPage, build_classroom_service(), download_drive_file(), list_courses(), list_coursework(), list_coursework_materials(), build_gmail_service() (+13 more)

### Community 2 - "Document Parsing & Normalization"
Cohesion: 0.12
Nodes (9): BaseFileParser, ParsedDocument, DocxParser, FileTooLargeError, UnsupportedFileError, perform_ocr_if_needed(), PdfParser, TextParser (+1 more)

### Community 3 - "Database & Repositories"
Cohesion: 0.08
Nodes (32): configure_logging(), main(), run_cli_generation(), get_db_path(), get_engine(), get_session(), init_db(), run_migrations() (+24 more)

### Community 4 - "Report Generation & Export"
Cohesion: 0.08
Nodes (26): SectionGenerator, escape_latex(), sanitize_math(), _inline(), _is_table_separator(), LatexGenerator, markdown_to_latex(), close_list() (+18 more)

### Community 5 - "Architecture Docs & Concepts"
Cohesion: 0.05
Nodes (47): Assignment Section Evaluation Prompt, Assignment Section Generation Prompt, Assignment System Prompt, [1], [2] Numbered Citation Convention, Final Lab Section Evaluation Prompt, Final Lab Section Generation Prompt, IEEE Style and Structured Schema Requirement, Final Lab System Prompt (+39 more)

### Community 7 - "Assignment Category Config"
Cohesion: 0.04
Nodes (48): max, min, category, max, min, display_name, formatting, citation_style (+40 more)

### Community 8 - "CategoryConfig"
Cohesion: 0.10
Nodes (14): CategoryConfig, FormattingConfig, load_category_config(), MarginConfig, preload_all_configs(), PromptsConfig, RagCategoryConfig, RangeLimit (+6 more)

### Community 9 - "formatting"
Cohesion: 0.18
Nodes (11): formatting, citation_style, font, font_size, heading_numbering, line_spacing, margins_inches, bottom (+3 more)

### Community 10 - "sections"
Cohesion: 0.20
Nodes (10): max, min, max, min, max, min, abstract, methodology (+2 more)

### Community 12 - "re"
Cohesion: 0.10
Nodes (17): evaluate_arithmetic(), extract_and_evaluate_formulas(), safe_eval(), UnsafeExpressionError, sanitize_external_input(), wrap_untrusted_data(), add_markdown_paragraph(), format_inline_markdown() (+9 more)

### Community 14 - "Review & Edit Page"
Cohesion: 0.16
Nodes (4): ReviewPage, DocumentPreviewWidget, SectionEditorWidget, HumanDecision

### Community 15 - "settings.py"
Cohesion: 0.13
Nodes (8): chunk_text(), RagRetriever, Settings, test_defaults_do_not_require_env(), test_google_client_path_resolves_against_project_root(), test_storage_paths(), test_chunking(), test_rag_index_and_retrieve()

### Community 17 - "Initial Lab Category Config"
Cohesion: 0.18
Nodes (10): category, display_name, prompts, evaluation, generation, system, references, min_count (+2 more)

### Community 18 - "Formatting & Layout Config"
Cohesion: 0.18
Nodes (11): formatting, citation_style, font, font_size, heading_numbering, line_spacing, margins_inches, bottom (+3 more)

### Community 19 - "Lab Sections Schema"
Cohesion: 0.20
Nodes (10): max, min, max, min, max, min, apparatus, discussion (+2 more)

### Community 20 - "preferences.py"
Cohesion: 0.34
Nodes (12): AppPreferences, category_for_document_type(), DocumentDefaults, is_profile_complete(), load_preferences(), preferences_path(), save_preferences(), StudentProfile (+4 more)

### Community 21 - "Tech Stack — Academic AI (`academic-ai`)"
Cohesion: 0.15
Nodes (12): 2. Backend (Orchestration & Domain Layer), 3. Database and Storage, 5. Infrastructure and DevOps, 6. Development Tools, 7. Document Pipeline (cross-cutting), 8. Unused / Misleading Items, 9. Summary by Layer, Authorization model (+4 more)

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

### Community 39 - "test_classroom_client.py"
Cohesion: 0.29
Nodes (4): _CoursesResource, _Request, _Service, test_list_courses_paginates()

### Community 40 - "final_lab.yaml"
Cohesion: 0.20
Nodes (9): category, display_name, rag, collections, enabled, references, min_count, required (+1 more)

### Community 41 - "prompts"
Cohesion: 0.50
Nodes (4): prompts, evaluation, generation, system

### Community 42 - "rubric"
Cohesion: 0.50
Nodes (4): rubric, description, id, weight

### Community 43 - "word_limits"
Cohesion: 0.50
Nodes (4): max, min, word_limits, total

### Community 44 - "apparatus"
Cohesion: 0.67
Nodes (3): max, min, apparatus

### Community 45 - "conclusion"
Cohesion: 0.67
Nodes (3): max, min, conclusion

### Community 46 - "error_analysis"
Cohesion: 0.67
Nodes (3): max, min, error_analysis

### Community 47 - "experimental_data"
Cohesion: 0.67
Nodes (3): max, min, experimental_data

### Community 48 - "introduction"
Cohesion: 0.67
Nodes (3): max, min, introduction

### Community 49 - "results_and_discussion"
Cohesion: 0.67
Nodes (3): max, min, results_and_discussion

### Community 50 - "theory"
Cohesion: 0.67
Nodes (3): theory, max, min

## Knowledge Gaps
- **7 isolated node(s):** `academic-ai`, `MockProvider`, `Phased Delivery Plan (0-9)`, `Gemini Model Resolution and Fallback Chain`, `Tesseract OCR Fallback for Scanned PDFs` (+2 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 228 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `HomePage` connect `Home Page & Preferences` to `Workflow Orchestration Core`, `Database & Repositories`, `App Shell & Workflow Worker`, `Desktop UI Widgets`, `Tech Stack — Academic AI (`academic-ai`)`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `ReportContent` (e.g. with `Evaluator` and `SectionGenerator`) actually correct?**
  _`ReportContent` has 11 INFERRED edges - model-reasoned connections that need verification._
- **What connects `academic-ai`, `MockProvider`, `Phased Delivery Plan (0-9)` to the rest of the system?**
  _7 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Workflow Orchestration Core` be split into smaller, more focused modules?**
  _Cohesion score 0.06776315789473684 - nodes in this community are weakly interconnected._
- **Why does `ReportContent` connect `Report Generation & Export` to `Workflow Orchestration Core`, `CategoryConfig`, `Desktop UI Widgets`, `Review & Edit Page`, `Tech Stack — Academic AI (`academic-ai`)`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `LLMProvider` (e.g. with `Classifier` and `Evaluator`) actually correct?**
  _`LLMProvider` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Should `Google API Integrations` be split into smaller, more focused modules?**
  _Cohesion score 0.0642243328810493 - nodes in this community are weakly interconnected._