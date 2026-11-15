"""Write (or check) the synthetic teaching sample in data/sample/. SYNTHETIC data only.

    python scripts/make_sample_data.py            # write the files
    python scripts/make_sample_data.py --check    # fail if the committed files differ

Files:
  synthetic_cgm_sample.csv  five synthetic people (S000 to S004), 14 days, one reading every 5 minutes
  example_windows.csv       20 hour-long windows from S000 with the nine model inputs, the outcome and
                            the risk the demo's frozen M2 model gives (10 followed by a low, 10 not)

The people are the first five of the demo's 40-person development cohort (seed 3), so the numbers in
docs/DEMO_USER_MANUAL.md ("Worked results") can be traced to real rows.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

from lbidsm.integrity import apply_gate, audit_cohort
from lbidsm.model_bundle import predict, train_frozen
from lbidsm.prediction import FEATURES_CGM, cohort_split, make_examples
from lbidsm.synthetic_cohort import synthetic_cohort

OUT = Path("data/sample")
N_SAMPLE_PEOPLE = 5


def build() -> dict:
    raw = synthetic_cohort(n_subjects=40, days=14, seed=3)
    dev = apply_gate(raw, audit_cohort(raw))
    examples = make_examples(dev)
    train, cal, _ = cohort_split(examples)
    model = train_frozen(train, cal, "M2")

    keep = sorted(raw.subject_id.unique())[:N_SAMPLE_PEOPLE]
    cgm = raw[raw.subject_id.isin(keep)].copy()
    cgm["glucose_mg_dl"] = cgm["glucose_mg_dl"].round(1)

    s0 = examples[examples.subject_id == keep[0]]
    pick = pd.concat([s0[s0.event_lt54 == 1].head(10), s0[s0.event_lt54 == 0].head(10)])
    windows = pick[["subject_id", "as_of"] + FEATURES_CGM + ["event_lt54"]].copy()
    windows["model_M2_risk"] = predict(model, windows).round(4)
    windows = windows.round(3).sort_values("as_of")
    return {"synthetic_cgm_sample.csv": cgm, "example_windows.csv": windows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    files = build()
    bad = 0
    for name, frame in files.items():
        text = frame.to_csv(index=False, lineterminator="\n")
        path = OUT / name
        if args.check:
            if not path.exists() or path.read_text() != text:
                print(f"DIFFERS {path}")
                bad += 1
        else:
            OUT.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            print(f"wrote {path} ({len(frame)} rows)")
    if args.check:
        print("Sample data match." if not bad else f"{bad} file(s) differ: rerun without --check.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
