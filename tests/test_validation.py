import numpy as np
import pandas as pd
import pytest

from lbidsm.model_bundle import train_frozen
from lbidsm.prediction import cohort_split, make_examples
from lbidsm.synthetic_cohort import synthetic_cohort
from lbidsm.validation import (QualificationPolicy, calibration_slope_intercept, cluster_bootstrap,
                               episode_starts, external_validation, planning_halfwidth, qualify)


def series(values):
    return pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=len(values), freq="5min", tz="UTC"),
                         "glucose_mg_dl": values})


POLICY = QualificationPolicy(min_positive_subjects=3, min_independent_episodes=10,
                             max_planned_halfwidth=0.25, planning_auroc=0.75, assumed_icc=0.3)


def test_two_dips_far_apart_are_two_episodes():
    # REQ: VAL-001
    v = [100] * 10 + [50] * 3 + [100] * 20 + [50] * 2 + [100] * 5
    assert len(episode_starts(series(v), POLICY)) == 2


def test_dips_close_together_are_one_episode():
    # REQ: VAL-002
    v = [100] * 10 + [50] * 2 + [100] * 3 + [50] * 2 + [100] * 5
    assert len(episode_starts(series(v), POLICY)) == 1


def test_planned_halfwidth_shrinks_with_more_events():
    # REQ: VAL-003
    assert planning_halfwidth(0.75, 10, 100) > planning_halfwidth(0.75, 100, 100)


def test_clustered_interval_is_wider_than_naive_when_windows_are_copies():
    # REQ: VAL-004
    rng = np.random.default_rng(0)
    sid, y, p = [], [], []
    for s in range(30):
        label = int(rng.random() < 0.3)
        score = np.clip(rng.normal(0.6 if label else 0.4, 0.2), 0.01, 0.99)
        sid += [s] * 20
        y += [label] * 20
        p += [score] * 20
    sid, y, p = map(np.array, (sid, y, p))
    clustered = cluster_bootstrap(sid, y, p, "auroc", reps=300)
    naive = cluster_bootstrap(np.arange(len(y)), y, p, "auroc", reps=300)
    assert (clustered["hi"] - clustered["lo"]) > (naive["hi"] - naive["lo"])


def test_gate_stops_everything_when_events_are_too_few():
    # REQ: VAL-005
    cohort = synthetic_cohort(n_subjects=40, days=14, seed=3)
    examples = make_examples(cohort)
    train, cal, test = cohort_split(examples)
    model = train_frozen(train, cal, "M2")
    strict = QualificationPolicy(min_positive_subjects=500, min_independent_episodes=5000,
                                 max_planned_halfwidth=0.01, planning_auroc=0.75, assumed_icc=0.3)
    gate = qualify(cohort[cohort.subject_id.isin(test.subject_id)], strict)
    result = external_validation(model, model.fingerprint(), test, gate, reps=50)
    assert result["status"] == "inconclusive"
    assert "auroc" not in result


def test_locked_model_is_scored_when_gate_passes():
    # REQ: VAL-006
    cohort = synthetic_cohort(n_subjects=40, days=14, seed=3)
    examples = make_examples(cohort)
    train, cal, test = cohort_split(examples)
    model = train_frozen(train, cal, "M2")
    lenient = QualificationPolicy(min_positive_subjects=2, min_independent_episodes=5,
                                  max_planned_halfwidth=0.5, planning_auroc=0.75, assumed_icc=0.3)
    gate = qualify(cohort[cohort.subject_id.isin(test.subject_id)], lenient)
    assert gate["passed"], gate
    result = external_validation(model, model.fingerprint(), test, gate, reps=200)
    assert result["status"] == "estimated"
    assert result["auroc"]["lo"] <= result["auroc"]["point"] <= result["auroc"]["hi"]
    assert set(result["calibration"]) == {"slope", "intercept"}


def test_wrong_fingerprint_is_refused():
    # REQ: VAL-007
    cohort = synthetic_cohort(n_subjects=40, days=14, seed=3)
    train, cal, test = cohort_split(make_examples(cohort))
    model = train_frozen(train, cal, "M0")
    with pytest.raises(ValueError):
        external_validation(model, "0" * 64, test, {"passed": True})


def test_calibration_slope_is_near_one_for_calibrated_scores():
    # REQ: VAL-008
    rng = np.random.default_rng(1)
    p = rng.uniform(0.02, 0.9, 20000)
    y = (rng.random(20000) < p).astype(int)
    cal = calibration_slope_intercept(y, p)
    assert abs(cal["slope"] - 1) < 0.08 and abs(cal["intercept"]) < 0.08
