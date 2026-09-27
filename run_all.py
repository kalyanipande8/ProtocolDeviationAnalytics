"""
run_all.py

Runs the full pipeline end-to-end:
  1. Simulate raw protocol-deviation monitoring data -> data/raw/
  2. Standardize into unified long-format schema -> data/processed/ and
     output/tableau_extract.csv (Tableau-ready extract)
  3. Analysis: deviation rates, severity, investigation-time reduction,
     corrective-action closure, figures, report.md -> output/

Run with:  python run_all.py

Note: Tableau itself is not installed/scriptable in this environment. This
pipeline produces everything a Tableau dashboard would be built on top of.
See README.md.
"""

import simulate_protocol_deviation_data
import standardize
import deviation_analysis


def main():
    print("--- Simulating protocol deviation monitoring data ---")
    simulate_protocol_deviation_data.simulate()

    print("\n--- Standardizing into unified schema + Tableau extract ---")
    standardize.main()

    print("\n--- Deviation analysis ---")
    deviation_analysis.main()


if __name__ == "__main__":
    main()
