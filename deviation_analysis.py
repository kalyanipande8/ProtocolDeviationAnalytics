"""
deviation_analysis.py

Analysis that stands in for what a Tableau dashboard would compute/show,
built directly on the standardized unified table
(data/processed/unified_deviation_data.csv, identical schema to
output/tableau_extract.csv).

Computes:
  - deviation rate by study
  - deviation rate by parameter category
  - severity breakdown
  - before/after investigation-time reduction %
  - corrective-action closure rate

Writes:
  - output/figures/deviations_by_study.png
  - output/figures/investigation_time_before_after.png
  - output/figures/severity_by_category_heatmap.png
  - output/report.md (real computed numbers + a written description of the
    Tableau dashboard sheets/calculated fields this data would feed)
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

import standardize

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
FIG_DIR = os.path.join(OUTPUT_DIR, "figures")


def load_unified():
    path = os.path.join(PROCESSED_DIR, "unified_deviation_data.csv")
    if not os.path.exists(path):
        standardize.standardize()
    return pd.read_csv(path)


def deviation_rate_by_study(df):
    g = df.groupby("study_id")["deviation_flag"].agg(["sum", "count"])
    g["deviation_rate_pct"] = 100 * g["sum"] / g["count"]
    return g.rename(columns={"sum": "n_deviations", "count": "n_observations"}).reset_index()


def deviation_rate_by_category(df):
    g = df.groupby("parameter_category")["deviation_flag"].agg(["sum", "count"])
    g["deviation_rate_pct"] = 100 * g["sum"] / g["count"]
    return g.rename(columns={"sum": "n_deviations", "count": "n_observations"}).reset_index() \
        .sort_values("deviation_rate_pct", ascending=False)


def severity_breakdown(df):
    dev = df[df["deviation_flag"]]
    counts = dev["severity"].value_counts()
    pct = 100 * counts / counts.sum()
    return pd.DataFrame({"n_deviations": counts, "pct": pct}).reset_index().rename(
        columns={"index": "severity"}
    )


def severity_by_category(df):
    dev = df[df["deviation_flag"]]
    ct = pd.crosstab(dev["parameter_category"], dev["severity"], normalize="index") * 100
    return ct


def investigation_time_reduction(df):
    dev = df[df["deviation_flag"]].dropna(subset=["investigation_time_before_hours"])
    before_mean = dev["investigation_time_before_hours"].mean()
    after_mean = dev["investigation_time_after_hours"].mean()
    reduction_pct = 100 * (before_mean - after_mean) / before_mean
    t_stat, p_val = stats.ttest_rel(
        dev["investigation_time_before_hours"], dev["investigation_time_after_hours"]
    )
    return {
        "before_mean_hours": before_mean,
        "after_mean_hours": after_mean,
        "reduction_pct": reduction_pct,
        "paired_t_stat": t_stat,
        "paired_p_value": p_val,
        "n_deviations": len(dev),
    }


def corrective_action_closure_rate(df):
    dev = df[df["deviation_flag"]]
    counts = dev["corrective_action_status"].value_counts()
    total = counts.sum()
    closure_rate_pct = 100 * counts.get("Closed", 0) / total
    return closure_rate_pct, counts


def make_figures(df, dev_by_study, inv, sev_by_cat):
    os.makedirs(FIG_DIR, exist_ok=True)

    # Figure 1: deviations by study (bar) -- stand-in for Tableau Sheet 1
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(dev_by_study["study_id"], dev_by_study["deviation_rate_pct"], color="#4C72B0")
    ax.set_ylabel("Deviation rate (%)")
    ax.set_xlabel("Study")
    ax.set_title("Deviation Rate by Study")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "deviations_by_study.png"), dpi=150)
    plt.close(fig)

    # Figure 2: before/after investigation time comparison -- Sheet 2 stand-in
    dev = df[df["deviation_flag"]].dropna(subset=["investigation_time_before_hours"])
    fig, ax = plt.subplots(figsize=(7, 5))
    means = [dev["investigation_time_before_hours"].mean(), dev["investigation_time_after_hours"].mean()]
    bars = ax.bar(["Before dashboard", "After dashboard"], means, color=["#C44E52", "#55A868"])
    for b, m in zip(bars, means):
        ax.text(b.get_x() + b.get_width() / 2, m + 0.3, f"{m:.1f}h", ha="center")
    ax.set_ylabel("Mean investigation time (hours)")
    ax.set_title(f"Investigation Time: Before vs After Proactive Dashboard\n"
                 f"({inv['reduction_pct']:.1f}% reduction)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "investigation_time_before_after.png"), dpi=150)
    plt.close(fig)

    # Figure 3: severity heatmap by parameter category -- Sheet 3 stand-in
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(sev_by_cat.values, aspect="auto", cmap="Reds")
    ax.set_xticks(range(len(sev_by_cat.columns)))
    ax.set_xticklabels(sev_by_cat.columns)
    ax.set_yticks(range(len(sev_by_cat.index)))
    ax.set_yticklabels(sev_by_cat.index, fontsize=8)
    ax.set_title("Severity Mix by Parameter Category (% of deviations)")
    for i in range(sev_by_cat.shape[0]):
        for j in range(sev_by_cat.shape[1]):
            ax.text(j, i, f"{sev_by_cat.values[i, j]:.0f}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=ax, label="% of deviations")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "severity_by_category_heatmap.png"), dpi=150)
    plt.close(fig)


def write_report(dev_by_study, dev_by_cat, sev, inv, closure_rate, ca_counts, n_params, n_studies):
    lines = []
    lines.append("# Protocol Deviation Analysis Report\n")
    lines.append("All numbers below come directly from an actual run of `python run_all.py` "
                  "against synthetically simulated data (fixed random seed). "
                  "No Tableau workbook was built or run to produce this report -- "
                  "see README.md for why.\n")

    lines.append("## Scope\n")
    lines.append(f"- **{n_params} protocol parameters** monitored across **{n_studies} studies**, "
                  "12 monthly periods each.\n")

    lines.append("## Deviation rate by study\n")
    lines.append(dev_by_study.to_markdown(index=False, floatfmt=".2f") + "\n")

    lines.append("## Deviation rate by parameter category\n")
    lines.append(dev_by_cat.to_markdown(index=False, floatfmt=".2f") + "\n")

    lines.append("## Severity breakdown (all deviations)\n")
    lines.append(sev.to_markdown(index=False, floatfmt=".2f") + "\n")

    lines.append("## Investigation time: before vs after proactive dashboard\n")
    lines.append(
        f"- Before (mean): **{inv['before_mean_hours']:.2f} hours**\n"
        f"- After (mean): **{inv['after_mean_hours']:.2f} hours**\n"
        f"- Reduction: **{inv['reduction_pct']:.1f}%** "
        f"(paired t = {inv['paired_t_stat']:.2f}, p = {inv['paired_p_value']:.2e}, "
        f"n = {inv['n_deviations']} deviations)\n"
    )

    lines.append("## Corrective action closure\n")
    lines.append(f"- Overall closure rate: **{closure_rate:.1f}%**\n")
    lines.append(ca_counts.rename_axis("status").reset_index(name="count")
                 .to_markdown(index=False) + "\n")

    lines.append("## What the Tableau dashboard would show (not built here -- see README)\n")
    lines.append(
        "If built in actual Tableau against `output/tableau_extract.csv`, the dashboard "
        "would consist of:\n\n"
        "- **Sheet 1 - Deviation Rate by Study (bar chart):** one bar per study, "
        "`SUM([deviation_flag]) / COUNTD([study_id]+[parameter_id]+[period])`, "
        "colored by rate threshold (calculated field `Deviation Rate Flag` = "
        "IF rate > study average THEN 'Above Average' ELSE 'At/Below Average').\n"
        "- **Sheet 2 - Investigation Time Trend (line, before/after reference line):** "
        "`investigation_time_before_hours` and `investigation_time_after_hours` as two "
        "measures on a dual-axis line chart over `period`, with a reference line at the "
        "42% target reduction band, so investigators can see the trend converging.\n"
        "- **Sheet 3 - Severity Heatmap by Parameter Category:** `parameter_category` x "
        "`severity` crosstab as a heatmap, highlighting which categories skew toward "
        "Critical severity for proactive corrective-action prioritization.\n"
        "- **Sheet 4 - Corrective Action Status Tracker:** a stacked bar / Gantt-style view "
        "of `corrective_action_status` (Closed/Open/Overdue) by study and category, with a "
        "calculated field `Days Open` = TODAY() - [deviation_date] for still-open items, "
        "used for the proactive corrective-action planning workflow.\n"
        "- A dashboard-level filter action linking Sheet 1 -> Sheet 3/4 so clicking a study "
        "bar filters the severity heatmap and CA tracker to that study.\n"
    )

    with open(os.path.join(OUTPUT_DIR, "report.md"), "w") as f:
        f.write("\n".join(lines))


def main():
    df = load_unified()

    dev_by_study = deviation_rate_by_study(df)
    dev_by_cat = deviation_rate_by_category(df)
    sev = severity_breakdown(df)
    sev_by_cat = severity_by_category(df)
    inv = investigation_time_reduction(df)
    closure_rate, ca_counts = corrective_action_closure_rate(df)

    n_params = df["parameter_id"].nunique()
    n_studies = df["study_id"].nunique()

    make_figures(df, dev_by_study, inv, sev_by_cat)
    write_report(dev_by_study, dev_by_cat, sev, inv, closure_rate, ca_counts, n_params, n_studies)

    print(f"Parameters: {n_params}, Studies: {n_studies}")
    print("Deviation rate by study:")
    print(dev_by_study.to_string(index=False))
    print("\nDeviation rate by category:")
    print(dev_by_cat.to_string(index=False))
    print("\nSeverity breakdown:")
    print(sev.to_string(index=False))
    print(f"\nInvestigation time before: {inv['before_mean_hours']:.2f}h, "
          f"after: {inv['after_mean_hours']:.2f}h, "
          f"reduction: {inv['reduction_pct']:.1f}% "
          f"(p={inv['paired_p_value']:.2e})")
    print(f"\nCorrective action closure rate: {closure_rate:.1f}%")
    print("\nWritten -> output/report.md, output/figures/*.png")

    return {
        "n_params": n_params,
        "n_studies": n_studies,
        "dev_by_study": dev_by_study,
        "dev_by_cat": dev_by_cat,
        "sev": sev,
        "inv": inv,
        "closure_rate": closure_rate,
    }


if __name__ == "__main__":
    main()
