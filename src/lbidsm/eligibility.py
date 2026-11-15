"""Fail-closed eligibility of action options. Research use only.

This module holds NO clinical rules. It is the mechanism that applies a rule table that
clinicians write, version and approve. With no approved table, every option is ineligible,
so nothing can reach a clinician as a worthwhile option by accident.

Table format (a plain dict, so it can be stored as reviewed JSON):
    {"version": "...", "approved_by": "...", "approved_on": "YYYY-MM-DD",
     "actions": {"option_A": [{"field": "egfr", "op": "<", "value": 30, "reason": "..."}]}}
Only actions listed in "actions" can be eligible. A rule excludes the option when it matches.
"""
from __future__ import annotations

import operator

OPS = {"<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge, "==": operator.eq, "!=": operator.ne}


def validate_table(table: dict) -> None:
    missing = [k for k in ("version", "approved_by", "approved_on") if not table.get(k)]
    if missing or not isinstance(table.get("actions"), dict):
        raise ValueError(f"Rule table not approved or incomplete: missing {missing or ['actions']}")
    for action, rules in table["actions"].items():
        for r in rules:
            if r.get("op") not in OPS or not r.get("field") or not r.get("reason"):
                raise ValueError(f"Bad rule for {action}: need field, op in {sorted(OPS)}, and reason")


def eligibility(action: str, person: dict, table: dict | None) -> tuple[bool, str]:
    """(eligible, reason). Fails closed on a missing table, an unlisted action or a missing field."""
    if table is None:
        return False, "no clinician-approved rule table supplied"
    validate_table(table)
    if action not in table["actions"]:
        return False, "action not listed in the approved rule table"
    for r in table["actions"][action]:
        if person.get(r["field"]) is None:
            return False, f"cannot check rule on '{r['field']}': value missing"
        if OPS[r["op"]](person[r["field"]], r["value"]):
            return False, r["reason"]
    return True, f"passes rule table {table['version']}"


def apply_eligibility(candidates: list, person: dict, table: dict | None) -> list:
    """Set `eligible` and `ineligible_reason` on each candidate from the table."""
    for c in candidates:
        c.eligible, why = eligibility(c.name, person, table)
        c.ineligible_reason = "" if c.eligible else why
    return candidates
