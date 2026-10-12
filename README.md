# AI-Powered Student Analytics and Success Platform

A runnable Python Flask + SQLite project with a light, colorful dashboard, role-based login, seven student data modules, AI demonstration models and support action tracking.

## Start on Windows (PowerShell or VS Code terminal)

Extract the RAR and open the `Student-Success-Platform` folder containing `app.py`.
Install Python 3.10 or newer if it is not already installed. Run each command:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000 in your browser. Keep the terminal open.
The actual database file `campus.db` is included with 300 synthetic students and ready-to-use accounts. You do NOT need to run seed.py.
If `py` is not recognized but `python` works, use `python -m venv .venv` for the first command.
After installation, you can double-click `RUN_WINDOWS.bat` for subsequent launches.

macOS / Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

## Demo login accounts

| Access | Username | Password | Scope |
|---|---|---|---|
| Admin | admin | Admin@12345 | All students and account administration |
| Faculty | faculty | Faculty@12345 | CSE department only |
| User / Student | student | Student@12345 | DEMO-0001 only |

These are public demonstration credentials. Change them from **My account** before entering real data or sharing the application. Authentication and backend authorization are enabled in this version because separate access roles were requested. The earlier no-login edition is a separate project.

## Permissions

| Feature | Admin | Faculty | User / Student |
|---|---|---|---|
| Dashboard, scores, AI and CSV | All students | Assigned department | Own linked record |
| View seven data areas | All students | Assigned department | Own linked record |
| Edit seven data areas | Yes | Assigned department | No |
| Add/delete student | Yes | No | No |
| Create accounts, reset passwords, enable/disable | Yes | No | No |
| View activity log | Yes | No | No |
| Add/complete support actions | Yes | Assigned department | Read own actions |
| Change own password | Yes | Yes | Yes |

Department and linked student are assigned when an Admin creates an account. Create the student record before creating its Student account. To change an account's role/scope, disable it and create a new account with the desired scope. Deleting a student unlinks its account; that account then has no student records to access.

## Seven integrated areas

- **Academic:** CGPA and backlogs.
- **Attendance:** overall attendance percentage.
- **LMS:** login activity score and assignment completion.
- **Engagement:** events, clubs, hackathons and certifications.
- **Placement:** aptitude, coding and mock interview scores.
- **Skills:** technical and soft skills.
- **Feedback:** student satisfaction and faculty feedback (1–5).

Open **Students**, select a row, choose the record area, enter values, and Save. Data is validated and stored in SQLite. This project supports CSV imports from a roster and seven separate sources, validation previews, cleaning reports, provenance, manual data entry and CSV export. It does not automatically connect to a college ERP or LMS service.

## Analytics and AI

- Explainable Student Success Score: weighted normalized indicators, with missing-data reporting.
- Academic and placement risk flags, risk groups, student filters, score distribution and department chart.
- Two trained logistic regression models estimate academic and placement risk.
- Student-level AI contributors and transparent rule-based support recommendations.
- Support action plan: add an action and mark it complete; students can read their own actions.

**Model limitation:** the bundled models use 4,000 synthetic examples with simulated binary outcomes. A 75/25 split is used for fitting/testing. They are a working ML demonstration, not models validated on actual institutional outcomes. Displayed percentages are demonstration estimates. Do not interpret synthetic test metrics as real-world accuracy. Missing any of the seven indices suppresses AI predictions. The weighted score and model predictions are separate outputs.

`models/risk_model.json` contains coefficients, feature means, data provenance and synthetic test metrics. Inference runs locally with Python's standard library; no API key, cloud AI or scikit-learn installation is required to run the app.

To reproduce training (optional):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-training.txt
.\.venv\Scripts\python.exe train_model.py
```

To adapt the models for real use, collect approved historical outcomes, replace the synthetic generator, use a time-based evaluation, assess calibration and subgroup errors, and obtain faculty review. No real student training dataset is provided.

## Database files

- `campus.db`: populated SQLite database; ready to use.
- `schema.sql`: relational table definitions.
- `database_dump.sql`: portable schema and demo data export.
- `seed.py`: optional reset and demo initialization tool.

All seven domain tables link to `students.id`. Users link to student IDs or a faculty department. `interventions` links support actions to students. `audit_log` records who changed or exported data.

Back up `campus.db` while the app is stopped. Keep it local; do not commit databases containing personal data to a public GitHub repository. Do not replace this database with the earlier project database: the role schema differs and there is no automatic migration.

Destructive reset commands (optional, erase current data):

```powershell
.\.venv\Scripts\python.exe seed.py --reset
```

For an empty student database with Admin and Faculty accounts only:

```powershell
.\.venv\Scripts\python.exe seed.py --reset --no-demo
```

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_access test_challenge
```

Tests use a temporary copy of the included demo database and cover role scopes, unauthorized access, all seven updates, student creation/deletion, CSV scope, support actions, CSRF, password reset/session invalidation, disabled accounts and model missing-data behavior. Run them against the unmodified demo database.

## Deployment and configuration

The supplied project is ready for local use and a persistent Python server. It writes SQLite and a local session key file. It is NOT a drop-in Vercel deployment: use persistent database storage and adapt the database layer for a serverless deployment first.

For a persistent server after installing requirements:

```sh
waitress-serve --host=127.0.0.1 --port=8000 app:app
```

Use HTTPS through a reverse proxy. Set SECRET_KEY to a stable secret and COOKIE_SECURE=1 when using HTTPS. DATABASE_PATH can set an alternate persistent database location; PORT controls local `python app.py` only. Login throttling is per process; a public deployment needs a shared rate limiter. CSRF tokens, parameterized queries, password hashing and role checks are included.

## Project files

- app.py: Flask routes, authentication, permissions, scoring and APIs.
- ai_engine.py: local ML inference and support recommendations.
- train_model.py: reproducible synthetic training.
- models/risk_model.json: actual fitted model parameters.
- templates/: login and main pages.
- static/: light theme, JavaScript dashboard and favicon.
- test_access.py: automated backend checks.
- RUN_WINDOWS.bat: launcher after installing dependencies.


## Challenge submission additions

Open Data import for CSV integration and quality reports. Start with sample_sources/students.csv, then import the seven module files. An empty module row preserves existing data; a partly empty module row is rejected. The first occurrence of a duplicate ID takes precedence, even if that row is invalid, so correct duplicates before applying. IDs are case-sensitive. Valid accepted rows commit together, while rejected/skipped rows remain unchanged. Percent suffixes are accepted only for 0–100 fields. Roster imports may update a student's department/year and therefore faculty access.

Trends shows monthly saved snapshots and a student profile shows individual history. All preloaded history is explicitly simulated. Faculty snapshots cover only their department; student accounts cannot create snapshots. Snapshots use each student's current access scope and disappear if the student is deleted.

The submission/ folder contains the score note, requirement coverage matrix, five-minute demo script, synthetic-data insights and presentation. No evaluation outcome or marks are guaranteed.
