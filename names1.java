# ROLE: Senior AI Engineer & Software Architect

Act as a Senior AI Engineer, Software Architect, and Technical Lead reviewing this entire project repository.

Your responsibility is to understand the existing project before suggesting or implementing improvements.

I want to approach this project as an AI Engineer who needs to understand how a real-world production application is structured, how its components communicate, how data flows through the system, and how the architecture can be improved.

## PHASE 1 — Repository Exploration

First, inspect the complete project directory recursively.

Identify and categorize all important:

- Directories and subdirectories
- Python source files
- Configuration files
- Environment and dependency files
- API routes and endpoints
- Database models and schemas
- Services and business logic
- AI/LLM-related modules
- Document processing modules
- Templates and static assets
- Frontend components
- Tests and testing configurations
- Deployment and infrastructure files
- Documentation files
- Scripts and utility files

Do not ignore files simply because their names appear unimportant.

Skip generated or irrelevant directories such as `.git`, `venv`, `__pycache__`, `node_modules`, and build artifacts when producing the main architecture report. Mention their existence only when relevant.

## PHASE 2 — Identify What I Should Understand First

Organize the project files into a learning and investigation order.

Use these categories:

1. **Project Foundation**
   - README
   - requirements.txt / pyproject.toml
   - .env.example
   - Configuration files
   - Application entry points

2. **Application Architecture**
   - Main application initialization
   - Routing
   - Controllers
   - Services
   - Dependency injection
   - Middleware

3. **Database Architecture**
   - Database connections
   - Models
   - Schemas
   - Migrations
   - Repositories
   - Relationships between entities

4. **AI Engineering Components**
   - LLM providers and model configuration
   - Prompt templates
   - Embedding models
   - Vector databases
   - RAG pipelines
   - Retrieval and reranking
   - Agent workflows
   - Tool calling
   - Context management
   - Evaluation and monitoring

5. **Document Processing and Generation**
   - Document ingestion
   - File loaders
   - Text extraction
   - Text cleaning
   - Chunking
   - Metadata extraction
   - Document templates
   - PDF generation
   - LaTeX templates and formatting
   - Export and download functionality

6. **Frontend Architecture**
   - Pages
   - Components
   - State management
   - API communication
   - Upload interfaces
   - Document preview
   - Download functionality

7. **Testing and Quality Assurance**
   - Unit tests
   - Integration tests
   - API tests
   - AI pipeline tests
   - Document generation tests

8. **Deployment and Production Readiness**
   - Docker
   - CI/CD
   - Logging
   - Error handling
   - Security
   - Performance
   - Environment management

For every category, identify the exact files and folders in this repository.

Do not assume that all these components exist. Clearly distinguish implemented, partially implemented, missing, and not applicable components.

## PHASE 3 — Document and LaTeX Architecture (HIGH PRIORITY)

Pay special attention to every file responsible for defining how generated assignments and academic documents should look.

Search for:

- `.tex` files
- `.cls` files
- `.sty` files
- `.bib` files
- `.latex` files
- Jinja2 templates
- HTML document templates
- CSS used for document styling
- Markdown templates
- JSON/YAML document configurations
- PDF generation scripts
- LaTeX compilation scripts
- Document formatting utilities

Identify the files responsible for:

1. Overall document structure.
2. Assignment title and heading format.
3. University, campus, department, and subject information.
4. Student name, roll number, registration number, and submission details.
5. Cover page and title page.
6. Table of contents.
7. Chapter and section numbering.
8. Question and answer formatting.
9. Code blocks and syntax highlighting.
10. Mathematical equations and symbols.
11. Images, figures, and tables.
12. Page margins and paper size.
13. Header and footer.
14. Page numbering.
15. Font family and font sizes.
16. Line spacing and paragraph spacing.
17. References and bibliography.
18. Appendices.
19. PDF export and compilation.

IMPORTANT:

Do not treat LaTeX files as ordinary implementation files.

They may define the visual identity, academic formatting rules, and document-generation standards of the entire application.

Explain how the document-generation pipeline works:

User input → Document content → Template selection → LaTeX generation → Compilation → PDF output.

Adjust this flow according to the actual implementation.

Identify which files control content and which files control presentation.

Explain how changing a particular template or configuration would affect the final generated PDF.

Also identify duplicated formatting logic, hardcoded values, and opportunities to make templates reusable and configurable.

## PHASE 4 — Understand the Complete Data Flow

Trace the actual execution flow of the application.

Identify:

- Where user input enters.
- Which API or frontend component receives it.
- Which validation layer processes it.
- Which service handles the request.
- Where AI models are called.
- How prompts are constructed.
- How information is retrieved or generated.
- How document content is structured.
- How templates are selected.
- How LaTeX or other document formats are generated.
- How the final PDF is compiled.
- Where generated files are stored.
- How the user receives or downloads the output.

Create architecture and data-flow diagrams using Mermaid.

Do not create diagrams based only on assumptions. Use the actual code.

## PHASE 5 — File Dependency Analysis

Identify how important files depend on one another.

For each major file, explain:

- What its responsibility is.
- Why it exists.
- Which files call or import it.
- Which files it depends on.
- What data it receives.
- What data it produces.
- What would break if it were modified incorrectly.

Prioritize important execution paths rather than explaining every minor utility individually.

## PHASE 6 — AI Engineering Improvement Audit

After understanding the architecture, evaluate the project from a production-oriented AI engineering perspective.

Investigate:

- Separation of concerns.
- Modular architecture.
- Reusability.
- Code duplication.
- Error handling.
- Logging.
- Configuration management.
- Security and API key management.
- Prompt management.
- LLM provider abstraction.
- Token usage and cost optimization.
- Retrieval quality.
- Context management.
- Document-generation reliability.
- PDF and LaTeX compilation errors.
- Testing coverage.
- Scalability.
- Maintainability.

For every proposed improvement, provide:

1. Current implementation.
2. Problem or limitation.
3. Why it matters.
4. Recommended solution.
5. Exact files that need modification.
6. Expected benefits.
7. Potential risks or breaking changes.
8. Priority: Critical, High, Medium, or Low.

Do not recommend unnecessary technologies or introduce frameworks just because they are popular.

Prefer improving the existing architecture when it is appropriate.

## PHASE 7 — Create a Learning and Improvement Roadmap

Create an ordered roadmap with three stages:

**Stage A: Understand**
- Files I must read first.
- Architecture I must understand.
- Important execution paths to trace.
- Concepts I need to understand before modifying code.

**Stage B: Improve**
- Architectural improvements.
- Code-quality improvements.
- AI pipeline improvements.
- Document-generation improvements.
- Testing improvements.

**Stage C: Production Readiness**
- Security.
- Performance.
- Reliability.
- Monitoring.
- Deployment.
- Evaluation.

For every task, mention the exact files and prerequisites.

## PHASE 8 — Generate Documentation

Create a `docs/` directory if it does not already exist.

Generate the following documentation files:

1. `docs/01_PROJECT_OVERVIEW.md`
   - Project purpose, features, technologies, and repository overview.

2. `docs/02_PROJECT_STRUCTURE.md`
   - Complete directory tree.
   - Responsibilities of important directories and files.
   - Why each exists.

3. `docs/03_SYSTEM_ARCHITECTURE.md`
   - Architecture diagrams.
   - Component relationships.
   - Application execution flow.

4. `docs/04_DATA_FLOW.md`
   - End-to-end request and data flow.
   - AI processing flow.
   - Document generation flow.

5. `docs/05_AI_ENGINEERING_ARCHITECTURE.md`
   - LLM integration.
   - Prompts.
   - RAG and retrieval.
   - Embeddings.
   - AI services and pipelines.

6. `docs/06_DOCUMENT_GENERATION.md`
   - Document-generation architecture.
   - LaTeX files and their responsibilities.
   - Formatting rules.
   - PDF generation and compilation.
   - Content versus presentation separation.

7. `docs/07_DATABASE_AND_API.md`
   - Database models.
   - Relationships.
   - API endpoints.
   - Request and response structures.

8. `docs/08_TECHNICAL_DEBT_AND_IMPROVEMENTS.md`
   - Existing problems.
   - Missing functionality.
   - Improvement recommendations.
   - Priority levels.

9. `docs/09_LEARNING_AND_IMPLEMENTATION_ROADMAP.md`
   - Exact order in which I should understand and improve the project.

## IMPORTANT RULES

- First inspect and understand the existing implementation.
- Do not modify application source code.
- Do not refactor or delete anything.
- Do not install additional dependencies.
- Do not invent files, functionality, architecture, or implementation details.
- Clearly label assumptions and missing implementations.
- Reference actual file paths and relevant function/class names.
- Do not explain basic Python syntax.
- Explain engineering decisions and architectural reasoning.
- Explain WHY a component exists, not just WHAT it does.
- Preserve the existing project behavior.
- Do not expose API keys, credentials, or other secrets in generated documentation.
- Keep documentation synchronized with the actual repository.
- Do not overwrite existing documentation without inspecting it first.

## FINAL DELIVERABLE

At the end, provide:

1. A summary of the existing architecture.
2. The 10 most important files I should read first, in order.
3. The most important files responsible for assignment formatting and LaTeX generation.
4. The complete application execution flow.
5. The biggest architectural weaknesses.
6. The top 10 recommended improvements.
7. A step-by-step implementation order.

Remember: You are conducting a technical architecture audit, not blindly rewriting a project.

I want to understand this codebase like a junior AI Engineer preparing to take ownership of an existing production-oriented application.