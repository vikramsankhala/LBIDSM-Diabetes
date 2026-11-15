"""L7 governance: turn evidence into one of five governed outputs. Research use only.

Escalate, Review, Assess, Monitor or Abstain. Nothing here executes, doses or
adjusts treatment. Every output is a message for a human, and every decision
carries the audit fields named in docs/DATA_CONTRACT.md (`decisions` entity).

Order matters, and the order is a safety design:
1. A verified reading below 54 mg/dL always escalates, even if other checks failed.
   (If data quality failed, the message says the reading is unverified.)
   This ordering is a clinical-safety choice and needs clinician sign-off.
2. Otherwise any failed quality gate, missing or out-of-range estimate, or
   wide uncertainty means Abstain: no output, human review.
3. Otherwise a confidently high risk escalates, a worthwhile eligible option goes to
   Review, rising risk goes to Assess, and everything else is Monitor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

CATEGORIES = ("Escalate", "Review", "Assess", "Monitor", "Abstain")
NO_ACTION = "No treatment action is executed by this software."


@dataclass(frozen=True)
class PolicyConfig:
    """No defaults except the level 2 line: every threshold is a protocol decision."""
    version: str
    escalate_risk: float            # escalate if the LOWER bound of calibrated risk is at least this
    max_risk_interval_width: float  # abstain if (upper - lower) exceeds this
    review_min_utility: float       # minimum net utility worth showing a clinician
    assess_risk: float              # assess if the UPPER bound of risk is at least this
    level2_mg_dl: float = 54.0


@dataclass
class ActionOption:
    name: str
    utility: float
    lo: float
    hi: float
    eligible: bool = True


@dataclass
class DecisionInput:
    subject_id: str
    as_of: str                              # ISO 8601, UTC
    quality_passed: bool
    last_glucose: Optional[float] = None
    quality_reasons: list = field(default_factory=list)
    risk: Optional[tuple] = None            # (point, lower, upper) calibrated probability
    in_distribution: bool = True
    actions: list = field(default_factory=list)
    model_version: str = ""


@dataclass
class Decision:
    category: str
    reasons: list
    review_options: list
    requires_human: bool
    message: str
    audit: dict


def _decision(inp, cfg, category, reasons, options=None, abstention=None):
    return Decision(
        category=category, reasons=reasons, review_options=options or [],
        requires_human=category != "Monitor",
        message=f"{category}: {'; '.join(reasons)}. {NO_ACTION}",
        audit={"patient_id": inp.subject_id, "as_of_utc": inp.as_of, "model_version": inp.model_version,
               "rule_version": cfg.version, "action_set": [o["name"] for o in (options or [])],
               "abstention_reason": abstention, "reviewer_id": None},
    )


def decide(inp: DecisionInput, cfg: PolicyConfig) -> Decision:
    if inp.last_glucose is not None and inp.last_glucose < cfg.level2_mg_dl:
        why = [f"reading {inp.last_glucose:.0f} mg/dL is below {cfg.level2_mg_dl:.0f}: follow the established care plan"]
        if not inp.quality_passed:
            why.append("the reading failed data-quality checks: confirm it before acting")
        return _decision(inp, cfg, "Escalate", why)

    problems = list(inp.quality_reasons) if not inp.quality_passed else []
    if inp.risk is None:
        problems.append("no risk estimate available")
    elif inp.risk[2] - inp.risk[1] > cfg.max_risk_interval_width:
        problems.append("risk estimate too uncertain")
    if not inp.in_distribution:
        problems.append("input outside the range the model was validated on")
    if not inp.quality_passed and not problems:
        problems.append("data-quality gate failed")
    if problems:
        return _decision(inp, cfg, "Abstain", problems, abstention="; ".join(problems))

    point, lo, hi = inp.risk
    if lo >= cfg.escalate_risk:
        return _decision(inp, cfg, "Escalate", [f"calibrated risk {point:.2f} (lower bound {lo:.2f}) is high"])

    options = sorted(
        ({"name": a.name, "utility": a.utility, "interval": (a.lo, a.hi),
          "evidence": "interval excludes zero" if a.lo > 0 else "interval crosses zero"}
         for a in inp.actions if a.eligible and a.utility >= cfg.review_min_utility),
        key=lambda o: -o["utility"])
    if options:
        return _decision(inp, cfg, "Review",
                         ["an eligible option may help; clinician and patient decide"], options)
    if hi >= cfg.assess_risk:
        return _decision(inp, cfg, "Assess", [f"risk may be rising (upper bound {hi:.2f}): gather more clinical data"])
    return _decision(inp, cfg, "Monitor", ["stable, no rule favours action"])
