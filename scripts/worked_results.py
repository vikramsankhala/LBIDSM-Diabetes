"""Reproduce every number in the "Worked results" section of docs/DEMO_USER_MANUAL.md. SYNTHETIC data only.

    python scripts/worked_results.py

Uses the same seeds as scripts/demo_research_pipeline.py, so the numbers match its output where they
overlap. Lines marked (extra) are not printed by the demo. Nothing here is a finding.
"""
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from lbidsm.integrity import apply_gate, audit_cohort
from lbidsm.model_bundle import predict, train_frozen
from lbidsm.prediction import FEATURES_CGM, cohort_split, make_examples
from lbidsm.synthetic_cohort import synthetic_cohort

pd.set_option("display.width", 160)


def heading(text):
    print(f"\n== {text}")


raw = synthetic_cohort(n_subjects=40, days=14, seed=3)
heading("1. The sample data (development cohort)")
print(f"rows {len(raw):,} = {raw.subject_id.nunique()} people x {len(raw) // raw.subject_id.nunique():,} readings")
print("first row:", raw.iloc[0].to_dict())
s0 = raw[raw.subject_id == "S000"]
print(f"S000 readings below 54 mg/dL: {(s0.glucose_mg_dl < 54).sum()}")

dev = apply_gate(raw, audit_cohort(raw))
ex = make_examples(dev)
heading("2. Windows and the nine inputs")
print(f"windows {len(ex):,}; event rate {ex.event_lt54.mean():.4f}; people with an event {ex[ex.event_lt54 == 1].subject_id.nunique()}")
tr, cal, _ = cohort_split(ex)
model = train_frozen(tr, cal, "M2")
print("trained on:", model.trained_on)
w = ex[ex.subject_id == "S000"]
pair = pd.concat([w[w.event_lt54 == 1].head(1), w[w.event_lt54 == 0].head(1)])
cols = ["last_glucose", "mean_60", "min_60", "slope_15", "event_lt54"]
out = pair[cols].round(3)
out["model_M2_risk"] = predict(model, pair).round(3)
print(out.to_string(index=False))

heading("3. Outside cohort (30 new people)")
ext = synthetic_cohort(n_subjects=30, days=14, seed=99)
exx = make_examples(apply_gate(ext, audit_cohort(ext)))
p, y = predict(model, exx), exx.event_lt54.values
print(f"windows {len(exx):,}; events {int(y.sum())} ({y.mean():.3f}); AUROC {roc_auc_score(y, p):.3f}")
print(f"(extra) mean predicted risk: followed by a low {p[y == 1].mean():.3f}, not {p[y == 0].mean():.3f}")
groups = pd.qcut(p, 5, duplicates="drop")
print("(extra) five equal risk groups, predicted vs observed:")
print(pd.DataFrame({"p": p, "y": y, "g": groups}).groupby("g", observed=True)
      .agg(windows=("y", "size"), predicted=("p", "mean"), observed=("y", "mean")).round(4).to_string())
for cut in (0.05, 0.10):
    a = p >= cut
    hit = int((a & (y == 1)).sum())
    print(f"(extra) alert at risk >= {cut}: {int(a.sum())} alerts ({a.mean():.3f} of windows), "
          f"caught {hit} of {int(y.sum())}, share of alerts followed by a low {hit / max(int(a.sum()), 1):.3f}")

heading("4. Known truths for the causal and genetic examples")
rng = np.random.default_rng(0)
n = 3000
x1, x2 = rng.normal(size=n), rng.normal(size=n)
risk = lambda a: 1 / (1 + np.exp(-(-1.6 + 0.9 * x1 - 0.3 * x2 - 0.6 * a)))
print(f"(extra) true average risk reduction in the synthetic trial: {(risk(0) - risk(1)).mean():.4f}  (demo estimate 0.053, 95% CI 0.027 to 0.079)")
print("true genetic effect built into the synthetic variants: 0.4  (demo: IVW 0.349, Egger 0.377)")
print("ranking by hand: B = 0.08 - 10 x 0.002 = 0.060; A = 0.10 - 10 x 0.06 = -0.500; C = 0.20 but ineligible")
