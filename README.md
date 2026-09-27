# Protocol Deviation Tracking with Corrective Actions

> **Note on Tableau:** the resume bullet behind this project names **Tableau**
> as the dashboard tool. Tableau is a licensed desktop application with no
> CLI/scriptable API, and **it is not installed or available in this
> environment**, so **no Tableau workbook was built, opened, or run here** --
> there is no `.twbx` file and no screenshot of a live dashboard in this repo.
> What *was* built, in full: the complete Python data pipeline (simulate ->
> standardize -> analyze) that a Tableau dashboard would sit on top of, a
> clean, documented, Tableau-ready CSV extract (`output/tableau_extract.csv`),
> matplotlib figures standing in for what the dashboard's views would show,
> and a written, sheet-by-sheet description of what the actual Tableau
> dashboard would contain if built from that extract (see "What the Tableau
> dashboard would show" in `output/report.md`). This mirrors how the sibling
> project `PrecisionMedicineStratificationDashboard` handled an unavailable
> runtime (R/Shiny there; Tableau here) -- state plainly what could and could
> not be executed rather than implying a tool ran when it didn't.

> **Disclaimer:** All data in this project is **synthetically simulated** by
> `simulate_protocol_deviation_data.py` using a fixed random seed (42). No
> real patient, site, study, or sponsor data is used anywhere. Deviation
> rates, severity distributions, and investigation-time figures are
> plausible, literature-informed synthetic values calibrated to match the
> scale and headline result of the resume bullet -- they are not measurements
> from any real clinical trial.

## What it does

Simulates and analyzes protocol-deviation monitoring data across **144
protocol parameters** and **6 clinical studies**, and produces the data
extract and written dashboard design a Tableau "Protocol Deviation Tracking
with Corrective Actions" dashboard would be built from.

1. **`simulate_protocol_deviation_data.py`** simulates 144 protocol
   parameters (8 categories of 18 parameters each: Visit Window Compliance,
   Inclusion/Exclusion Criteria, Dosing Schedule Adherence, Informed Consent
   Timing, Lab Sample Handling Timing, Concomitant Medication Documentation,
   Adverse Event Reporting Timeliness, Source Document Verification) monitored
   across 6 studies over 12 monthly periods, with category- and study-specific
   deviation rates, a severity classification (Minor/Major/Critical) and a
   corrective-action record (status + days-to-close) for each deviation. It
   also simulates a matched "before proactive dashboard" and "after proactive
   dashboard / corrective-action planning" investigation-time (hours) pair for
   every deviation, calibrated to a ~42% mean reduction.

2. **`standardize.py`** joins the raw tables into one unified long-format
   table -- **one row per protocol-parameter x study x period** -- and writes
   it both to `data/processed/unified_deviation_data.csv` (used by the Python
   analysis) and to **`output/tableau_extract.csv`**, the Tableau-ready
   extract (identical schema, documented below).

3. **`deviation_analysis.py`** computes deviation rate by study and by
   parameter category, severity breakdown, the before/after investigation-time
   reduction (with a paired t-test), and corrective-action closure rate;
   saves 3 matplotlib figures to `output/figures/` standing in for the
   dashboard's views; and writes `output/report.md` with the real computed
   numbers plus a sheet-by-sheet description of what the actual Tableau
   dashboard would contain.

4. **`run_all.py`** orchestrates all three steps.

5. **`tests/test_pipeline.py`** (pytest) checks parameter/study counts, the
   unified table's shape and schema, the Tableau extract's schema, the
   investigation-time reduction falling in a reasonable [30%, 50%] band
   around the 42% target, and an injected sanity check (a category simulated
   with a higher base deviation rate must show a higher observed rate).

## Tableau extract schema (`output/tableau_extract.csv`)

One row per protocol-parameter x study x period (10,368 rows = 144 params x
6 studies x 12 periods). Ready to drop into Tableau and pivot/filter on any
column.

| Column | Type | Description |
|---|---|---|
| `study_id` | string | One of `STUDY-01` .. `STUDY-06` |
| `parameter_id` | string | `P001` .. `P144` |
| `parameter_name` | string | Human-readable parameter name |
| `parameter_category` | string | One of the 8 categories listed above |
| `period` | int | Monthly period, 1-12 |
| `deviation_flag` | bool | Whether a deviation occurred this parameter/study/period |
| `severity` | string or blank | `Minor` / `Major` / `Critical` (blank if no deviation) |
| `corrective_action_status` | string or blank | `Closed` / `Open` / `Overdue` (blank if no deviation) |
| `corrective_action_days_to_close` | float or blank | Days to close, only populated when status = `Closed` |
| `investigation_time_before_hours` | float or blank | Simulated investigation time under the pre-dashboard regime |
| `investigation_time_after_hours` | float or blank | Simulated investigation time under the proactive-dashboard regime |

## How to run

```bash
python3 -m venv .venv && source .venv/bin/activate   # or use your existing env
pip install -r requirements.txt
python run_all.py
pytest -q
```

(In this environment the pipeline was run against the system Python/Anaconda
environment, which already had numpy/pandas/scipy/matplotlib/pytest/tabulate
installed, rather than a fresh `.venv` -- disk space on this machine was
nearly exhausted, so `pip install` into a new venv failed with "No space
left on device." A fresh venv install should work fine on a machine with
normal free disk space; `requirements.txt` is provided for that.)

## Results

_All numbers below are copied directly from an actual run of `python
run_all.py` -- nothing is hardcoded. Fixed random seed makes them
reproducible._

- **144 protocol parameters** across **6 studies**, 12 monthly periods each
  -> **10,368 parameter x study x period observations**.
- **937 deviations** observed overall (~9.0% of all observations).
- **Deviation rate by study** ranged from 7.87% (STUDY-05) to 11.05%
  (STUDY-02).
- **Deviation rate by category** ranged from 3.16% (Informed Consent Timing)
  to 14.58% (Visit Window Compliance) -- the two most deviation-prone
  categories, Visit Window Compliance and Lab Sample Handling Timing, were
  simulated with intentionally higher base rates, consistent with how these
  categories behave operationally in real trials.
- **Severity breakdown:** 53.9% Minor, 32.1% Major, 14.0% Critical.
- **Investigation time reduction: before = 11.45 hours, after = 6.58 hours,
  a 42.5% reduction** (paired t = 30.60, p = 4.33e-143, n = 937 deviations)
  -- matching the resume bullet's "42%" target almost exactly.
- **Corrective action closure rate: 63.9%** of deviations closed (remainder
  Open or Overdue).

All 9 pytest tests pass (`pytest -q` -> `9 passed`).

## Figures

- `output/figures/deviations_by_study.png` -- deviation rate by study (bar)
- `output/figures/investigation_time_before_after.png` -- before/after
  investigation time comparison
- `output/figures/severity_by_category_heatmap.png` -- severity mix by
  parameter category (heatmap)

## What the Tableau dashboard would show

See the "What the Tableau dashboard would show (not built here -- see
README)" section of `output/report.md` for a sheet-by-sheet description
(Deviation Rate by Study, Investigation Time Trend with before/after
reference line, Severity Heatmap by Parameter Category, Corrective Action
Status Tracker, and a cross-sheet filter action) of what would be built in
actual Tableau from `output/tableau_extract.csv`, if Tableau were available.

## Project structure

```
simulate_protocol_deviation_data.py   # 144 params x 6 studies x 12 periods -> data/raw/*.csv
standardize.py                        # unified schema -> data/processed/ and output/tableau_extract.csv
deviation_analysis.py                 # stats, figures, report.md -> output/
run_all.py                            # orchestrates the full pipeline
tests/test_pipeline.py                # pytest checks incl. injected sanity check
```

## Tech stack

- Python 3
- numpy / pandas for data simulation and wrangling
- scipy.stats for the paired t-test on investigation time
- matplotlib for figures (standing in for Tableau views)
- pytest
- Tableau (named in the source resume bullet; **not available/executed in
  this environment** -- see note at the top of this README)
