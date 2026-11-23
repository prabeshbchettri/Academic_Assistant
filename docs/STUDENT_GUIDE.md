# Student Guide

This is the production workflow. You use your own Google account and only access courses you are enrolled in.

## What you need

- A Google account that is enrolled in the Google Classroom course.
- The Academic AI desktop app.
- A Gemini API key configured by you or the app administrator.
- Permission to read your Classroom courses and coursework.

## First-time setup

1. Install the app.
2. Add your Gemini key in the app settings or `.env`.
3. Sign in with Google when prompted.
4. Approve the read-only scopes.
5. The app stores the refresh token in your operating system's credential store.

### Scopes the student app requests

```text
https://www.googleapis.com/auth/classroom.courses.readonly
https://www.googleapis.com/auth/classroom.coursework.me.readonly
https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly
https://www.googleapis.com/auth/classroom.student-submissions.me.readonly
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/drive.readonly
```

The app never requests write scopes in normal use.

## Workflow

### 1. Fetch your courses

The app lists the Classroom courses you are enrolled in.

If a course is missing:

- Confirm you accepted the Classroom invitation in Google Classroom.
- Confirm you are signed in with the same Google account.
- Refresh the course list.

### 2. Select an assignment

Choose the assignment or material you want to work on.

The app shows:

- Title
- Course
- Due date
- Instructions
- Attachments
- Points, if available

### 3. Review the extracted instructions

Check that the assignment text and attachments were read correctly. If a scanned PDF was used, OCR text may need correction.

### 4. Provide missing information

The app will ask for data it must not invent, such as:

- Experiment observations
- Measurements
- Results
- Student details
- References you already have

Never let the app fabricate experimental data.

### 5. Generate

The app classifies the assignment and generates the required sections using the category rules and your supplied data.

Generation is section-by-section. If one section is weak, only that section is regenerated.

### 6. Review the evaluation

The app checks:

- Required sections
- Word limits
- Citations
- Structure
- Arithmetic
- Missing data placeholders
- Semantic quality

You will see which sections passed and which need work.

### 7. Edit or regenerate

You can:

- Edit any section directly.
- Regenerate one section.
- Add missing data.
- Add or correct references.

### 8. Approve

Human approval is mandatory. The app will not export a final document without your explicit approval.

### 9. Export

The app creates:

- `report.docx` — editable Word document
- `report.pdf` — high-quality LaTeX PDF
- `report.tex` — LaTeX source, when applicable

Files are stored locally with version history.

## Submitting to Classroom

The first build does **not** submit automatically.

A future version may offer a **Submit to Classroom** button after approval. That action will:

- Require a separate write scope.
- Show exactly what will be uploaded.
- Require a confirmation dialog.
- Never run automatically.

## Privacy and security

- Your assignment history and documents stay on your machine.
- API keys and OAuth tokens are stored locally.
- OAuth tokens are stored in the OS keyring when available.
- Extracted documents and emails are treated as untrusted data.
- The app does not execute commands found inside documents or emails.
- You can revoke access at any time from your Google Account permissions page.

## Troubleshooting

### No courses appear

- Accept the Classroom invitation.
- Confirm the correct Google account is signed in.
- Check that the course is active.

### Access blocked

- If the app is in Google OAuth Testing mode, your account must be added as a test user.
- Ask the app administrator to add your Gmail address under **Audience → Test users**.

### Weekly sign-in

External OAuth apps in Testing mode may require re-authentication every 7 days. This is a Google limitation, not an app bug.

### PDF export fails

- Confirm Tectonic is available.
- If not, the app falls back to LibreOffice.
- If neither is available, export DOCX and convert it manually.

### OCR text is wrong

- Scanned PDFs may produce imperfect text.
- Correct the extracted text before generation.
