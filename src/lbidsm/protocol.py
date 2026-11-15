"""Provisional protocol values, with the reasoning for each. Research use only.

These are working choices so the project can proceed. They are NOT clinically approved.
Each must be reviewed, changed if needed, and signed in the study protocol (docs/DECISIONS.md).
The classes themselves still have no defaults: nothing is applied unless it is passed in by name.
"""
from __future__ import annotations

from .policy import PolicyConfig
from .validation import QualificationPolicy

PROVISIONAL = True
VERSION = "provisional-0.1"

# Planned AUROC half-width of 0.10 or less: if the model's true AUROC is about 0.75, the lower
# bound stays above 0.65, clearly better than chance. 50 independent episodes matches the lower
# end of the figure in the project deck; 20 event-positive people gives the person-level bootstrap
# enough clusters to be more than a handful. At ICC 0.3 the planned half-width is 0.097; at ICC 0.5
# it is 0.107 and the gate would fail, so the ICC assumption must be justified or tested.
QUALIFICATION = QualificationPolicy(
    min_positive_subjects=20, min_independent_episodes=50,
    max_planned_halfwidth=0.10, planning_auroc=0.75, assumed_icc=0.3)

# The weight is how many times worse one level 2 low is than one unit of benefit. Nobody can set it
# from data, so the ranking is run across a wide range (1, 3, 10) and an option is preferred only
# if it holds up in the worst case. Clinicians and patients should replace or confirm the range.
HARM_WEIGHT_SCENARIOS = [{"level2_low": w} for w in (1.0, 3.0, 10.0)]

# Risk thresholds are placeholders until calibration on a qualified cohort shows what they mean.
POLICY = PolicyConfig(version=f"rules-{VERSION}", escalate_risk=0.40, max_risk_interval_width=0.30,
                      review_min_utility=0.02, assess_risk=0.15)
