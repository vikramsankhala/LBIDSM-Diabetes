import numpy as np
import pandas as pd

from lbidsm.causal import arr_iptw, e_value, effective_sample_size, individual_effects, smd, stabilised_weights


def _sig(z):
    return 1 / (1 + np.exp(-z))


def synthetic_trial(n=4000, seed=0):
    """Confounded by indication: sicker people (x1) are more likely to be treated and more likely to have events.
    Treatment helps much more when x2 > 0. The true effect is known exactly."""
    rng = np.random.default_rng(seed)
    x1, x2 = rng.normal(size=n), rng.normal(size=n)
    a = (rng.random(n) < _sig(0.9 * x1 - 0.4 * x2)).astype(int)
    base = -1.6 + 0.9 * x1 - 0.3 * x2
    shift = np.where(x2 > 0, -1.0, -0.15)
    p0, p1 = _sig(base), _sig(base + shift)
    y = (rng.random(n) < np.where(a == 1, p1, p0)).astype(int)
    df = pd.DataFrame({"x1": x1, "x2": x2, "treated": a, "event": y, "pid": np.arange(n)})
    return df, float((p0 - p1).mean()), p0 - p1


def test_weighting_removes_confounding_bias():
    # REQ: L6-001
    df, truth, _ = synthetic_trial()
    naive = df[df.treated == 0].event.mean() - df[df.treated == 1].event.mean()
    res = arr_iptw(df, "treated", "event", ["x1", "x2"], reps=150)
    assert abs(res["arr"] - truth) < 0.025
    assert abs(naive - truth) > abs(res["arr"] - truth)
    assert res["arr_ci"][0] < truth < res["arr_ci"][1]


def test_balance_improves_and_positivity_is_reported():
    # REQ: L6-002
    df, _, _ = synthetic_trial()
    res = arr_iptw(df, "treated", "event", ["x1", "x2"], reps=20)
    assert res["max_abs_smd_after"] < res["max_abs_smd_before"]
    assert res["balance_ok"] and "positivity_ok" in res


def test_weights_are_truncated_and_positive():
    # REQ: L6-003
    df, _, _ = synthetic_trial()
    w, ps = stabilised_weights(df, "treated", ["x1", "x2"])
    assert (w > 0).all() and effective_sample_size(w) <= len(w)
    assert smd(df, "treated", ["x1"], w).abs().iloc[0] < smd(df, "treated", ["x1"]).abs().iloc[0]


def test_e_value_known_values():
    # REQ: L6-004
    assert abs(e_value(2.0) - (2 + 2 ** 0.5)) < 1e-9
    assert abs(e_value(0.5) - e_value(2.0)) < 1e-9
    assert e_value(1.0) == 1.0


def test_individual_effects_find_the_responders():
    # REQ: L6-005
    df, _, true_arr = synthetic_trial(n=3000)
    new = df.iloc[:200].copy()
    eff = individual_effects(df.iloc[200:], new, "treated", "event", ["x1", "x2"], reps=40)
    responders = (new.x2 > 0).to_numpy()
    assert eff.arr[responders].mean() > eff.arr[~responders].mean()
    assert (eff.lo <= eff.arr + 1e-9).mean() > 0.9 and (eff.hi >= eff.arr - 1e-9).mean() > 0.9
