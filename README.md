# Smart Campus Analytics

Student Success platform for faculty and administrators. Flask backend, SQLite database, direct dashboard access with all Admin features available. No login is required.

## What is included

- **Database tables:** `users`, `students`, `academic`, `attendance`, `lms`, `engagement`, `placement`, `skills`, `feedback`, `audit_log` (see `schema.sql`).
- **Admin page:** manage staff accounts (create, disable, set password), add or delete students, view the activity log, update any data.
- **Direct access:** view the dashboard, open and update students, export CSV, and use all Admin controls.
- **Dashboard:** overview, student list with filters, explainable score per student, segments, method page.
- **Public pages:** privacy policy at `/privacy`, terms and conditions at `/terms`, favicon at `static/favicon.svg`.

## Run it

Requires Python 3.9 or newer.

```
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS or Linux
pip install -r requirements.txt
python seed.py                  # creates campus.db, prints the admin and staff passwords once
python app.py                   # http://127.0.0.1:5000
```

`python seed.py --no-demo` creates accounts only, for real data. `python seed.py --reset` starts over. Set `ADMIN_PASSWORD` and `STAFF_PASSWORD` to choose your own (10 or more characters).

The seeded students (IDs starting `DEMO-`) are synthetic. Delete them before using real data: open each student, or run `--reset --no-demo` on a new database.

## Entering real data

Admin adds a student under Admin, then any visitor opens the student and fills each record (academic, attendance, LMS, engagement, placement, skills, feedback). Each table keeps one current record per student. A student with too many records missing is shown as Unrated.

## Score

Weights: academic 30, attendance 20, placement readiness 15, LMS 12, skills 10, engagement 8, feedback 5. High risk below 52, medium below 64. Full rules are on the Method page and in `compute()` in `app.py`.

## Deploying

```
pip install -r requirements.txt
SECRET_KEY=<long random string> COOKIE_SECURE=1 gunicorn -w 2 -b 127.0.0.1:8000 app:app
```

Put it behind HTTPS (nginx or Caddy). Set `COOKIE_SECURE=1` only when serving over HTTPS. Back up `campus.db` regularly. This version has no login gate; anyone who can reach the app can use Admin controls. Account creation, enabling/disabling and password changes are preserved, but do not restrict access in this mode.

## Before you launch

- [ ] Point your custom domain at the server and enable HTTPS.
- [ ] Set `SECRET_KEY` and `COOKIE_SECURE=1`.
- [ ] Change or replace the seeded passwords.
- [ ] Have the privacy policy and terms reviewed by someone qualified.
- [ ] Remove demo students.
- [ ] If you host on a site builder that adds a "Made with" badge, remove it in that platform's settings. This code adds none.

## Layout

```
app.py          routes, request protection, scoring
schema.sql      database tables
seed.py         first accounts and demo data
templates/      dashboard, privacy, terms, error
static/         css, js, favicon.svg
```
