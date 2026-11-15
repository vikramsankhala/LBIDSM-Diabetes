import numpy as np
import pytest

from lbidsm.utility import Candidate, robust_rank, summarise, utility_draws

RNG = np.random.default_rng(0)


def cand(name, arr, hypo, **kw):
    return Candidate(name, RNG.normal(arr, 0.01, 500), {"level2_low": RNG.normal(hypo, 0.005, 500)}, **kw)


def test_utility_is_benefit_minus_weighted_harm_minus_cost():
    # REQ: L6-010
    c = Candidate("a", np.full(10, 0.10), {"level2_low": np.full(10, 0.04)}, cost=0.01)
    assert np.allclose(utility_draws(c, {"level2_low": 2.0}), 0.10 - 2.0 * 0.04 - 0.01)


def test_missing_weight_is_an_error_not_a_default():
    # REQ: L6-011
    with pytest.raises(ValueError):
        utility_draws(cand("a", 0.1, 0.04), {})


def test_ranking_changes_with_how_much_a_low_is_feared():
    # REQ: L6-012
    big_benefit_more_lows = cand("A", 0.12, 0.08)
    modest_benefit_safe = cand("B", 0.07, 0.01)
    mild, severe = {"level2_low": 0.5}, {"level2_low": 3.0}
    assert robust_rank([big_benefit_more_lows, modest_benefit_safe], [mild])[0]["action"] == "A"
    assert robust_rank([big_benefit_more_lows, modest_benefit_safe], [severe])[0]["action"] == "B"
    # Across both views, the robust choice is the one that never does badly
    assert robust_rank([big_benefit_more_lows, modest_benefit_safe], [mild, severe])[0]["action"] == "B"


def test_ineligible_actions_are_listed_last_with_reason():
    # REQ: L6-013
    ok = cand("ok", 0.05, 0.01)
    blocked = cand("blocked", 0.30, 0.0, eligible=False, ineligible_reason="excluded by approved rule table")
    ranked = robust_rank([blocked, ok], [{"level2_low": 1.0}])
    assert [r["action"] for r in ranked] == ["ok", "blocked"]
    assert ranked[-1]["ineligible_reason"]


def test_summary_reports_uncertainty():
    # REQ: L6-014
    s = summarise(cand("a", 0.05, 0.01), {"level2_low": 1.0})
    assert s["lo"] < s["utility"] < s["hi"] and 0 <= s["p_utility_positive"] <= 1
