import numpy as np
import pandas as pd
import pytest
from lbidsm import mr
from lbidsm.endotype_schema import coverage_report, check_homa2, preliminary_endotypes, suggest_names, ROUTINE_SIX


def test_wald_ratio_exact():
    df = pd.DataFrame({"snp": ["a"], "beta_x": [0.2], "se_x": [0.01], "beta_y": [0.1], "se_y": [0.02]})
    r = mr.wald_ratio(df)
    assert r["beta"] == pytest.approx(0.5) and r["se"] == pytest.approx(0.1)


def test_ivw_recovers_effect_and_sensitivity_methods_agree():
    d = mr.synthetic_mr_data(n_snps=12, true_beta=0.4, seed=1)
    tab = mr.run_mr(d).set_index("method")
    for m in ["IVW (random effects)", "MR-Egger", "Weighted median"]:
        assert abs(tab.loc[m, "beta"] - 0.4) < 0.25
    assert tab.loc["IVW (random effects)", "p"] < 0.05


def test_null_effect_not_significant_most_seeds():
    hits = sum(mr.ivw(mr.synthetic_mr_data(8, 0.0, seed=s)).get("p", 1) < 0.05 for s in range(40))
    assert hits <= 8  # nominal 5% of 40 is 2; generous bound


def test_egger_intercept_detects_directional_pleiotropy():
    d = mr.synthetic_mr_data(n_snps=30, true_beta=0.3, seed=1, pleiotropy=0.03)
    assert mr.mr_egger(d)["intercept_p"] < 0.05
    clean = mr.synthetic_mr_data(n_snps=30, true_beta=0.3, seed=1, pleiotropy=0.0)
    assert mr.mr_egger(clean)["intercept_p"] > 0.05


def test_weak_instruments_flagged():
    d = mr.synthetic_mr_data(4, seed=3)
    d.loc[0, "beta_x"] = 0.001
    assert instrument_flag(d)


def instrument_flag(d):
    return bool(mr.instrument_strength(d).weak.iloc[0])


def test_colocalisation_shared_vs_distinct():
    shared = mr.colocalisation(mr.synthetic_locus(shared=True, seed=4))
    distinct = mr.colocalisation(mr.synthetic_locus(shared=False, seed=4))
    assert shared["PP.H4"] > 0.8 and shared["colocalised"]
    assert distinct["PP.H3"] > distinct["PP.H4"] and not distinct["colocalised"]
    assert sum(shared[f"PP.H{i}"] for i in range(5)) == pytest.approx(1.0)


def test_colocalisation_needs_whole_locus():
    with pytest.raises(ValueError):
        mr.colocalisation(mr.synthetic_mr_data(5))


def test_reverse_mr_flags_real_reverse_effect():
    rev = mr.synthetic_mr_data(10, true_beta=0.5, seed=5)
    assert mr.reverse_mr(rev)["reverse_signal"]
    none = mr.synthetic_mr_data(10, true_beta=0.0, seed=6)
    assert not mr.reverse_mr(none)["reverse_signal"]


def test_safety_read_across_flags_only_the_real_trait():
    frames = []
    for trait, b in [("ckd", 0.5), ("fracture", 0.0), ("asthma", 0.0)]:
        t = mr.synthetic_mr_data(8, true_beta=b, seed=7)
        t["trait"] = trait
        frames.append(t)
    res = mr.safety_read_across(pd.concat(frames))
    assert res[res.flag].trait.tolist() == ["ckd"]


def test_stratified_mr_detects_difference_between_strata():
    tabs = {"endotype_A": mr.synthetic_mr_data(10, 0.6, seed=8), "endotype_B": mr.synthetic_mr_data(10, 0.0, seed=9)}
    out = mr.stratified_mr(tabs)
    assert out["differs_between_strata"]
    same = mr.stratified_mr({"A": mr.synthetic_mr_data(10, 0.4, seed=10), "B": mr.synthetic_mr_data(10, 0.4, seed=11)})
    assert not same["differs_between_strata"]
    with pytest.raises(ValueError):
        mr.stratified_mr({"only": mr.synthetic_mr_data(5)})


def test_target_filter_passes_a_clean_target_and_fails_closed_without_evidence():
    d = mr.synthetic_mr_data(12, 0.4, seed=12)
    region = mr.synthetic_locus(shared=True, seed=12)
    rev = mr.synthetic_mr_data(10, 0.0, seed=13)
    ok = mr.target_filter(d, region=region, disease_instruments=rev)
    assert ok["verdict"].startswith("hypothesis_supported"), ok["reasons"]
    missing = mr.target_filter(d)  # no colocalisation, no reverse MR
    assert missing["verdict"] == "not_supported"
    assert "not met: colocalised" in missing["reasons"] and "not met: no_reverse_signal" in missing["reasons"]
    bad_region = mr.target_filter(d, region=mr.synthetic_locus(shared=False, seed=12), disease_instruments=rev)
    assert bad_region["verdict"] == "not_supported"


def test_input_validation():
    with pytest.raises(ValueError):
        mr.ivw(pd.DataFrame({"snp": ["a"], "beta_x": [1.0]}))
    d = mr.synthetic_mr_data(3)
    d.loc[0, "se_y"] = 0
    with pytest.raises(ValueError):
        mr.ivw(d)


def _toy_endotype_table(n=240, seed=0):
    rng = np.random.default_rng(seed)
    centres = {"SIDD": (45, 28, 10.5, 40, 1.2), "SIRD": (55, 34, 7.8, 150, 3.5),
               "MOD": (50, 36, 7.2, 110, 1.9), "MARD": (68, 27, 6.9, 90, 1.3)}
    rows = []
    for i, (k, c) in enumerate(centres.items()):
        for j in range(n // 4):
            rows.append({"subject_id": f"{k}{j}", "gad_antibody_positive": 0,
                         **dict(zip(["age_at_diagnosis", "bmi", "hba1c_percent", "homa2_b", "homa2_ir"],
                                    rng.normal(c, [3, 1.5, 0.5, 8, 0.25])))})
    rows += [{"subject_id": f"S{j}", "gad_antibody_positive": 1, "age_at_diagnosis": 30, "bmi": 24,
              "hba1c_percent": 11, "homa2_b": 20, "homa2_ir": 1.0} for j in range(8)]
    return pd.DataFrame(rows)


def test_schema_coverage_and_homa2_warning():
    df = pd.DataFrame({"subject_id": ["a"], "bmi": [30.0], "egfr": [80.0]})
    cov = coverage_report(df)
    assert set(cov.layer) == {"routine_six", "L2_clinical_vulnerability", "L3_cgm_metrics", "L4_dynamic_stability_exploratory"}
    assert cov.set_index("variable").loc["bmi", "present"]
    assert check_homa2(df)


def test_preliminary_endotypes_sets_aside_said_and_names_clusters():
    df = _toy_endotype_table()
    labels, profile, quality = preliminary_endotypes(df, k=4)
    assert (labels == "SAID_candidate").sum() == 8
    assert quality["k"] == 4
    names = suggest_names(profile)
    assert sorted(v.split(" ")[0] for v in names.values()) == ["MARD", "MOD", "SIDD", "SIRD"]
    with pytest.raises(ValueError):
        preliminary_endotypes(df.drop(columns=["bmi"]))
