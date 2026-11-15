"""Patient-specific causal effects from observational data. Research use only.

Scope: one time zero per person (a "baseline" target-trial emulation) with two
treatment strategies. Time-varying treatment needs a marginal structural model
with repeated weights; that is the next step and is not claimed here.

The answer is only as good as three assumptions that no code can check:
no unmeasured confounding, positivity (everyone could have received either
strategy) and consistency (the treatment is well defined). The diagnostics
below test positivity and measured balance, and the E-value says how strong
an unmeasured confounder would have to be to explain the result away.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _logit_fit(X, y, sample_weight=None):
    from sklearn.linear_model import LogisticRegression
    return LogisticRegression(C=10.0, max_iter=2000).fit(X, y, sample_weight=sample_weight)


def _standardise(df, covars):
    x = df[covars].to_numpy(float)
    return (x - x.mean(0)) / np.where(x.std(0) == 0, 1, x.std(0))


def stabilised_weights(df: pd.DataFrame, treat: str, covars: list, trunc=(0.01, 0.99)):
    """Stabilised inverse-probability-of-treatment weights, truncated at set percentiles."""
    a = df[treat].to_numpy(int)
    ps = _logit_fit(_standardise(df, covars), a).predict_proba(_standardise(df, covars))[:, 1]
    p_a = a.mean()
    w = np.where(a == 1, p_a / ps, (1 - p_a) / (1 - ps))
    lo, hi = np.percentile(w, [100 * trunc[0], 100 * trunc[1]])
    return np.clip(w, lo, hi), ps


def smd(df: pd.DataFrame, treat: str, covars: list, w=None) -> pd.Series:
    """Standardised mean difference between arms for each covariate (below 0.1 is the usual aim)."""
    w = np.ones(len(df)) if w is None else np.asarray(w)
    a = df[treat].to_numpy(int)
    out = {}
    for c in covars:
        x = df[c].to_numpy(float)
        m1, m0 = np.average(x[a == 1], weights=w[a == 1]), np.average(x[a == 0], weights=w[a == 0])
        v1 = np.average((x[a == 1] - m1) ** 2, weights=w[a == 1])
        v0 = np.average((x[a == 0] - m0) ** 2, weights=w[a == 0])
        out[c] = (m1 - m0) / np.sqrt((v1 + v0) / 2)
    return pd.Series(out)


def effective_sample_size(w) -> float:
    w = np.asarray(w)
    return float(w.sum() ** 2 / (w ** 2).sum())


def e_value(rr: float) -> float:
    """VanderWeele-Ding E-value for a risk ratio: the confounding strength needed to explain it away."""
    rr = 1 / rr if rr < 1 else rr
    return float(rr + np.sqrt(rr * (rr - 1)))


def _risks(df, treat, outcome, w):
    a, y = df[treat].to_numpy(int), df[outcome].to_numpy(float)
    r1 = float((w * y * (a == 1)).sum() / (w * (a == 1)).sum())
    r0 = float((w * y * (a == 0)).sum() / (w * (a == 0)).sum())
    return r0, r1


def _resample(df, subject, rng):
    if subject is None:
        return df.iloc[rng.integers(0, len(df), len(df))]
    groups = {s: g for s, g in df.groupby(subject)}
    keys = list(groups)
    return pd.concat([groups[keys[i]] for i in rng.integers(0, len(keys), len(keys))])


def arr_iptw(df, treat, outcome, covars, subject=None, reps=500, seed=42) -> dict:
    """Absolute risk reduction ARR = P(Y under control) - P(Y under treatment), with diagnostics."""
    w, ps = stabilised_weights(df, treat, covars)
    r0, r1 = _risks(df, treat, outcome, w)
    rng, arr_draws, rr_draws = np.random.default_rng(seed), [], []
    for _ in range(reps):
        b = _resample(df, subject, rng)
        wb, _ = stabilised_weights(b, treat, covars)
        b0, b1 = _risks(b, treat, outcome, wb)
        arr_draws.append(b0 - b1)
        rr_draws.append(b1 / b0 if b0 > 0 else np.nan)
    lo, hi = np.percentile(arr_draws, [2.5, 97.5])
    rr = r1 / r0
    rr_lo, rr_hi = np.nanpercentile(rr_draws, [2.5, 97.5])
    after = smd(df, treat, covars, w)
    a = df[treat].to_numpy(int)
    out_of_overlap = float(((ps < 0.05) | (ps > 0.95)).mean())
    near_null = rr_hi if rr < 1 else rr_lo
    return {
        "risk_control": r0, "risk_treated": r1, "arr": r0 - r1, "arr_ci": (float(lo), float(hi)),
        "risk_ratio": rr, "e_value_point": e_value(rr),
        "e_value_ci_limit": 1.0 if (rr_lo < 1 < rr_hi) else e_value(near_null),
        "n": len(df), "n_treated": int(a.sum()),
        "ess_treated": effective_sample_size(w[a == 1]), "ess_control": effective_sample_size(w[a == 0]),
        "share_outside_overlap": out_of_overlap,
        "max_abs_smd_before": float(smd(df, treat, covars).abs().max()),
        "max_abs_smd_after": float(after.abs().max()),
        "positivity_ok": out_of_overlap < 0.05, "balance_ok": bool(after.abs().max() < 0.1),
    }


def individual_effects(train, new, treat, outcome, covars, subject=None, reps=200, seed=42) -> pd.DataFrame:
    """Estimated ARR for each person in `new`, with a bootstrap interval.

    Weighted outcome model in each arm (a "T-learner"), predicting both risks per person.
    These are model-based and wider in the tails; treat them as hypotheses for review.
    """
    rng, draws = np.random.default_rng(seed), []
    for _ in range(reps + 1):
        b = train if not draws else _resample(train, subject, rng)
        w, _ = stabilised_weights(b, treat, covars)
        mu, sd = b[covars].to_numpy(float).mean(0), b[covars].to_numpy(float).std(0)
        sd = np.where(sd == 0, 1, sd)
        xb, xn = (b[covars].to_numpy(float) - mu) / sd, (new[covars].to_numpy(float) - mu) / sd
        risk = {}
        for arm in (0, 1):
            m = b[treat].to_numpy(int) == arm
            risk[arm] = _logit_fit(xb[m], b[outcome].to_numpy(int)[m], w[m]).predict_proba(xn)[:, 1]
        draws.append(risk[0] - risk[1])
    point, boot = draws[0], np.array(draws[1:])
    return pd.DataFrame({"arr": point, "lo": np.percentile(boot, 2.5, axis=0),
                         "hi": np.percentile(boot, 97.5, axis=0)}, index=new.index)
