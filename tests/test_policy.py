import numpy as np
import pytest

from lbidsm.policy import CATEGORIES, ActionOption, DecisionInput, PolicyConfig, decide

CFG = PolicyConfig(version="rules-test-0", escalate_risk=0.40, max_risk_interval_width=0.30,
                   review_min_utility=0.02, assess_risk=0.15)


def make(**kw):
    base = dict(subject_id="p1", as_of="2026-01-01T00:00:00Z", quality_passed=True, last_glucose=110.0,
                risk=(0.05, 0.02, 0.10), model_version="M2-test")
    base.update(kw)
    return DecisionInput(**base)


def test_verified_low_always_escalates_even_if_quality_failed():
    # REQ: L7-001
    d = decide(make(last_glucose=48.0, quality_passed=False, risk=None), CFG)
    assert d.category == "Escalate" and any("confirm it" in r for r in d.reasons)


def test_quality_failure_abstains():
    # REQ: L7-002
    d = decide(make(quality_passed=False, quality_reasons=["coverage below policy"]), CFG)
    assert d.category == "Abstain" and d.audit["abstention_reason"]


def test_wide_uncertainty_and_missing_risk_abstain():
    # REQ: L7-003
    assert decide(make(risk=(0.2, 0.0, 0.6)), CFG).category == "Abstain"
    assert decide(make(risk=None), CFG).category == "Abstain"
    assert decide(make(in_distribution=False), CFG).category == "Abstain"


def test_confident_high_risk_escalates():
    # REQ: L7-004
    assert decide(make(risk=(0.55, 0.45, 0.65)), CFG).category == "Escalate"


def test_review_lists_eligible_options_only_and_labels_evidence():
    # REQ: L7-005
    acts = [ActionOption("A", 0.05, 0.01, 0.09), ActionOption("B", 0.04, -0.02, 0.10),
            ActionOption("C", 0.30, 0.20, 0.40, eligible=False), ActionOption("D", 0.001, -0.01, 0.01)]
    d = decide(make(actions=acts), CFG)
    assert d.category == "Review"
    assert [o["name"] for o in d.review_options] == ["A", "B"]
    assert d.review_options[0]["evidence"] == "interval excludes zero"
    assert d.review_options[1]["evidence"] == "interval crosses zero"


def test_assess_then_monitor():
    # REQ: L7-006
    assert decide(make(risk=(0.10, 0.05, 0.20)), CFG).category == "Assess"
    d = decide(make(), CFG)
    assert d.category == "Monitor" and not d.requires_human


def test_every_decision_carries_the_data_contract_audit_fields():
    # REQ: L7-007
    d = decide(make(), CFG)
    assert set(d.audit) == {"patient_id", "as_of_utc", "model_version", "rule_version",
                            "action_set", "abstention_reason", "reviewer_id"}
    assert "No treatment action is executed" in d.message


def test_property_any_reading_below_54_escalates():
    # REQ: L7-008
    rng = np.random.default_rng(0)
    for _ in range(500):
        lo = rng.uniform(0, 0.8)
        d = decide(make(last_glucose=float(rng.uniform(20, 53.9)), quality_passed=bool(rng.integers(0, 2)),
                        risk=None if rng.random() < 0.3 else (lo, lo, lo + rng.uniform(0, 0.9)),
                        in_distribution=bool(rng.integers(0, 2))), CFG)
        assert d.category == "Escalate"


def test_output_categories_are_the_five_governed_ones():
    # REQ: L7-009
    rng = np.random.default_rng(1)
    for _ in range(300):
        lo = rng.uniform(0, 0.8)
        d = decide(make(last_glucose=float(rng.uniform(40, 300)),
                        risk=(lo, lo, lo + rng.uniform(0, 0.5))), CFG)
        assert d.category in CATEGORIES
