"""Confounder screening for subject-level questions such as 'is endotype / a genetic score
associated with low-glucose events?'. Research-only, and **not** causal identification.

Data cannot say which variables are confounders; that needs a causal diagram fixed in
advance. This module (1) applies a declared role for each variable (confounder candidate,
mediator, collider, post-baseline, outcome-descendant) so that mediators and colliders are
never adjusted for, and (2) ranks the remaining candidates with two standard data checks:
association with both exposure and outcome, and the change-in-estimate criterion.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

# Default roles for a genetic/endotype exposure and a low-glucose outcome. Edit with a clinician.
DEFAULT_ROLES = {
    "age_years": "candidate", "diabetes_duration_years": "candidate", "egfr": "candidate",
    "bmi": "mediator",           # genes -> adiposity -> insulin resistance -> events
    "homa_ir": "mediator", "fasting_insulin_uU_ml": "mediator", "fasting_glucose_mg_dl": "mediator",
    "triglycerides_mg_dl": "mediator", "hdl_mg_dl": "mediator", "hba1c_percent": "mediator",
    "on_sulfonylurea": "candidate", "on_insulin": "candidate",  # indication by disease severity
}


def subject_outcomes(examples: pd.DataFrame) -> pd.DataFrame:
    """Subject-level outcome: any event, and event-window rate (avoids window pseudo-replication)."""
    g = examples.groupby("subject_id").event_lt54
    return pd.DataFrame({"any_event": (g.max() > 0).astype(int), "event_rate": g.mean()})


def screen_confounders(subject_table: pd.DataFrame, exposure: str, outcome: str = "any_event",
                       roles: dict | None = None, assoc_threshold: float = 0.20,
                       change_threshold: float = 0.10) -> pd.DataFrame:
    """Rank adjustment candidates. subject_table: one row per subject with exposure, outcome, covariates.

    Flags: associated_with_exposure, associated_with_outcome (|Spearman rho| >= threshold) and
    change_in_estimate (relative change in the exposure's logistic coefficient when the candidate is added).
    'recommended_adjustment' needs role == candidate AND (both associations OR change >= threshold).
    """
    from scipy.stats import spearmanr
    from sklearn.linear_model import LogisticRegression
    roles = {**DEFAULT_ROLES, **(roles or {})}
    d = subject_table.dropna(subset=[exposure, outcome]).copy()
    if len(d) < 30 or d[outcome].nunique() != 2:
        raise ValueError("Need >=30 subjects with both outcome classes for confounder screening")

    def coef(cols):
        X = d[cols].apply(lambda s: (s - s.mean()) / (s.std() or 1.0)).fillna(0.0)
        m = LogisticRegression(C=10.0, max_iter=2000).fit(X, d[outcome])
        return float(m.coef_[0][0])
    base = coef([exposure])
    rows = []
    for c in subject_table.columns:
        if c in (exposure, outcome, "subject_id", "any_event", "event_rate") or c not in d or d[c].nunique() < 2:
            continue
        dd = d[[exposure, outcome, c]].dropna()
        r_e = float(spearmanr(dd[c], dd[exposure])[0]); r_o = float(spearmanr(dd[c], dd[outcome])[0])
        adj = coef([exposure, c])
        change = abs(adj - base) / (abs(base) + 1e-9)
        role = roles.get(c, "unclassified")
        both = abs(r_e) >= assoc_threshold and abs(r_o) >= assoc_threshold
        rows.append({"variable": c, "role": role, "rho_with_exposure": round(r_e, 2), "rho_with_outcome": round(r_o, 2),
                     "associated_with_both": both, "change_in_estimate": round(change, 2),
                     "recommended_adjustment": bool(role == "candidate" and (both or change >= change_threshold)),
                     "note": "do not adjust: mediator on assumed path" if role == "mediator"
                             else ("role not declared: needs clinical review" if role == "unclassified" else "")})
    return pd.DataFrame(rows).sort_values(["recommended_adjustment", "change_in_estimate"], ascending=False).reset_index(drop=True)
