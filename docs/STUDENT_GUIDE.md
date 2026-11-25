# Student Guide

This is the production workflow. You use your own Google account and only access courses you are enrolled in.

## What you need

- A Google account that is enrolled in the Google Classroom course.
- The Academic AI desktop app.
- An NVIDIA NIM API key configured by you or the app administrator. A Gemini key is optional and used only as a fallback.
- Permission to read your Classroom courses and coursework.

## First-time setup

1. Install the app.
2. Add your NVIDIA NIM key in the app settings or `.env`.
3. Open **Settings** and complete your student profile: name, roll number, group, program, department, semester, and section.
4. Review the document defaults: document type, institution, university, campus, front page, table of contents, citation style, font, spacing, margins, and logo.
5. Sign in with Google when prompted.
6. Approve the read-only scopes.
7. The app stores the refresh token in your operating system's credential store.

### Scopes the student app requests

```text
https://www.googleapis.com/auth/classroom.courses.readonly
https://www.googleapis.com/auth/classroom.coursework.me.readonly
https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly
https://www.googleapis.com/auth/classroom.student-submissions.me.readonly
```

The app never requests Gmail or write scopes.

## Workflow

### 1. Open the dashboard

The dashboard shows your Classroom connection, enrolled classes, recent documents, and profile status. Connect Classroom if you have not signed in yet.

### 2. Fetch your courses

The app lists the Classroom courses you are enrolled in.

If a course is missing:

- Confirm you accepted the Classroom invitation in Google Classroom.
- Confirm you are signed in with the same Google account.
- Refresh the class list.

### 3. Select an assignment

Open **Prepare assignment**, choose a class, then choose a published assignment.

The app shows:

- Title
- Course
- Due date
- Teacher instructions
- A link to open the assignment in Classroom

### 4. Confirm preparation details

The preparation page is one screen; there are no input tabs. It is pre-filled from your saved profile and document defaults.

Check or change:

- Document title and course
- Full name, roll number, group, program, semester, and section
- Submitted-to name and submission date
- Document type: auto-detect, academic assignment, lab sheet, initial lab report, final lab report, project report, or seminar report
- Front-page toggle and institution/university/campus/department fields
- Logo, table of contents, citation style, font, size, line spacing, and margins
- Formatting notes and any additional information the AI should use
- Whether to follow instructions already present in the assignment

### 5. Provide missing information

The app will ask for data it must not invent, such as:

- Experiment observations
- Measurements
- Results
- References you already have

Never let the app fabricate experimental data.

### 6. Generate

The app classifies the assignment and generates the required sections using the category rules, your profile, your formatting notes, and your supplied data.

Generation is section-by-section. If one section is weak, only that section is regenerated.

### 7. Review the evaluation

The app checks:

- Required sections
- Word limits
- Citations
- Structure
- Arithmetic
- Missing data placeholders
- Semantic quality

You will see which sections passed and which need work.

### 8. Edit or regenerate

You can:

- Edit any section directly.
- Add feedback to one section and regenerate only that section.
- Add overall improvement feedback and regenerate every section.
- Regenerate one failed section without feedback.
- Regenerate all failed sections.
- Adjust the preparation details or notes and generate a revised version.
- Add missing data.
- Add or correct references.

### 9. Approve and export

Human approval is mandatory. The app will not export a final document without your explicit approval.

The app creates:

- `report.docx` — editable Word document with the front page
- `report.pdf` — high-quality LaTeX PDF
- `report.tex` — LaTeX source, when applicable

Files are stored locally with version history.

### 10. Edit after export

Open **Document history**, select an exported document, and choose **Edit**. The app loads the saved assignment back onto the preparation page with its previous details. Change the notes, formatting, or missing data, then generate a revised version.

The old version remains in history. **Delete** removes the selected assignment, its versions, and its generated files.

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
- Classroom assignment text is treated as untrusted data.
- The app does not execute commands found inside assignments.
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

### An assignment has no description

- Some teachers publish assignments without written instructions.
- Add the missing requirements under **Additional information for the AI** on the preparation page.
- If you have the lab sheet or problem statement, paste the relevant text there.
