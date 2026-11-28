# 03 — LaTeX and Document-Formatting Audit

> Read-only. No template, style, or generator file was modified.
> This document explains **where assignment/report formatting is actually controlled** and separates *content* files from *appearance* files.

## 1. Formatting control map

| Layer | File(s) | What it controls | Verified how |
|---|---|---|---|
| PDF page layout & typography | `document/templates/latex/report.tex.j2` | Page size, margins, font, spacing, heading styles, header/footer, TOC, front page, tables, bibliography | Template read in full (237 lines) |
| LaTeX rendering / data binding | `document/latex_generator.py` | Which template is loaded; Markdown→LaTeX; escaping; variable injection | Code read |
| LaTeX text safety | `document/latex_escape.py` | Escapes TeX specials; sanitizes math | Code read |
| DOCX page layout & typography | `document/docx_generator.py` | Margins, styles, headers/footers, TOC, front page, tables — **driven by YAML `formatting`** | Code read |
| DOCX Markdown conversion | `document/markdown_to_docx.py` | Inline/paragraph Markdown subset | Code read |
| PDF compilation | `document/pdf_exporter.py` | Tectonic → XeLaTeX → LibreOffice fallback; metadata | Code read |
| Per-category rules | `configs/assignment.yaml`, `configs/initial_lab.yaml`, `configs/final_lab.yaml` | Required sections, word limits, `formatting` block, rubric, references | YAML read |
| Config validation | `configs/schema.py` | Enforces `FormattingConfig`, `WordLimits`, `RubricItem` shapes | Code read |
| Content data model | `models/report.py` | `ReportContent`, `SectionDraft`, `TableData`, `FigureData`, `FrontPage` | Code read |
| Front-page logo asset | `document/assets/tu_logo.png` | Logo rendered on LaTeX title page; path resolved in `models/report.py` and `app/preferences.py` | Code + grep |

## 2. LaTeX template — what each region controls

`document/templates/latex/report.tex.j2` (Jinja2 with LaTeX-safe delimiters `\VAR{}` / `\BLOCK{}`):

| Lines | Region | Formatting responsibility |
|---|---|---|
| 1–2 | Document class | `article`, **12 pt**, **A4** |
| 4–11 | Fonts (XeLaTeX) | `fontspec`; main font **Times New Roman**, mono **Liberation Mono** |
| 13–18 | Page layout | `geometry`: top/bottom **1 in**, left **1.25 in**, right **1 in**, headheight 15 pt |
| 20–22 | Line spacing | `setspace` with `\setstretch{1.25}` |
| 24–34 | Packages | math, `booktabs`/`tabularx`/`longtable` tables, `graphicx`, captions, floats, lists, color, microtype |
| 36–40 | Colors | `ioeblue` (27,54,93), `ioegold` (180,145,80), `textgray`, `linkblue` |
| 42–51 | Hyperlinks | `hyperref` colors and PDF bookmarks |
| 53–68 | Section styling | `titlesec`: section/subsection sizes, IOE blue, gold rule under sections, spacing |
| 70–73 | Paragraph style | `\parindent=0`, `\parskip=0.5em`, `emergencystretch` |
| 75–77 | List style | compact `itemize`/`enumerate` |
| 79–96 | Header / footer | `fancyhdr`: left header = course (or title), right header = title, **centered page number**, 0.4 pt head rule; `plain` style = page number only |
| 98–99 | TOC title | "Table of Contents" colored IOE blue |
| 104–171 | Front page | Optional `titlepage`: logo (2.1 cm), university/campus/department, gold rule, document type, title, subtitle, course, submitted-by/to two-column block, date |
| 172–182 | Simple title block | Fallback when no `front_page` |
| 184–193 | Abstract | Centered 0.88-width minipage, italic |
| 195–199 | Table of contents | Optional (`include_toc`) |
| 201–224 | Body + tables | `\section{heading}` then `body_latex`; `tabularx` full-width tables with booktabs rules |
| 226–235 | References | Manual `thebibliography` block (IEEE-like numbered list); **no BibTeX** |

### Content vs. appearance

- **Content** comes from `ReportContent` (`models/report.py`): title, course, author, abstract, sections (`heading`, `body_markdown`), tables, references, front-page fields.
- **Appearance** is decided by `report.tex.j2` (PDF) and `docx_generator.py` (DOCX), not by the AI prompts.
- The AI prompts decide *what text* is produced; the templates decide *how it is laid out*.

## 3. Important verified finding — LaTeX ignores YAML `formatting`

`document/latex_generator.py::render(self, report)` takes **only** `ReportContent`; it never receives `CategoryConfig`. The YAML `formatting` block (`font`, `font_size`, `line_spacing`, `margins_inches`, `citation_style`, `heading_numbering`) is consumed by **`document/docx_generator.py`**, not by the LaTeX path.

Consequences (verified by code, corroborated by `docs/08` §3.6):

- PDF margins are hard-coded **left 1.25 in**, while DOCX margins come from YAML (default 1.0 in all sides).
- PDF line spacing is hard-coded **1.25**, while DOCX uses YAML `line_spacing` (default 1.15).
- PDF font is hard-coded **Times New Roman 12 pt**; DOCX font/size come from YAML.
- Editing `configs/*.yaml::formatting` changes **DOCX only**, not the PDF. This is a key place to inspect before changing formatting behavior.

## 4. DOCX formatting controls (verified)

`document/docx_generator.py`:

- `generate(report, config, assignment_id, version)` applies `config.formatting.margins_inches` to the section (lines 46–49).
- `_configure_styles(doc, config)` applies font, size, line spacing, heading numbering (line 135 onward).
- `_add_header_footer`, `_enable_field_updates`, `_add_front_page`, `_add_toc`, `_add_data_table`, `_add_field` build the document.
- It calls `docx.Document()` directly; the constructor accepts `template_path` but the default is `None` and the parameter is **not used** to load a base template. Therefore `document/templates/academic_base.docx` is a dead hook.
- Output path: `storage/outputs/<assignment_id>/v<version>/report.docx`.

## 5. PDF compilation controls (verified)

`document/pdf_exporter.py`:

1. Renders LaTeX via `LatexGenerator`.
2. Writes `report.tex` to the output directory.
3. Tries **Tectonic** (`_compile_with_tectonic`).
4. Falls back to **XeLaTeX/pdflatex** (`_compile_with_xelatex`, runs twice for TOC).
5. Falls back to **LibreOffice headless** converting the DOCX.
6. Writes `metadata.json` with title, version, created_at, docx/pdf paths, engine.

Engine selection comes from `app/settings.py` (`pdf_engine`, `pdf_fallback_engine`, `tectonic_path`).

## 6. LaTeX escaping and safety (verified)

`document/latex_escape.py`:

- `escape_latex(text)` escapes TeX special characters in regular text.
- `sanitize_math(formula)` sanitizes math formulas and blocks dangerous low-level TeX primitives.
- `LatexGenerator` applies `escape_latex` to headings, table captions/headers/cells, references, and every front-page field; body text goes through `markdown_to_latex` then escaping rules.

**Observed risk (documented in `docs/08` §5.4):** `front_page.logo_path` is inserted into `\includegraphics` after only replacing backslashes (line 271); an absolute path with spaces, `#`, `%`, or Unicode can break compilation or inject TeX. The template wraps it in `\IfFileExists` but does not sanitize the path itself.

## 7. LaTeX / document-formatting file inventory

| No. | File | Type | Role | Status |
|---|---|---|---|---|
| 1 | `document/templates/latex/report.tex.j2` | Jinja2/LaTeX | **Primary report layout** | Active, used by `LatexGenerator` |
| 2 | `document/templates/latex/references.bib.j2` | Jinja2/BibTeX | Bibliography template | **Empty (0 bytes), unused** |
| 3 | `document/templates/academic_base.docx` | DOCX | Base DOCX template | **Empty (0 bytes), unused** |
| 4 | `document/assets/tu_logo.png` | PNG | Front-page logo | Active (LaTeX + preferences) |
| 5 | `document/latex_generator.py` | Python | Template loader + Markdown→LaTeX | Active |
| 6 | `document/latex_escape.py` | Python | TeX escaping/sanitization | Active |
| 7 | `document/docx_generator.py` | Python | DOCX layout engine | Active |
| 8 | `document/markdown_to_docx.py` | Python | Markdown→DOCX | Active |
| 9 | `document/pdf_exporter.py` | Python | PDF engine fallback | Active |
| 10 | `configs/assignment.yaml` | YAML | `formatting` block for assignments | Active (DOCX) |
| 11 | `configs/initial_lab.yaml` | YAML | `formatting` block for initial labs | Active (DOCX) |
| 12 | `configs/final_lab.yaml` | YAML | `formatting` block for final labs | Active (DOCX) |
| 13 | `configs/schema.py` | Python | Validates formatting schema | Active |

## 8. Document-generation file inventory

| File | Responsibility |
|---|---|
| `document/docx_generator.py` | Build DOCX from `ReportContent` + `CategoryConfig` |
| `document/markdown_to_docx.py` | Convert Markdown subset to DOCX runs/paragraphs |
| `document/latex_generator.py` | Render `ReportContent` through `report.tex.j2` |
| `document/latex_escape.py` | Escape TeX / sanitize math |
| `document/pdf_exporter.py` | Compile PDF via Tectonic/XeLaTeX/LibreOffice |
| `models/report.py` | Data contract for all exporters |
| `document/templates/latex/report.tex.j2` | Layout contract for PDF |
| `document/templates/academic_base.docx` | Unused DOCX base template |

## 9. Formatting divergences and dead hooks (verified / documented)

| Finding | Evidence | Status |
|---|---|---|
| PDF and DOCX formatting differ | `latex_generator.render` ignores `CategoryConfig`; template hard-codes margins/spacing/font | **Verified** |
| `academic_base.docx` unused | `DocxGenerator` never loads `template_path`; no code reference | **Verified** |
| `references.bib.j2` unused | No code reference; references use manual `thebibliography` | **Verified** |
| `FigureData` modeled but not rendered | `report.tex.j2` has no figures loop; `FigureData` exists in `models/report.py` | **Verified (template)** / documented in `docs/08` §3.7 |
| `appendix` modeled but not rendered | `ReportContent.appendix` not referenced by exporters | Documented in `docs/08` §3.7 |
| Absolute logo path in LaTeX | `latex_generator.py:271`, `report.tex.j2:114-115` | **Verified** |

## 10. Graphify cross-reference

Graphify extracted the LaTeX structure (see `06_GRAPHIFY_PROJECT_KNOWLEDGE_GRAPH.md`):

- `report.tex.j2` nodes: "IOE Pulchowk Academic Report LaTeX Template", "LaTeX Title Page Block", "Manual thebibliography Block", "IOE Color Palette".
- **EXTRACTED (1.0):** `06_DOCUMENT_GENERATION.md` → `report.tex.j2` (LatexGenerator → template); `tu_logo.png` → `report.tex.j2` (logo → title page); template blocks → "FrontPage".
- **INFERRED (0.85):** `report.tex.j2` ↔ `DocxGenerator` (shared report rendering intent).

These corroborate the manually verified mapping above.
