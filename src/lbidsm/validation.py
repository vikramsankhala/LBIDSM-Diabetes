"""External validation helpers: cohort qualification gate and honest uncertainty.

Order of operations, as in docs/INDEPENDENT_T2D_COHORT_QUALIFICATION_REPORT.md:
1. count independent events and event-positive people in the cohort,
2. check that the planned precision is good enough,
3. only then compute AUROC, AUPRC and calibration, with patient-clustered intervals.
If step 1 or 2 fails, no performance number is produced at all.
Research use only.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .model_bundle import LABEL, FrozenModel, predict


@dataclass(frozen=True)
class QualificationPolicy:
    """Thresholds have NO defaults on purpose: the protocol must state them, in writing,
    before any outcome is examined. The project documents disagree on a universal
    event count, so this code refuses to invent one."""
    min_positive_subjects: int
    min_independent_episodes: int
    max_planned_halfwidth: float      # largest acceptable 95% half-width for AUROC
    planning_auroc: float             # AUROC you expect, for the planning calculation only
    assumed_icc: float                # within-person similarity of events, 0 to 1
    separation_minutes: float = 30.0  # new episode after this long above threshold
    max_gap_minutes: float = 15.0
    threshold_mg_dl: float = 54.0


def episode_starts(frame: pd.DataFrame, policy: QualificationPolicy) -> list:
    """Start times of independent low-glucose episodes for one subject.

    Same proxy definition as scripts/expanded_validation.py: consecutive samples below the
    threshold form one episode; a new one starts after the separation time or a long gap.
    """
    d = frame.sort_values("timestamp")
    t = pd.to_datetime(d.timestamp, utc=True).astype("int64").to_numpy() / 60e9
    low = d.glucose_mg_dl.to_numpy() < policy.threshold_mg_dl
    starts, last_low, prev_t = [], None, None
    for i in range(len(t)):
        if low[i]:
            new = (last_low is None or t[i] - last_low >= policy.separation_minutes
                   or (prev_t is not None and t[i] - prev_t > policy.max_gap_minutes))
            if new:
                starts.append(t[i])
            last_low = t[i]
        prev_t = t[i]
    return starts


def planning_halfwidth(auroc: float, n_pos: float, n_neg: float) -> float:
    """Hanley-McNeil 95% half-width for an AUROC. A planning approximation only."""
    a = auroc
    q1, q2 = a / (2 - a), 2 * a * a / (1 + a)
    var = (a * (1 - a) + (n_pos - 1) * (q1 - a * a) + (n_neg - 1) * (q2 - a * a)) / (n_pos * n_neg)
    return float(1.96 * np.sqrt(max(var, 0.0)))


def qualify(raw: pd.DataFrame, policy: QualificationPolicy) -> dict:
    """Stage 1 (counts) and stage 2 (planned precision). `raw` has subject_id, timestamp, glucose_mg_dl."""
    per_subject, patient_days = {}, 0.0
    for sid, g in raw.groupby("subject_id"):
        per_subject[sid] = len(episode_starts(g, policy))
        gaps = pd.to_datetime(g.timestamp, utc=True).sort_values().diff().dt.total_seconds().dropna() / 60
        patient_days += float(gaps[gaps <= policy.max_gap_minutes].sum()) / 1440
    positive = [s for s, n in per_subject.items() if n > 0]
    episodes = int(sum(per_subject.values()))
    out = {"subjects": len(per_subject), "positive_subjects": len(positive), "independent_episodes": episodes,
           "patient_days": round(patient_days, 2), "reasons": []}
    if out["positive_subjects"] < policy.min_positive_subjects:
        out["reasons"].append("too few event-positive subjects")
    if episodes < policy.min_independent_episodes:
        out["reasons"].append("too few independent episodes")
    out["stage1_passed"] = not out["reasons"]
    if positive and episodes:
        per_person = episodes / len(positive)
        design_effect = 1 + (per_person - 1) * policy.assumed_icc
        out["planned_halfwidth"] = round(planning_halfwidth(
            policy.planning_auroc, max(episodes / design_effect, 2), max(patient_days, 2)), 3)
        if out["planned_halfwidth"] > policy.max_planned_halfwidth:
            out["reasons"].append("planned precision is worse than the pre-specified limit")
    else:
        out["planned_halfwidth"] = None
        out["reasons"].append("no events: precision cannot be planned")
    out["stage2_passed"] = out["planned_halfwidth"] is not None and out["planned_halfwidth"] <= policy.max_planned_halfwidth
    out["passed"] = out["stage1_passed"] and out["stage2_passed"]
    return out


def calibration_slope_intercept(y, p) -> dict:
    from sklearn.linear_model import LogisticRegression
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    z = np.log(p / (1 - p)).reshape(-1, 1)
    m = LogisticRegression(C=1e6, max_iter=2000).fit(z, np.asarray(y))
    return {"slope": float(m.coef_[0, 0]), "intercept": float(m.intercept_[0])}


def _metrics(y, p):
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
    return {"auroc": roc_auc_score(y, p), "auprc": average_precision_score(y, p), "brier": brier_score_loss(y, p)}


def cluster_bootstrap(subject_id, y, p, metric: str = "auroc", reps: int = 1000, seed: int = 42) -> dict:
    """Resample whole people, not windows. Windows from one person are not independent."""
    sid, y, p = np.asarray(subject_id), np.asarray(y), np.asarray(p)
    groups = {s: np.flatnonzero(sid == s) for s in np.unique(sid)}
    ids = list(groups)
    rng, values, skipped = np.random.default_rng(seed), [], 0
    for _ in range(reps):
        pick = rng.choice(len(ids), size=len(ids), replace=True)
        idx = np.concatenate([groups[ids[i]] for i in pick])
        if len(np.unique(y[idx])) < 2:
            skipped += 1
            continue
        values.append(_metrics(y[idx], p[idx])[metric])
    point = _metrics(y, p)[metric]
    lo, hi = (np.percentile(values, [2.5, 97.5]) if values else (np.nan, np.nan))
    return {"point": float(point), "lo": float(lo), "hi": float(hi), "valid_resamples": len(values), "skipped": skipped}


def external_validation(model: FrozenModel, expected_fingerprint: str, examples: pd.DataFrame,
                        qualification: dict, reps: int = 1000, seed: int = 42) -> dict:
    """Score a locked model on an external cohort, but only if the gate passed."""
    if model.fingerprint() != expected_fingerprint:
        raise ValueError("Model fingerprint differs from the one recorded before unblinding")
    if not qualification.get("passed"):
        return {"status": "inconclusive", "reason": qualification.get("reasons"), "qualification": qualification}
    y, p = examples[LABEL].to_numpy(), predict(model, examples)
    if len(np.unique(y)) < 2:
        return {"status": "inconclusive", "reason": ["only one outcome class"], "qualification": qualification}
    result = {"status": "estimated", "model": model.name, "fingerprint": expected_fingerprint,
              "n_subjects": int(examples.subject_id.nunique()), "n_windows": len(y), "n_event_windows": int(y.sum()),
              "calibration": calibration_slope_intercept(y, p), "qualification": qualification}
    for m in ("auroc", "auprc", "brier"):
        result[m] = cluster_bootstrap(examples.subject_id, y, p, m, reps, seed)
    return result
