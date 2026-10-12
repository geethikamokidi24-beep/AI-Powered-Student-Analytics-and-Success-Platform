# Five-minute demo script

Use an extracted copy of the project. Start the server as described in README.md. The included SQLite database already has demo records. Do not reset it during the presentation.

## 0:00–0:35 — Campus problem

Explain that attendance, marks, LMS and placement records often sit in separate systems. This prototype joins seven sources by student ID so faculty can decide who needs support and record the action taken.

## 0:35–1:25 — Integration and cleaning

Sign in as admin / Admin@12345. Open Data import. Show source coverage: 294 of 300 synthetic students have all seven areas.
Choose attendance and upload sample_sources/attendance_dirty_demo.csv. Click Preview and validate. Expected: 1 accepted, 3 rejected, 1 skipped. Show whitespace/percent normalization, duplicate ID, out-of-range value, unknown ID and blank preservation. Preview does not change the DB. If you apply it, explain that the one accepted student record updates.
The eight clean CSV files can recreate roster plus seven module sources. Import students.csv first.

## 1:25–2:30 — Score, risks and explainability

Open Overview and Students. Filter High risk, then open any profile. Explain weighted domain points, missing indicators, exact risk reasons and AI estimates. The supplied database starts at mean score 65.0, with 100 academic flags and 88 placement flags. These categories overlap and are not additive.
Open Method for the formula. Show that the ML estimate is separate from the rule-based score and uses synthetic training data.

## 2:30–3:20 — Segments and action

Open Segments. Select strong academics with low placement readiness. Explain why coding practice and mock interviews may be more relevant than generic tutoring. Open a profile, add a specific support action, then mark it completed. This turns analysis into a recorded follow-up.

## 3:20–4:10 — Trends

Open Trends. Explain that July–September are simulated examples, not measured outcomes. Show mean score and risk counts beside the cohort sizes. Save a snapshot of the current month to demonstrate real persistence. The same month overwrites snapshots only for accessible students.

## 4:10–4:45 — Role boundaries

Sign out. Faculty / Faculty@12345 sees only CSE students and no Admin account panel. Student / Student@12345 sees only DEMO-0001 and cannot edit institutional records. The backend enforces these rules, not just hidden buttons.

## 4:45–5:00 — Scope and next step

Show the requirements matrix and note. Explain that real deployment needs approved historical outcomes to validate the models, and persistent hosting for SQLite. Do not claim real-world model accuracy or guaranteed judging marks.
