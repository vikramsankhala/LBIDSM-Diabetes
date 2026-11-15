"""Net utility of candidate actions, and a robust research ranking. Research use only.

U(a) = ARR(a) - sum_k w_k * P(harm_k under a) - C(a)

ARR is the benefit from causal.py. The harms are other outcomes (for example a
level 2 low) with severity weights w_k. Those weights are CLINICAL VALUE
JUDGEMENTS. They have no defaults here: they must be elicited from clinicians
and patients, written into the protocol and passed in. The result is a ranking
for human review. It is never a prescription.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Candidate:
    name: str
    arr_draws: np.ndarray                      # draws of absolute risk reduction (benefit)
    harm_draws: dict = field(default_factory=dict)   # outcome name -> draws of P(harm | action)
    cost: float = 0.0                          # burden or cost on the same scale as risk
    eligible: bool = True                      # set from a clinician-approved rule table
    ineligible_reason: str = ""


def utility_draws(c: Candidate, weights: dict) -> np.ndarray:
    missing = set(c.harm_draws) - set(weights)
    if missing:
        raise ValueError(f"No severity weight supplied for: {sorted(missing)}")
    u = np.asarray(c.arr_draws, float) - c.cost
    for k, draws in c.harm_draws.items():
        u = u - weights[k] * np.asarray(draws, float)
    return u


def summarise(c: Candidate, weights: dict) -> dict:
    u = utility_draws(c, weights)
    return {"action": c.name, "eligible": c.eligible, "utility": float(u.mean()),
            "lo": float(np.percentile(u, 2.5)), "hi": float(np.percentile(u, 97.5)),
            "p_utility_positive": float((u > 0).mean())}


def robust_rank(candidates: list, scenarios: list) -> list:
    """Rank eligible actions by their WORST mean utility across several weight scenarios.

    max over actions of min over scenarios of expected net utility. Ineligible actions are
    listed last with the reason, so a reviewer sees what was excluded and why.
    """
    if not scenarios:
        raise ValueError("Provide at least one weight scenario")
    rows = []
    for c in candidates:
        per = [summarise(c, w) for w in scenarios]
        worst = min(per, key=lambda r: r["utility"])
        rows.append({**worst, "worst_case_utility": worst["utility"],
                     "best_case_utility": max(r["utility"] for r in per),
                     "ineligible_reason": c.ineligible_reason})
    eligible = sorted([r for r in rows if r["eligible"]], key=lambda r: -r["worst_case_utility"])
    return eligible + [r for r in rows if not r["eligible"]]
