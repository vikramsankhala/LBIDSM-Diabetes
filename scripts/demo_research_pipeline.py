"""End-to-end research demo on SYNTHETIC data. Shows how the modules fit together.

    python scripts/demo_research_pipeline.py --out demo_results

Every number printed here comes from synthetic fixtures. None is a finding.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from lbidsm.access import AccessGuard
from lbidsm.causal import arr_iptw
from lbidsm.evidence import build_pack, release_blockers, write_pack
from lbidsm.genetics import mr_summary
from lbidsm.integrity import apply_gate, audit_cohort, summarise
from lbidsm.model_bundle import predict, train_frozen
from lbidsm.eligibility import apply_eligibility
from lbidsm.policy import ActionOption, DecisionInput, decide
from lbidsm.protocol import HARM_WEIGHT_SCENARIOS, POLICY, QUALIFICATION
from lbidsm.prediction import cohort_split, make_examples
from lbidsm.requirements import REQUIREMENTS
from lbidsm.synthetic_cohort import synthetic_cohort
from lbidsm.utility import Candidate, robust_rank
from lbidsm.validation import external_validation, qualify


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="demo_results")
    ap.add_argument("--bootstrap", type=int, default=300)
    ap.add_argument("--sparse-external", action="store_true",
                    help="External cohort with 14 people and almost no events, like the CGMacros feasibility run")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print("1. L0 data integrity")
    dev_raw = synthetic_cohort(n_subjects=40, days=14, seed=3)
    reports = audit_cohort(dev_raw)
    print("   subjects passing:", sum(r.passed for r in reports), "of", len(reports))
    dev = apply_gate(dev_raw, reports)

    print("2. Train, calibrate, freeze (development cohort)")
    train, cal, _ = cohort_split(make_examples(dev))
    model = train_frozen(train, cal, "M2")
    fingerprint = model.fingerprint()
    (out / "model_M2.json").write_text(model.to_json())
    print("   fingerprint recorded BEFORE external data is opened:", fingerprint[:16], "...")

    print("3. External cohort: qualification gate, then locked validation")
    ext_raw = (synthetic_cohort(n_subjects=14, days=14, seed=99, dip_rate_per_day=0.004) if args.sparse_external
               else synthetic_cohort(n_subjects=30, days=14, seed=99))
    policy = QUALIFICATION  # provisional values from lbidsm.protocol, with reasoning
    gate = qualify(ext_raw, policy)
    print("   gate:", {k: gate[k] for k in ("positive_subjects", "independent_episodes", "planned_halfwidth", "passed")})
    ext_examples = make_examples(apply_gate(ext_raw, audit_cohort(ext_raw)))
    result = external_validation(model, fingerprint, ext_examples, gate, reps=args.bootstrap)
    if result["status"] == "estimated":
        a = result["auroc"]
        print(f"   AUROC {a['point']:.3f} (95% CI {a['lo']:.3f} to {a['hi']:.3f}), patient-clustered; synthetic data")
    else:
        print("   inconclusive:", result["reason"])

    print("4. Patient-specific causal effect (synthetic trial)")
    rng = np.random.default_rng(0)
    n = 3000
    x1, x2 = rng.normal(size=n), rng.normal(size=n)
    a = (rng.random(n) < 1 / (1 + np.exp(-(0.9 * x1 - 0.4 * x2)))).astype(int)
    y = (rng.random(n) < 1 / (1 + np.exp(-(-1.6 + 0.9 * x1 - 0.3 * x2 - 0.6 * a)))).astype(int)
    trial = pd.DataFrame({"x1": x1, "x2": x2, "treated": a, "event": y})
    eff = arr_iptw(trial, "treated", "event", ["x1", "x2"], reps=100)
    print(f"   ARR {eff['arr']:.3f}, 95% CI {eff['arr_ci'][0]:.3f} to {eff['arr_ci'][1]:.3f}; "
          f"balance_ok={eff['balance_ok']}, positivity_ok={eff['positivity_ok']}, E-value {eff['e_value_point']:.2f}")

    print("5. Genetics: Mendelian randomisation on synthetic summary statistics")
    g = np.random.default_rng(1)
    gx = g.uniform(0.04, 0.12, 60) * g.choice([-1, 1], 60)
    snp = [f"rs{i}" for i in range(60)]
    ex = pd.DataFrame({"snp": snp, "ea": "A", "oa": "G", "eaf": 0.3, "beta": gx + g.normal(0, 0.01, 60), "se": 0.01})
    oc = pd.DataFrame({"snp": snp, "ea": "A", "oa": "G", "eaf": 0.3, "beta": 0.4 * gx + g.normal(0, 0.02, 60), "se": 0.02})
    mr = mr_summary(ex, oc)
    print("   IVW", round(mr["ivw"]["beta"], 3), "Egger", round(mr["egger"]["beta"], 3), "warnings:", mr["warnings"])

    print("6. Optimised treatments: robust research ranking")
    d = np.random.default_rng(2)
    cands = [Candidate("option_A", d.normal(0.10, 0.02, 400), {"level2_low": d.normal(0.06, 0.01, 400)}),
             Candidate("option_B", d.normal(0.08, 0.02, 400), {"level2_low": d.normal(0.002, 0.0005, 400)}),
             Candidate("option_C", d.normal(0.20, 0.02, 400), {}, eligible=False, ineligible_reason="excluded by rule table")]
    demo_table = {"version": "demo-table", "approved_by": "DEMO ONLY", "approved_on": "2026-01-01",
                  "actions": {"option_A": [], "option_B": []}}   # option_C is not listed, so it is excluded
    apply_eligibility(cands, {}, demo_table)
    ranked = robust_rank(cands, HARM_WEIGHT_SCENARIOS)
    for r in ranked:
        print(f"   {r['action']}: worst-case utility {r['worst_case_utility']:.3f}, eligible={r['eligible']}")

    print("7. L7 decision policy")
    cfg = POLICY
    options = [ActionOption(r["action"], r["utility"], r["lo"], r["hi"], r["eligible"]) for r in ranked]
    for label, inp in {
        "stable": DecisionInput("p1", "2026-01-01T00:00:00Z", True, 120.0, risk=(0.03, 0.01, 0.06), model_version="M2"),
        "benefit": DecisionInput("p2", "2026-01-01T00:00:00Z", True, 140.0, risk=(0.05, 0.02, 0.09), actions=options, model_version="M2"),
        "bad sensor": DecisionInput("p3", "2026-01-01T00:00:00Z", False, 110.0, ["coverage below policy"], risk=(0.05, 0.02, 0.09)),
        "low reading": DecisionInput("p4", "2026-01-01T00:00:00Z", True, 48.0, risk=(0.5, 0.4, 0.6)),
    }.items():
        print(f"   {label:11s} -> {decide(inp, cfg).category}")

    print("8. Access control and audit")
    guard = AccessGuard()
    guard.check("analyst1", "researcher", "read", "restricted_data", {"mfa": True, "dua_id": "DUA-1", "environment": "laptop"})
    guard.check("analyst1", "researcher", "read", "synthetic_data")
    print("   attempts logged:", len(guard.log.entries), "| chain intact:", guard.log.verify()[0])
    guard.log.save(out / "audit_log.jsonl")

    print("9. Regulatory evidence pack")
    pack = build_pack(intended_use="", model=model, qualification=gate, validation=result, validation_independent=False,
                      data_manifest={}, tripod={}, requirements=REQUIREMENTS, tests_dir=Path("tests"), regulatory_review=None)
    digest = write_pack(pack, out / "evidence_pack.json")
    print("   pack hash:", digest[:16], "...")
    print("   release blockers (expected for a research demo):")
    for b in release_blockers(pack):
        print("    -", b)


if __name__ == "__main__":
    main()
