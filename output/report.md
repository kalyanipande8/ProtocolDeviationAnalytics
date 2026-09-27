# Protocol Deviation Analysis Report

All numbers below come directly from an actual run of `python run_all.py` against synthetically simulated data (fixed random seed). No Tableau workbook was built or run to produce this report -- see README.md for why.

## Scope

- **144 protocol parameters** monitored across **6 studies**, 12 monthly periods each.

## Deviation rate by study

| study_id   |   n_deviations |   n_observations |   deviation_rate_pct |
|:-----------|---------------:|-----------------:|---------------------:|
| STUDY-01   |            143 |             1728 |                 8.28 |
| STUDY-02   |            191 |             1728 |                11.05 |
| STUDY-03   |            145 |             1728 |                 8.39 |
| STUDY-04   |            180 |             1728 |                10.42 |
| STUDY-05   |            136 |             1728 |                 7.87 |
| STUDY-06   |            142 |             1728 |                 8.22 |

## Deviation rate by parameter category

| parameter_category                   |   n_deviations |   n_observations |   deviation_rate_pct |
|:-------------------------------------|---------------:|-----------------:|---------------------:|
| Visit Window Compliance              |            189 |             1296 |                14.58 |
| Lab Sample Handling Timing           |            180 |             1296 |                13.89 |
| Concomitant Medication Documentation |            137 |             1296 |                10.57 |
| Source Document Verification         |            126 |             1296 |                 9.72 |
| Dosing Schedule Adherence            |            116 |             1296 |                 8.95 |
| Adverse Event Reporting Timeliness   |             85 |             1296 |                 6.56 |
| Inclusion/Exclusion Criteria         |             63 |             1296 |                 4.86 |
| Informed Consent Timing              |             41 |             1296 |                 3.16 |

## Severity breakdown (all deviations)

| severity   |   n_deviations |   pct |
|:-----------|---------------:|------:|
| Minor      |            505 | 53.90 |
| Major      |            301 | 32.12 |
| Critical   |            131 | 13.98 |

## Investigation time: before vs after proactive dashboard

- Before (mean): **11.45 hours**
- After (mean): **6.58 hours**
- Reduction: **42.5%** (paired t = 30.60, p = 4.33e-143, n = 937 deviations)

## Corrective action closure

- Overall closure rate: **63.9%**

| status   |   count |
|:---------|--------:|
| Closed   |     599 |
| Open     |     212 |
| Overdue  |     126 |

## What the Tableau dashboard would show (not built here -- see README)

If built in actual Tableau against `output/tableau_extract.csv`, the dashboard would consist of:

- **Sheet 1 - Deviation Rate by Study (bar chart):** one bar per study, `SUM([deviation_flag]) / COUNTD([study_id]+[parameter_id]+[period])`, colored by rate threshold (calculated field `Deviation Rate Flag` = IF rate > study average THEN 'Above Average' ELSE 'At/Below Average').
- **Sheet 2 - Investigation Time Trend (line, before/after reference line):** `investigation_time_before_hours` and `investigation_time_after_hours` as two measures on a dual-axis line chart over `period`, with a reference line at the 42% target reduction band, so investigators can see the trend converging.
- **Sheet 3 - Severity Heatmap by Parameter Category:** `parameter_category` x `severity` crosstab as a heatmap, highlighting which categories skew toward Critical severity for proactive corrective-action prioritization.
- **Sheet 4 - Corrective Action Status Tracker:** a stacked bar / Gantt-style view of `corrective_action_status` (Closed/Open/Overdue) by study and category, with a calculated field `Days Open` = TODAY() - [deviation_date] for still-open items, used for the proactive corrective-action planning workflow.
- A dashboard-level filter action linking Sheet 1 -> Sheet 3/4 so clicking a study bar filters the severity heatmap and CA tracker to that study.
