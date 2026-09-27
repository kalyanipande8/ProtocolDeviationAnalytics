"""
standardize.py

Joins the raw simulated tables (parameter registry, monitoring log,
investigation-time log) into one unified long-format table:
one row per protocol-parameter x study x period.

This unified table is written to:
  - data/processed/unified_deviation_data.csv   (used by the Python analysis)
  - output/tableau_extract.csv                  (the Tableau-ready extract;
    same schema, documented in README.md)

Schema (documented in README.md "Tableau extract schema" section):
  study_id, parameter_id, parameter_name, parameter_category, period,
  deviation_flag, severity, corrective_action_status,
  corrective_action_days_to_close, investigation_time_before_hours,
  investigation_time_after_hours
"""

import os

import pandas as pd

import simulate_protocol_deviation_data as sim

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")


def standardize():
    params = pd.read_csv(os.path.join(RAW_DIR, "parameter_registry.csv"))
    monitoring = pd.read_csv(os.path.join(RAW_DIR, "monitoring_log.csv"))
    investigation = pd.read_csv(os.path.join(RAW_DIR, "investigation_time_log.csv"))

    unified = monitoring.merge(
        params[["parameter_id", "parameter_name"]], on="parameter_id", how="left"
    )

    # attach investigation-time hours for the rows that are deviations
    # (join key: study_id, parameter_id, period -- unique per deviation event)
    unified = unified.merge(
        investigation[[
            "study_id", "parameter_id", "period",
            "investigation_time_before_hours", "investigation_time_after_hours",
        ]],
        on=["study_id", "parameter_id", "period"],
        how="left",
    )

    col_order = [
        "study_id", "parameter_id", "parameter_name", "parameter_category", "period",
        "deviation_flag", "severity", "corrective_action_status",
        "corrective_action_days_to_close",
        "investigation_time_before_hours", "investigation_time_after_hours",
    ]
    unified = unified[col_order].sort_values(
        ["study_id", "parameter_category", "parameter_id", "period"]
    ).reset_index(drop=True)

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    processed_path = os.path.join(PROCESSED_DIR, "unified_deviation_data.csv")
    extract_path = os.path.join(OUTPUT_DIR, "tableau_extract.csv")

    unified.to_csv(processed_path, index=False)
    unified.to_csv(extract_path, index=False)

    print(f"Unified table: {len(unified)} rows "
          f"({unified['study_id'].nunique()} studies x "
          f"{unified['parameter_id'].nunique()} parameters x "
          f"{unified['period'].nunique()} periods).")
    print(f"Written -> {processed_path}")
    print(f"Written -> {extract_path} (Tableau-ready extract)")
    return unified


def main():
    return standardize()


if __name__ == "__main__":
    main()
