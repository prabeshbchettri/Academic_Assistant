# 06 — Graphify Project Knowledge Graph

> Read-only. This document explains how the repository knowledge graph was produced, what it contains, how to read it, and where its limits are. The canonical machine artifacts are copied to `docs/project_audit/graphify/`; the originals remain in `graphify-out/`.

## 1. What Graphify produced

A persistent, queryable knowledge graph of the repository containing:

- **Code structure** from AST extraction (files, classes, functions, imports, inheritance, calls).
- **Semantic concepts** from documentation, prompts, templates, and prose, extracted by an LLM.
- **Community structure** (Leiden clustering) and **god nodes** (highest-degree hubs).
- **Hypergraphs** for relationships that span more than two nodes.
- **Surprising connections** (semantically related but structurally distant).
- **Confidence labels** on every edge: `EXTRACTED`, `INFERRED`, or `AMBIGUOUS`.

## 2. How it was run

| Step | Detail |
|---|---|
| Tool | `graphify` (installed via `uv tool`, package `graphifyy`) |
| Interpreter | `C:\Users\LENOVO\AppData\Roaming\uv\tools\graphifyy\Scripts\python.exe` (recorded in `graphify-out/.graphify_python`) |
| Mode | **Incremental update** (`--update`) because a graph already existed |
| Base vs HEAD | Built at commit `f5dd993e`; repository HEAD was `96a14403` |
| Changed files detected | **57** — 37 code, 19 docs, 1 image |
| Semantic LLM | **Host-agent subagents** (no `GEMINI_API_KEY`/`GOOGLE_API_KEY` in the environment) |
| Semantic chunks | **2** parallel `general` subagents |
| Outputs | `graphify-out/graph.json`, `graph.html`, `GRAPH_REPORT.md`, `manifest.json`, `cost.json`, `.graphify_labels.json` |

### Pipeline stages executed

1. **Detect** changed files (`detect_incremental`).
2. **AST extract** changed code → nodes/edges.
3. **Semantic extract** 2 chunks of docs/prompts/templates → concept nodes and edges.
4. **Coverage check** against the manifest (128 corpus files).
5. **Cache save** per chunk.
6. **Merge** AST + semantic fragments into the full graph.
7. **Build merge** (multi-file `build_merge`).
8. **Cluster** (Leiden) → 79 communities.
9. **Label** communities (`.graphify_labels.json`).
10. **Serialize** with `to_json(..., force=True)` (see §8 on the shrink guard).
11. **Report** → `GRAPH_REPORT.md`; **visualize** → `graph.html`; **cost** → `cost.json`.

## 3. Corpus and extraction statistics

| Metric | Value |
|---|---|
| Corpus files | **128** |
| Corpus words | **70,656** |
| AST nodes | 561 |
| AST edges | 1,443 |
| Semantic nodes | 114 (74 + 40) |
| Semantic edges | 197 (127 + 70) |
| Semantic hyperedges | 6 |
| **Final graph nodes** | **1,153** |
| **Final graph edges** | **2,664** |
| **Communities** | **79** |
| Edge provenance | **89% EXTRACTED**, **11% INFERRED**, **0% AMBIGUOUS** |
| Inferred edges | 288, average confidence **0.90** |
| Hyperedges | **8** |
| Surprising connections | **5** |
| Isolated nodes | **23** |
| Thin communities | **21** |
| Import cycles | **0** |

## 4. God nodes (highest degree)

| Node | Degree | Interpretation |
|---|---|---|
| `MockProvider` | 42 | Offline/test provider touched by many modules and tests |
| `ReportContent` | 42 | Central data contract across AI, workflow, exporters |
| `LLMProvider` | 39 | The AI abstraction every provider and consumer depends on |
| `NvidiaProvider` | 30 | Production provider hub |
| `HomePage` | 28 | Main UI entry surface |
| `SectionGenerator` | 28 | Core generation engine |
| `DocxGenerator` | 28 | DOCX export hub |
| `Citation` | 28 | Shared citation model |
| `MainWindow` | 27 | UI composition root |
| `Evaluator` | 24 | Quality gate |

These hubs confirm the architecture described in `04_FILE_DEPENDENCY_MAP.md`: the provider interface, the report contract, and the generation/evaluation/export core are the load-bearing parts of the system.

## 5. Community structure

- **79 communities** total; **21 are thin** (small clusters of docs/assets).
- Large communities correspond to recognizable subsystems:
  - AI provider / LLM layer (`LLMProvider`, `NvidiaProvider`, `MockProvider`, factory, settings)
  - Workflow pipeline (graph, nodes, routing, state, checkpointer)
  - Document generation (LaTeX generator/template, DOCX generator, PDF exporter)
  - UI (main window, pages, widgets, workers)
  - Rules/config (YAML configs, schema, prompts)
  - Domain models (`ReportContent`, `Citation`, `EvaluationResult`)
  - Integrations (Google auth, Classroom, Gmail, file parsers)
  - Tests and documentation clusters
- Community labels are stored in `graphify-out/.graphify_labels.json`; the interactive `graph.html` colors nodes by community.

## 6. Hyperedges and surprising connections

- **8 hyperedges** capture multi-node relationships (for example, the generation path spanning `SectionGenerator`, prompt files, config, and `LLMProvider`; and the export path spanning `ReportContent`, both exporters, and the PDF engine).
- **5 surprising connections** link semantically related but structurally distant nodes — useful for finding undocumented coupling. Inspect them in `GRAPH_REPORT.md` or `graph.html`.
- **23 isolated nodes** are mostly assets/templates/docs with no semantic or import edge (e.g. logo, empty templates, `.gitkeep`-style placeholders). Isolated ≠ unused; several are referenced dynamically (template paths, assets).

## 7. Health check

- **0 import cycles** — the dependency graph is acyclic.
- **0 dangling edges / 0 missing endpoints** — all edges resolve.
- **2 self-loop edges** — nodes with an edge to themselves; benign, but flagged by the health check.
- No critical structural problems reported.

## 8. Shrink guard and node-ID churn (important)

During serialization the anti-shrink guard tripped. Cause: **semantic node IDs are derived from slugs**, and the re-extracted docs produced slightly different slugs than the previous build (for example an old `ai_prompts_assignment_evaluation_prompt` vs a new `..._eval_prompt`). The guard interpreted the ID change as a large node-count drop.

Resolution: the graph was written with `to_json(..., force=True)`. **No real data was lost** — node/edge counts increased (the final graph has 1,153 nodes and 2,664 edges). This is an **ID-churn artifact**, not a data-loss event, and is recorded here so future incremental updates are interpreted correctly.

## 9. Known limitations (reported by Graphify)

| Limitation | Detail | Impact |
|---|---|---|
| No semantic API key | Host-agent extraction used instead of Gemini | Semantic coverage is subagent-driven; acceptable but not identical to the Gemini path |
| `document/assets/tu_logo.png` | Image coverage flagged **partial** (line-based coverage N/A) | Asset is referenced but not semantically described |
| `document/templates/academic_base.docx` | Office conversion failed (needs `pip install graphifyy[office]`) | Empty/unused file; no impact |
| `names.java`, `names1.java` | AST syntax errors (they contain prompt prose, not Java) | Zero symbols extracted; correctly treated as prose duplicates |
| `ai/__init__.py`, `ai/llm/__init__.py`, `pyproject.toml` | No symbols | Expected for empty inits; `pyproject.toml` is config, not code |
| ID churn | See §8 | Serialization needed `force=True` |

## 10. How to read confidence labels

- **EXTRACTED** — directly observed by AST or explicitly stated in text. Trust as structural fact.
- **INFERRED** — a semantic relationship inferred by the LLM (e.g. "this module implements that concept"). Useful for discovery; verify before acting.
- **AMBIGUOUS** — none in this graph (0%).

Rule of thumb: use the graph to **find** candidates, then confirm in code. The manually verified relationships in docs `02`–`04` are the ground truth.

## 11. Querying the graph

From the repository root (adjust the interpreter if needed):

```powershell
# Show god nodes / summary
& "C:\Users\LENOVO\AppData\Roaming\uv\tools\graphifyy\Scripts\python.exe" -m graphify query "what depends on ReportContent?"

# Shortest path between two concepts
& "C:\Users\LENOVO\AppData\Roaming\uv\tools\graphifyy\Scripts\python.exe" -m graphify path "SectionGenerator" "NvidiaProvider"

# Explain a node
& "C:\Users\LENOVO\AppData\Roaming\uv\tools\graphifyy\Scripts\python.exe" -m graphify explain "LLMProvider"
```

(If the module entry point differs, use the `graphify` executable in the same `Scripts` directory. Open `graph.html` in a browser for interactive exploration.)

## 12. Artifact locations

| Artifact | Original | Copy in audit folder |
|---|---|---|
| Machine graph | `graphify-out/graph.json` | `docs/project_audit/graphify/graph.json` |
| Interactive viewer | `graphify-out/graph.html` | `docs/project_audit/graphify/graph.html` |
| Human report | `graphify-out/GRAPH_REPORT.md` | `docs/project_audit/graphify/GRAPH_REPORT.md` |
| Corpus manifest | `graphify-out/manifest.json` | — |
| Community labels | `graphify-out/.graphify_labels.json` | — |
| Cost log | `graphify-out/cost.json` | — |

## 13. Cross-check against manual verification

The graph agrees with the manually verified wiring:

- Prompt files → `SectionGenerator` / `Evaluator` (matches `ai/generator.py`, `ai/evaluator.py`).
- `report.tex.j2` → `LatexGenerator` → PDF exporter (matches `document/latex_generator.py`, `document/pdf_exporter.py`).
- `LLMProvider` → `NvidiaProvider` / `MockProvider` (matches `ai/llm/factory.py`).
- Workflow nodes → `workflow/graph.py` (11 nodes, two conditional edges).

Where the graph is **INFERRED** (e.g. semantic similarity among prompts), the manual audit in `02_PROMPT_AND_INSTRUCTION_AUDIT.md` is authoritative.
