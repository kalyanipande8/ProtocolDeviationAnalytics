"""
simulate_protocol_deviation_data.py

Simulates protocol-deviation monitoring data for a portfolio project standing
in for a Tableau "Protocol Deviation Tracking with Corrective Actions"
dashboard. Tableau itself is NOT used/available in this environment -- see
README.md. This script only produces the synthetic raw data.

Design:
- 6 clinical studies
- 144 protocol parameters monitored, grouped into 8 categories of 18
  parameters each (visit-window compliance, inclusion/exclusion criteria,
  dosing-schedule adherence, informed-consent timing, lab-sample-handling
  timing, concomitant-medication documentation, adverse-event reporting
  timeliness, source-document verification)
- Each parameter x study monitored over 12 monthly periods
- Deviations occur at a category-specific rate; each deviation gets a
  severity (Minor/Major/Critical) and a corrective-action record (status +
  days-to-close)
- A separate "investigation time" dataset simulates individual deviation
  investigations under a "before proactive dashboard" regime and an "after
  proactive dashboard / corrective-action planning" regime, calibrated so
  the mean investigation time drops by ~42%, matching the resume bullet.

Fixed random seed -> fully reproducible.
"""

import os

import numpy as np
import pandas as pd

SEED = 42
N_STUDIES = 6
N_PERIODS = 12  # monthly periods over 1 year
PARAM_CATEGORIES = {
    "Visit Window Compliance": 18,
    "Inclusion/Exclusion Criteria": 18,
    "Dosing Schedule Adherence": 18,
    "Informed Consent Timing": 18,
    "Lab Sample Handling Timing": 18,
    "Concomitant Medication Documentation": 18,
    "Adverse Event Reporting Timeliness": 18,
    "Source Document Verification": 18,
}
N_PARAMETERS = sum(PARAM_CATEGORIES.values())  # 144

RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "raw")

STUDY_IDS = [f"STUDY-{i+1:02d}" for i in range(N_STUDIES)]

# per-category baseline monthly deviation rate (probability a given
# parameter x study x period has >=1 deviation) -- some categories are
# inherently more deviation-prone than others
CATEGORY_BASE_RATE = {
    "Visit Window Compliance": 0.16,
    "Inclusion/Exclusion Criteria": 0.05,
    "Dosing Schedule Adherence": 0.09,
    "Informed Consent Timing": 0.04,
    "Lab Sample Handling Timing": 0.13,
    "Concomitant Medication Documentation": 0.11,
    "Adverse Event Reporting Timeliness": 0.07,
    "Source Document Verification": 0.10,
}

# per-study multiplier -- some sites/studies run tighter operations than others
STUDY_MULTIPLIER = {
    "STUDY-01": 0.85,
    "STUDY-02": 1.10,
    "STUDY-03": 0.95,
    "STUDY-04": 1.25,
    "STUDY-05": 0.75,
    "STUDY-06": 1.05,
}

SEVERITY_LEVELS = ["Minor", "Major", "Critical"]
# category-specific severity distributions (rows sum to 1)
CATEGORY_SEVERITY_WEIGHTS = {
    "Visit Window Compliance": [0.70, 0.25, 0.05],
    "Inclusion/Exclusion Criteria": [0.20, 0.45, 0.35],
    "Dosing Schedule Adherence": [0.35, 0.45, 0.20],
    "Informed Consent Timing": [0.15, 0.40, 0.45],
    "Lab Sample Handling Timing": [0.60, 0.30, 0.10],
    "Concomitant Medication Documentation": [0.65, 0.30, 0.05],
    "Adverse Event Reporting Timeliness": [0.25, 0.40, 0.35],
    "Source Document Verification": [0.75, 0.20, 0.05],
}

CA_STATUSES = ["Closed", "Open", "Overdue"]


def _build_parameter_registry(rng):
    rows = []
    pid = 1
    for category, n in PARAM_CATEGORIES.items():
        for j in range(1, n + 1):
            rows.append({
                "parameter_id": f"P{pid:03d}",
                "parameter_name": f"{category} - Check {j:02d}",
                "parameter_category": category,
            })
            pid += 1
    return pd.DataFrame(rows)


def simulate_monitoring_data(rng):
    """One row per study x parameter x period, with deviation flag/severity/CA fields."""
    params = _build_parameter_registry(rng)
    rows = []
    for study in STUDY_IDS:
        study_mult = STUDY_MULTIPLIER[study]
        for _, prow in params.iterrows():
            category = prow["parameter_category"]
            base_rate = CATEGORY_BASE_RATE[category]
            rate = min(base_rate * study_mult, 0.9)
            sev_weights = CATEGORY_SEVERITY_WEIGHTS[category]
            for period in range(1, N_PERIODS + 1):
                deviation = rng.random() < rate
                severity = None
                ca_status = None
                ca_days_to_close = np.nan
                if deviation:
                    severity = rng.choice(SEVERITY_LEVELS, p=sev_weights)
                    # closure outcome depends on severity: critical gets
                    # prioritized (faster/likelier closure), minor lags
                    if severity == "Critical":
                        ca_status = rng.choice(CA_STATUSES, p=[0.80, 0.15, 0.05])
                        mean_days = 7
                    elif severity == "Major":
                        ca_status = rng.choice(CA_STATUSES, p=[0.70, 0.20, 0.10])
                        mean_days = 14
                    else:
                        ca_status = rng.choice(CA_STATUSES, p=[0.60, 0.25, 0.15])
                        mean_days = 21
                    if ca_status == "Closed":
                        ca_days_to_close = max(1, rng.normal(mean_days, mean_days * 0.35))
                rows.append({
                    "study_id": study,
                    "parameter_id": prow["parameter_id"],
                    "parameter_category": category,
                    "period": period,
                    "deviation_flag": deviation,
                    "severity": severity,
                    "corrective_action_status": ca_status,
                    "corrective_action_days_to_close": ca_days_to_close,
                })
    monitoring = pd.DataFrame(rows)
    return params, monitoring


def simulate_investigation_time(rng, monitoring):
    """
    For every deviation in `monitoring`, simulate an investigation-time
    (hours) record under BOTH a 'before' (manual/reactive) regime and an
    'after' (proactive dashboard + corrective-action planning) regime.

    These are not the same physical investigations happening twice --
    they represent two comparable operational periods (pre- and
    post-dashboard rollout) with matched deviation-severity mix, which is
    the standard way this kind of "reduced investigation time X%" claim is
    actually measured operationally (comparable cohorts, not a paired
    diff-in-diff on identical events).
    """
    deviations = monitoring[monitoring["deviation_flag"]].reset_index(drop=True)

    # base investigation time (hours) by severity, BEFORE proactive dashboard
    before_base = {"Minor": 6.0, "Major": 14.0, "Critical": 26.0}
    # calibrated reduction factor so overall mean lands close to 42%
    reduction_factor = 0.58  # after = before * reduction_factor -> ~42% reduction

    records = []
    for _, row in deviations.iterrows():
        sev = row["severity"]
        base_mean = before_base[sev]
        before_hours = max(0.5, rng.normal(base_mean, base_mean * 0.25))
        after_mean = base_mean * reduction_factor
        after_hours = max(0.5, rng.normal(after_mean, after_mean * 0.25))
        records.append({
            "study_id": row["study_id"],
            "parameter_id": row["parameter_id"],
            "parameter_category": row["parameter_category"],
            "period": row["period"],
            "severity": sev,
            "investigation_time_before_hours": round(before_hours, 2),
            "investigation_time_after_hours": round(after_hours, 2),
        })
    return pd.DataFrame(records)


def simulate():
    rng = np.random.default_rng(SEED)
    os.makedirs(RAW_DIR, exist_ok=True)

    params, monitoring = simulate_monitoring_data(rng)
    investigation = simulate_investigation_time(rng, monitoring)

    params.to_csv(os.path.join(RAW_DIR, "parameter_registry.csv"), index=False)
    monitoring.to_csv(os.path.join(RAW_DIR, "monitoring_log.csv"), index=False)
    investigation.to_csv(os.path.join(RAW_DIR, "investigation_time_log.csv"), index=False)

    print(f"Simulated {len(params)} protocol parameters across {N_STUDIES} studies "
          f"over {N_PERIODS} periods.")
    print(f"Monitoring log rows: {len(monitoring)}")
    print(f"Deviations: {int(monitoring['deviation_flag'].sum())}")
    print(f"Investigation-time records: {len(investigation)}")
    return params, monitoring, investigation


if __name__ == "__main__":
    simulate()
