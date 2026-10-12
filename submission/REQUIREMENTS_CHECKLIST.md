# Problem-statement coverage and judge walkthrough

This matrix records implemented evidence. It does not predict or guarantee an evaluation score.

| Requirement / evaluation area | Working evidence | Where to demonstrate |
|---|---|---|
| Data integration (30%) | Roster plus seven CSV sources join by student ID; normalized headers, whitespace and percent strings; numeric/range checks; duplicate and missing handling; preview; import provenance | Data import, sample_sources/, integration.py |
| Unified student view | Seven domain tables left-join into one profile; coverage remains visible | Students, select a row |
| Success Score and risk (25%) | Weighted 0–100 score, missing-data threshold, academic/placement flags and ML demonstration probabilities | Overview, student details, Method |
| Dashboard and visualization (25%) | Filters, sort, charts, monthly trends, per-student history, export, role-specific scope | Overview, Students, Trends |
| Campus problem understanding (10%) | Scoped faculty review, student self-view, support recommendations and tracked actions | Sign in under each role, student Support action plan |
| Presentation and demo (10%) | Short score note, demo script, editable slide deck and demo dataset | submission/ |
| Segmentation bonus | Six ordered, meaningful segments including strong academics / weak placement | Segments |
| Explainability bonus | Domain points, biggest losses, exact risk reasons and model contributors | Student profile, Method |

## Boundaries to disclose

CSV exports represent separate source systems. Live ERP/LMS connectors are not included or needed for this prototype demonstration. The examples in the statement are covered through domain-level indicators; per-subject mark/attendance tables are not implemented. All included students, historical profiles and ML training outcomes are synthetic. There is no verified claim of predictive accuracy on real students or of measured intervention impact. Judges decide acceptance and marks.
