"""CGM-only vs CGM + baseline metabolic/genetic covariates vs preliminary endotypes, plus PCA and confounder screen.

Inputs: harmonised CGM CSV (subject_id,timestamp,glucose_mg_dl) and a one-row-per-subject covariate CSV
(see lbidsm.covariates for column names). Research only; no network access.
"""
import argparse, json
from pathlib import Path
import pandas as pd
from lbidsm.prediction import make_examples, benchmark_extended
from lbidsm.confounders import subject_outcomes, screen_confounders

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cgm", required=True); p.add_argument("--covariates", required=True)
    p.add_argument("--out", default="covariate_results"); p.add_argument("--seed", type=int, default=42)
    p.add_argument("--exposure", default="prs_t2d", help="column to screen for confounders")
    a = p.parse_args()
    ex = make_examples(pd.read_csv(a.cgm)); cov = pd.read_csv(a.covariates)
    scores, rep = benchmark_extended(ex, cov, seed=a.seed)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    scores.to_csv(out / "metrics.csv", index=False)
    (out / "report.json").write_text(json.dumps(rep, indent=2, default=float))
    tab = subject_outcomes(ex).join(cov.assign(subject_id=cov.subject_id.astype(str)).set_index("subject_id"))
    if a.exposure in tab.columns:
        try:
            screen_confounders(tab.reset_index(), a.exposure).to_csv(out / "confounder_screen.csv", index=False)
        except ValueError as e:
            print("Confounder screen skipped:", e)
    print(scores.to_string(index=False)); print(json.dumps(rep["endotype_quality"], indent=2))

if __name__ == "__main__":
    main()
