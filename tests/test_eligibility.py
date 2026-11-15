import numpy as np
import pytest

from lbidsm.eligibility import apply_eligibility, eligibility
from lbidsm.protocol import PROVISIONAL, QUALIFICATION, POLICY, HARM_WEIGHT_SCENARIOS
from lbidsm.utility import Candidate

TABLE = {"version": "t-1", "approved_by": "Dr X", "approved_on": "2026-01-01",
         "actions": {"A": [{"field": "egfr", "op": "<", "value": 30, "reason": "kidney function too low"}]}}


def test_no_table_means_nothing_eligible():
    # REQ: ELG-001
    ok, why = eligibility("A", {"egfr": 60}, None)
    assert not ok and "no clinician-approved" in why
    cands = apply_eligibility([Candidate("A", np.zeros(3))], {"egfr": 60}, None)
    assert not cands[0].eligible and cands[0].ineligible_reason


def test_unapproved_table_rejected():
    # REQ: ELG-002
    bad = {k: v for k, v in TABLE.items() if k != "approved_by"}
    with pytest.raises(ValueError):
        eligibility("A", {"egfr": 60}, bad)


def test_rule_match_excludes_with_reason_and_missing_field_fails_closed():
    # REQ: ELG-003
    assert eligibility("A", {"egfr": 60}, TABLE)[0]
    ok, why = eligibility("A", {"egfr": 20}, TABLE)
    assert not ok and why == "kidney function too low"
    assert not eligibility("A", {}, TABLE)[0]
    assert not eligibility("B", {"egfr": 60}, TABLE)[0]


def test_provisional_values_are_marked_and_versioned():
    # REQ: PRO-001
    assert PROVISIONAL and POLICY.version.endswith("provisional-0.1")
    assert QUALIFICATION.min_independent_episodes == 50 and len(HARM_WEIGHT_SCENARIOS) == 3
