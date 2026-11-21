# Academic AI

Student-facing desktop assistant for academic assignments. It fetches an assignment from Google Classroom, generates structured content, validates it, lets the student review and edit, and exports a DOCX and a high-quality PDF.

## Who it is for

Students. The production app signs in with the student's own Google account and only reads courses and assignments the student is enrolled in.

## What it does

1. Fetches courses and assignments from Google Classroom.
2. Classifies the assignment type.
3. Loads the matching rules and template.
4. Generates structured sections with Gemini.
5. Validates output with deterministic checks and a separate evaluator.
6. Requests missing information from the student.
7. Lets the student review, edit, regenerate, and approve.
8. Exports DOCX and PDF.

Automatic submission to Classroom is not part of the first build. A future post-approval "submit" action must be explicit and confirmed.

## Quick start

```bash
uv sync --extra dev --extra google
cp .env.example .env
```

Add your Gemini key to `.env`:

```env
GEMINI_API_KEY=your-key
```

Save the Google OAuth desktop client as `credentials.json` in the project root.

Run the current CLI smoke test:

```bash
uv run python -m app.main
```

Test Classroom access as a student:

```bash
uv run python -m scripts.test_classroom
```

## Documentation

- [Student guide](docs/STUDENT_GUIDE.md) — the real student workflow
- [Implementation plan](plan.md) — architecture, workflow, phases, and risks

## Status

Early development. Project scaffolding and the Classroom read test script are in place. The desktop UI and generation workflow are next.
