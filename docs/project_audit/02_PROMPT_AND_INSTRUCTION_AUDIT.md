# 02 — Prompt and Instruction Audit

> Read-only. No prompt file was modified. Relationships marked **VERIFIED** were confirmed by reading the loader code; **INFERRED** relationships come from Graphify or documentation and are labelled as such.

## 1. How prompts are wired (VERIFIED)

Prompts are **file-based** and **category-bound through YAML**. There is no prompt registry or version table.

```
configs/{assignment,initial_lab,final_lab}.yaml
        └─ prompts: {system, generation, evaluation}   ← repo-relative paths
                 │
                 ├─ ai/generator.py::generate_section()
                 │     root_dir = Path(__file__).resolve().parent.parent   (project root)
                 │     system_prompt      = read(root_dir / config.prompts.system)
                 │     generation_template = read(root_dir / config.prompts.generation)
                 │     → jinja2 Template.render(...) → llm.generate_structured(SectionDraft, ...)
                 │
                 └─ ai/evaluator.py::evaluate_semantic()
                       eval_template = read(root_dir / config.prompts.evaluation)
                       → Template.render(section_heading, body_markdown, rubric_text, min_words, max_words)
                       → llm.generate_structured(EvaluationResult, "You are an evaluator.", prompt)
```

Verified facts:

- `ai/generator.py:116-129` loads `config.prompts.system` and `config.prompts.generation`; missing files silently fall back to `"You are an academic assistant."` / `"{{ assignment_text }}"`.
- `ai/evaluator.py:173-175` loads `config.prompts.evaluation`; missing file silently falls back to `"Evaluate: {{ body_markdown }}"`.
- `ai/evaluator.py:198` uses a **hard-coded** system prompt `"You are an evaluator."` — the `.txt` evaluation file is the *user* prompt template, not the system prompt.
- Prompt paths are resolved against the **project root** (`Path(__file__).parent.parent`), not against `configs/`. The YAML values are therefore written as `ai/prompts/...`.
- `configs/schema.py:45-49` requires all three keys (`system`, `generation`, `evaluation`) on every category; `PromptsConfig` forbids extra keys.

## 2. Standalone prompt files

| No. | File | Purpose | Consumer (agent/model) | Loaded by | Changing it changes AI output? | Dependencies |
|---|---|---|---|---|---|---|
| 1 | `ai/prompts/assignment_system.txt` | System persona/rules for academic assignments. | `SectionGenerator` → configured `LLMProvider` (NVIDIA NIM by default; Mock offline) | `ai/generator.py:117` via `configs/assignment.yaml` | **Yes** — system-level tone, constraints, schema behavior | `configs/assignment.yaml` (`prompts.system`) |
| 2 | `ai/prompts/assignment_generation.txt` | Jinja2 user-prompt template for each section. | `SectionGenerator` | `ai/generator.py:118` | **Yes** — section content, placeholders, word targets | `configs/assignment.yaml`; `ai/generator.py` render variables |
| 3 | `ai/prompts/assignment_evaluation.txt` | Jinja2 evaluation template (rubric scoring). | `Evaluator` | `ai/evaluator.py:174` | **Yes** — pass/fail, scores, feedback | `configs/assignment.yaml`; `models/evaluation.py` schema |
| 4 | `ai/prompts/initial_lab_system.txt` | System persona for initial lab reports. | `SectionGenerator` | `ai/generator.py:117` via `configs/initial_lab.yaml` | **Yes** | `configs/initial_lab.yaml` |
| 5 | `ai/prompts/initial_lab_generation.txt` | Initial-lab section template. | `SectionGenerator` | `ai/generator.py:118` | **Yes** | `configs/initial_lab.yaml` |
| 6 | `ai/prompts/initial_lab_evaluation.txt` | Initial-lab evaluation template. | `Evaluator` | `ai/evaluator.py:174` | **Yes** | `configs/initial_lab.yaml` |
| 7 | `ai/prompts/final_lab_system.txt` | System persona for final lab reports (IEEE/structured schema). | `SectionGenerator` | `ai/generator.py:117` via `configs/final_lab.yaml` | **Yes** | `configs/final_lab.yaml` |
| 8 | `ai/prompts/final_lab_generation.txt` | Final-lab section template. | `SectionGenerator` | `ai/generator.py:118` | **Yes** | `configs/final_lab.yaml` |
| 9 | `ai/prompts/final_lab_evaluation.txt` | Final-lab evaluation template. | `Evaluator` | `ai/evaluator.py:174` | **Yes** | `configs/final_lab.yaml` |

### Template variables (VERIFIED from `ai/generator.py:146-162`)

`assignment_generation.txt` may use: `title`, `course`, `assignment_text`, `section_heading`, `min_words`, `max_words`, `calculated_data`, `references_context`, `user_provided_data`, `prior_sections_summary`, `feedback`, `document_type`, `format_notes`, `assignment_notes`, `revision_feedback`.

### Template variables (VERIFIED from `ai/evaluator.py:189-195`)

`*_evaluation.txt` may use: `section_heading`, `body_markdown`, `rubric_text`, `min_words`, `max_words`.

## 3. Embedded prompts (not standalone files)

| Location | Prompt | Consumer | Output impact | Notes |
|---|---|---|---|---|
| `ai/classifier.py:94-97` | `"You are an academic classifier. Classify ... 'assignment', 'initial_lab', 'final_lab'..."` | `Classifier` → `LLMProvider` | **Yes** — category choice (only when rule confidence < 0.85) | Not configurable; embedded in code |
| `ai/evaluator.py:198` | `"You are an evaluator."` | `Evaluator` → `LLMProvider` | Yes — sets evaluator role | Hard-coded system prompt; evaluation `.txt` is the user prompt |

## 4. Duplicate / misnamed instruction files

| File | Finding | Verified by |
|---|---|---|
| `names.java` | Not Java. Contains the prompt "ROLE: Senior AI Engineer & Software Architect..." (an AI-audit instruction). | File read; byte size 10.6 KB |
| `names1.java` | **Byte-identical** to `names.java` (SHA-256 match). | `Get-FileHash` comparison |
| `plan.md` | Contains prompt-engineering conventions (placeholder convention, injection defense) but is a plan document, not a runtime prompt. | Manual read |
| `docs/*` | Describe prompt architecture; not loaded at runtime. | Manual read |

Graphify could not AST-parse `names.java`/`names1.java` (reported syntax errors, zero symbols) because they are prose with a `.java` extension. This is a tool limitation, not a code defect.

## 5. Prompt safety and data handling (VERIFIED)

- `ai/security.py::wrap_untrusted_data` wraps external text in randomized delimiters and calls `sanitize_external_input`, which caps input at 100,000 chars and redacts three literal injection phrases.
- `ai/generator.py:136-138` wraps `normalized.cleaned_text` and `user_provided_data` before insertion into the generation template.
- `ai/classifier.py:93` wraps the first 3,000 chars before LLM classification.
- **Gap:** the redaction list is a short literal regex; paraphrased injection is not caught. Documented in `docs/08_TECHNICAL_DEBT_AND_IMPROVEMENTS.md` §5.3.

## 6. Model / provider context (VERIFIED)

- `ai/llm/factory.py::build_llm_provider` returns `MockProvider` when `use_mock=True` or `NVIDIA_API_KEY` is empty; otherwise `NvidiaProvider`.
- `GeminiProvider` (`ai/llm/gemini.py`) still exists but is **not selected** by the factory. `README.md`, `docs/STUDENT_GUIDE.md`, and parts of `docs/08` still describe Gemini — a documentation drift relative to the NVIDIA migration.
- `.env.example` and `app/settings.py` define NVIDIA settings (`NVIDIA_MODEL`, `NVIDIA_FALLBACK_MODEL`, embedding model, etc.).

## 7. Observations that affect prompt changes

1. **No prompt versioning/trace.** Prompts are read at call time; no hash/model is stored with the report. A generated report cannot be reproduced against the prompt that produced it. (Documented in `docs/08` §4.4.)
2. **Silent fallback prompts.** If a prompt file is missing, generation/evaluation continue with a generic fallback rather than failing. Editing or moving a prompt can silently degrade output.
3. **Preference injection gap.** `ai/generator.py` reads `document_preferences`, `format_notes`, `assignment_notes`, and `revision_feedback` from `normalized.metadata`; whether the UI actually populates these is a separate integration question (see `docs/08`).
4. **Two Markdown/output contracts.** Generation prompt output must satisfy `models/report.py::SectionDraft`; evaluation output must satisfy `models/evaluation.py::EvaluationResult` (fail-safe INCONCLUSIVE default).
5. **Rubric coupling.** Evaluation templates receive `rubric_text` rendered from `configs/*.yaml::rubric`; changing rubric weights without changing the evaluation prompt can misalign scoring.

## 8. Graphify cross-reference (machine-derived, not all verified)

Graphify extracted prompt nodes and edges (see `06_GRAPHIFY_PROJECT_KNOWLEDGE_GRAPH.md`):

- **EXTRACTED (1.0):** each `*_evaluation.txt` → `docs/05_AI_ENGINEERING_ARCHITECTURE.md` "Evaluator"; each `*_generation.txt` → "Prompt Architecture"; each `*_system.txt` → `plan.md` placeholder/injection concepts.
- **INFERRED (0.95):** `SectionGenerator` → `assignment_generation.txt` (matches the verified code path).
- **INFERRED (0.75–0.85):** semantic similarity among the three generation prompts and among evaluation prompts.

The Graphify edges corroborate, but do not replace, the verified loader trace in Section 1.
