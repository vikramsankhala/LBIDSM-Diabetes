"""Run the benchmark on an independently obtained, verified CGM cohort.

Input is a harmonized long-format CSV with subject_id,timestamp,glucose_mg_dl.
No network downloads are performed; provenance is recorded via SHA-256.
"""
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd
from lbidsm.prediction import make_examples, benchmark

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True, help="Harmonized public CGM CSV, patient IDs preserved")
    p.add_argument("--dataset-name", required=True)
    p.add_argument("--source-url", required=True, help="Publisher or dataset DOI URL")
    p.add_argument("--out", default="benchmark_results")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--horizon-minutes", type=int, default=60)
    a = p.parse_args()
    source = Path(a.csv)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    df = pd.read_csv(source)
    examples = make_examples(df, horizon_minutes=a.horizon_minutes)
    if examples.empty:
        raise SystemExit("No eligible windows; inspect sampling rate, gaps, and data schema")
    scores, meta = benchmark(examples, seed=a.seed)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    meta.update({
        "dataset_name": a.dataset_name, "source_url": a.source_url,
        "sha256": digest, "horizon_minutes": a.horizon_minutes,
        "n_eligible_windows": len(examples),
        "warning": "Retrospective CGM-sample surrogate, not a validated clinical hypoglycemia prediction model.",
    })
    scores.to_csv(out / "metrics.csv", index=False)
    (out / "provenance.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(scores.to_string(index=False))
    print("Saved:", out.resolve())

if __name__ == "__main__":
    main()
