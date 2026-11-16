import numpy as np
import pandas as pd
import pytest
from lbidsm.covariates import prepare_covariates, attach_covariates, synthetic_covariates
from lbidsm.endotypes import EndotypeClusterer
from lbidsm.prediction import make_examples, benchmark_extended


def cohort(n=40, length=260, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for sid in range(n):
        t = pd.date_range("2026-01-01", periods=length, freq="15min", tz="UTC")
        g = 95 + 40 * np.sin(np.arange(length) / 14 + sid * 0.4) + rng.normal(0, 9, length) - (sid % 4 == 0) * 25
        rows.extend({"subject_id": str(sid), "timestamp": ts, "glucose_mg_dl": float(v)} for ts, v in zip(t, g))
    return pd.DataFrame(rows)


def test_homa_ir_derived_and_one_row_per_subject():
    cov = prepare_covariates(pd.DataFrame({"subject_id": ["a", "b"], "fasting_glucose_mg_dl": [90, 135],
                                            "fasting_insulin_uU_ml": [4.5, 9.0]}))
    assert cov.homa_ir.round(3).tolist() == [1.0, 3.0]
    with pytest.raises(ValueError):
        prepare_covariates(pd.DataFrame({"subject_id": ["a", "a"], "bmi": [20, 21]}))


def test_attach_refuses_low_coverage():
    ex = make_examples(cohort(10))
    with pytest.raises(ValueError):
        attach_covariates(ex, synthetic_covariates(["0", "1"]))


def test_clusters_recover_planted_groups_and_use_train_only():
    cov = synthetic_covariates([str(i) for i in range(90)], seed=3, separation=2.5)
    clus = EndotypeClusterer(seed=1, n_boot=10).fit(cov)
    assert clus.k_ in (2, 3)
    assert clus.quality_["silhouette"] > 0.15
    assert 1 <= len(clus.pca_summary_) <= 6 and clus.loadings_.shape[0] == len(clus.columns_)
    lab = clus.transform(cov)
    assert lab.nunique() == 3 and (lab.index == cov.subject_id.values).all()


def test_too_few_subjects_fail_closed():
    with pytest.raises(ValueError):
        EndotypeClusterer().fit(synthetic_covariates([str(i) for i in range(8)]))


def test_extended_benchmark_runs_and_reports_all_models():
    ex = make_examples(cohort(40))
    cov = synthetic_covariates(ex.subject_id.unique())
    scores, rep = benchmark_extended(ex, cov)
    assert {"cgm_history", "cgm_plus_metabolic", "cgm_plus_metabolic_genetic_treatment"} <= set(scores.model)
    assert "endotype_quality" in rep and set(rep["subjects"]) == {"train", "calibration", "test"}


def test_confounder_screen_flags_planted_confounder_and_skips_mediators():
    from lbidsm.confounders import screen_confounders
    rng = np.random.default_rng(0)
    n = 400
    age = rng.normal(0, 1, n)
    exposure = 0.7 * age + rng.normal(0, 1, n)          # age drives exposure
    p = 1 / (1 + np.exp(-(0.9 * age - 0.5)))             # and outcome; exposure has no direct effect
    tab = pd.DataFrame({"subject_id": range(n), "prs_t2d": exposure, "age_years": age,
                        "bmi": exposure + rng.normal(0, 0.5, n), "egfr": rng.normal(0, 1, n),
                        "any_event": (rng.random(n) < p).astype(int)})
    out = screen_confounders(tab, "prs_t2d").set_index("variable")
    assert out.loc["age_years", "recommended_adjustment"]
    assert not out.loc["bmi", "recommended_adjustment"] and "mediator" in out.loc["bmi", "note"]
    assert not out.loc["egfr", "recommended_adjustment"]
