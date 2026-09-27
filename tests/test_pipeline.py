import os
import sys

import pandas as pd
import pytest

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

import simulate_protocol_deviation_data as sim  # noqa: E402
import standardize  # noqa: E402
import deviation_analysis as da  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def ensure_pipeline_ran():
    sim.simulate()
    standardize.standardize()
    yield


def test_144_parameters_present():
    params = pd.read_csv(os.path.join(sim.RAW_DIR, "parameter_registry.csv"))
    assert params["parameter_id"].nunique() == 144
    assert len(params) == 144


def test_6_studies_present():
    monitoring = pd.read_csv(os.path.join(sim.RAW_DIR, "monitoring_log.csv"))
    assert monitoring["study_id"].nunique() == 6


def test_unified_table_one_row_per_param_study_period():
    unified = pd.read_csv(os.path.join(standardize.PROCESSED_DIR, "unified_deviation_data.csv"))
    expected_rows = 144 * 6 * sim.N_PERIODS
    assert len(unified) == expected_rows
    assert not unified.duplicated(["study_id", "parameter_id", "period"]).any()


def test_tableau_extract_created_with_expected_schema():
    extract_path = os.path.join(standardize.OUTPUT_DIR, "tableau_extract.csv")
    assert os.path.exists(extract_path)
    extract = pd.read_csv(extract_path)
    expected_cols = [
        "study_id", "parameter_id", "parameter_name", "parameter_category", "period",
        "deviation_flag", "severity", "corrective_action_status",
        "corrective_action_days_to_close",
        "investigation_time_before_hours", "investigation_time_after_hours",
    ]
    assert list(extract.columns) == expected_cols
    assert len(extract) == 144 * 6 * sim.N_PERIODS


def test_investigation_time_reduction_within_reasonable_band():
    results = da.main()
    reduction = results["inv"]["reduction_pct"]
    assert 30 <= reduction <= 50, f"reduction {reduction:.1f}% outside expected band"


def test_severity_values_are_valid():
    unified = pd.read_csv(os.path.join(standardize.PROCESSED_DIR, "unified_deviation_data.csv"))
    dev = unified[unified["deviation_flag"]]
    assert set(dev["severity"].dropna().unique()) <= {"Minor", "Major", "Critical"}


def test_corrective_action_status_valid_for_deviations():
    unified = pd.read_csv(os.path.join(standardize.PROCESSED_DIR, "unified_deviation_data.csv"))
    dev = unified[unified["deviation_flag"]]
    assert set(dev["corrective_action_status"].dropna().unique()) <= {"Closed", "Open", "Overdue"}
    # every deviation should have a CA status assigned
    assert dev["corrective_action_status"].notna().all()


def test_injected_sanity_check_higher_risk_category_has_higher_deviation_rate():
    """Injected sanity check: Visit Window Compliance was simulated with a
    substantially higher base deviation rate (0.16) than Informed Consent
    Timing (0.04), so it must show a materially higher observed rate."""
    unified = pd.read_csv(os.path.join(standardize.PROCESSED_DIR, "unified_deviation_data.csv"))
    rates = unified.groupby("parameter_category")["deviation_flag"].mean()
    assert rates["Visit Window Compliance"] > rates["Informed Consent Timing"]


def test_non_deviation_rows_have_no_severity_or_ca_data():
    unified = pd.read_csv(os.path.join(standardize.PROCESSED_DIR, "unified_deviation_data.csv"))
    non_dev = unified[~unified["deviation_flag"]]
    assert non_dev["severity"].isna().all()
    assert non_dev["corrective_action_status"].isna().all()
