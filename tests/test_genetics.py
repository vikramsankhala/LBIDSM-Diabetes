import numpy as np
import pandas as pd

from lbidsm.genetics import egger, f_statistic, harmonise, ivw, mr_summary, weighted_median


def simulate(n=80, effect=0.4, pleio_mean=0.0, seed=0):
    rng = np.random.default_rng(seed)
    gx = rng.uniform(0.04, 0.12, n) * rng.choice([-1, 1], n)
    sx = np.full(n, 0.01)
    bx = gx + rng.normal(0, sx)
    pleio = pleio_mean * np.sign(gx) + rng.normal(0, 0.01, n)   # same direction for exposure-increasing alleles
    sy = np.full(n, 0.02)
    by = effect * gx + pleio + rng.normal(0, sy)
    snp = [f"rs{i}" for i in range(n)]
    ex = pd.DataFrame({"snp": snp, "ea": "A", "oa": "G", "eaf": 0.3, "beta": bx, "se": sx})
    out = pd.DataFrame({"snp": snp, "ea": "A", "oa": "G", "eaf": 0.3, "beta": by, "se": sy})
    return ex, out


def test_recovers_a_known_effect_without_pleiotropy():
    # REQ: L1-001
    res = mr_summary(*simulate())
    assert res["status"] == "estimated"
    for method in ("ivw", "egger", "weighted_median"):
        assert abs(res[method]["beta"] - 0.4) < 0.1, method
    assert not res["warnings"]


def test_egger_flags_directional_pleiotropy_that_biases_ivw():
    # REQ: L1-002
    res = mr_summary(*simulate(pleio_mean=0.02))
    assert res["egger"]["intercept_p"] < 0.05
    assert any("pleiotropy" in w for w in res["warnings"])
    assert res["ivw"]["beta"] > 0.4 + 0.1          # plain IVW is pulled away from the truth
    assert abs(res["egger"]["beta"] - 0.4) < abs(res["ivw"]["beta"] - 0.4)


def test_harmonise_flips_mismatched_alleles_and_drops_palindromes():
    # REQ: L1-003
    ex = pd.DataFrame({"snp": ["a", "b", "c", "d"], "ea": ["A", "A", "A", "A"], "oa": ["G", "G", "T", "C"],
                       "eaf": [0.2, 0.2, 0.5, 0.2], "beta": [0.1] * 4, "se": [0.01] * 4})
    out = pd.DataFrame({"snp": ["a", "b", "c", "d"], "ea": ["A", "G", "A", "T"], "oa": ["G", "A", "T", "G"],
                        "eaf": [0.2, 0.8, 0.5, 0.2], "beta": [0.3, 0.3, 0.3, 0.3], "se": [0.02] * 4})
    h = harmonise(ex, out)
    assert list(h.snp) == ["a", "b"]          # c is palindromic near 0.5; d has mismatched alleles
    assert h.set_index("snp").by["a"] == 0.3 and h.set_index("snp").by["b"] == -0.3


def test_weak_instruments_are_filtered():
    # REQ: L1-004
    ex, out = simulate(n=30)
    ex.loc[:9, "beta"] = 0.001
    res = mr_summary(ex, out, min_f=10)
    assert res["n_snps"] <= 20
    assert (f_statistic([0.1, 0.01], [0.01, 0.01]) == np.array([100.0, 1.0])).all()


def test_too_few_instruments_is_inconclusive():
    # REQ: L1-005
    ex, out = simulate(n=2)
    assert mr_summary(ex, out)["status"] == "inconclusive"
