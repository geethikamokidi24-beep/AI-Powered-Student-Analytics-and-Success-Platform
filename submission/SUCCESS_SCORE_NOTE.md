# Student Success Score: method note

Purpose: prioritize supportive faculty review using integrated educational indicators. The score is a transparent rule-based index, separate from the ML estimates.

| Domain | Index (0–100) | Weight |
|---|---|---:|
| Academic | Clamp(CGPA × 10 − backlogs × 8, 0, 100) | 30 |
| Attendance | Overall attendance percentage | 20 |
| LMS | Mean(login activity score, assignment completion %) | 12 |
| Placement | Mean(aptitude, coding, mock interview) | 15 |
| Skills | Mean(technical, soft skills) | 10 |
| Engagement | Min(100, events × 10 + clubs × 15 + hackathons × 20 + certifications × 15) | 8 |
| Feedback | Mean(satisfaction, faculty feedback) × 20, ratings 1–5 | 5 |

For complete records: **Score = sum(weight × domain index / 100)**. Weights sum to 100. Each domain shows its earned points and the lost points relative to its maximum.

For missing data: include a domain only if all its required fields are present. If observed weights sum to at least 60, normalize the observed weighted score to 100. Otherwise show Unrated. Never silently replace missing values with zero. Coverage is visible. A score computed from fewer domains is not equally informative as a complete score.

Worked example: academic=70, attendance=80, LMS=60, placement=50, skills=70, engagement=50, feedback=80 gives 21 + 16 + 7.2 + 7.5 + 7 + 4 + 4 = **66.7/100**, overall Low risk. Attendance below 75 or low CGPA can still trigger an independent academic flag.

## Risk identification

- Overall High: score <52. Medium: 52≤score<64. Low: score≥64. Unrated is separate.
- Academic flag: CGPA<6, at least 2 backlogs, or attendance<75% where data exists.
- Placement flag: mean placement readiness<50/100.
- AI demonstration: separate logistic regression estimates for academic and placement outcomes. All seven indices are required. Top contributors are positive log-odds contributions relative to the synthetic training mean, summed across the two models.

Thresholds and weights are explicit starting assumptions for a campus prototype, not validated institutional policy. The Method page and app.py expose the exact implementation. No observed flag does not imply safety when data is incomplete.

## Segmentation and action

Ordered rules identify strong academics with low placement readiness, attendance/backlog concerns, low engagement, placement-ready students, steady performers and insufficient data. These rules are evaluated in order, so each student has one segment. Faculty can review recommended actions, record a support plan, and mark it completed.

## AI and interpretation limits

The two ML models use 4,000 synthetic examples, split into 3,000 training and 1,000 test examples. Synthetic metrics test implementation, not real-world predictive validity. Real institutional deployment requires approved historical outcomes, chronological testing, calibration and fairness review. Historical demo snapshots are also simulated. A rising trend does not demonstrate that an intervention caused improvement.
