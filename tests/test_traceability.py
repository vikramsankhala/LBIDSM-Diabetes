from pathlib import Path

from lbidsm.evidence import trace_matrix
from lbidsm.requirements import REQUIREMENTS


def test_every_requirement_has_a_test_and_every_tag_is_registered():
    # REQ: TRC-001
    t = trace_matrix(REQUIREMENTS, Path(__file__).parent)
    assert t["uncovered"] == [], t["uncovered"]
    assert t["unknown_tags"] == [], t["unknown_tags"]
