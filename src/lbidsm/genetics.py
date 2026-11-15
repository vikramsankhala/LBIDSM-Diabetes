"""Mendelian randomisation (MR) from published summary statistics. Research use only.

Idea in one line: genes are handed out at conception, so a gene variant that nudges
an exposure (for example the activity of a drug target) acts like a natural,
randomly assigned "dose". If that variant also shifts the outcome, the exposure
probably affects the outcome. Three assumptions must hold: the variant is strongly
linked to the exposure, it is not linked to confounders, and it affects the
outcome only through the exposure. Pleiotropy checks (MR-Egger, Cochran's Q,
weighted median) probe the third assumption; they cannot prove it.

Input: one row per variant with beta and standard error for exposure and outcome,
effect and other alleles, and effect-allele frequency.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

PALINDROMIC = {frozenset("AT"), frozenset("CG")}


def harmonise(exposure: pd.DataFrame, outcome: pd.DataFrame, palindromic_eaf=(0.42, 0.58)) -> pd.DataFrame:
    """Put both studies on the same effect allele. Columns: snp, ea, oa, eaf, beta, se.

    Allele mismatches are dropped. Palindromic variants (A/T, C/G) with allele
    frequency near 0.5 cannot be oriented reliably and are dropped.
    """
    m = exposure.merge(outcome, on="snp", suffixes=("_x", "_y"))
    same = (m.ea_x == m.ea_y) & (m.oa_x == m.oa_y)
    flipped = (m.ea_x == m.oa_y) & (m.oa_x == m.ea_y)
    m = m[same | flipped].copy()
    m["beta_y"] = np.where(m.ea_x == m.ea_y, m.beta_y, -m.beta_y)
    pal = m.apply(lambda r: frozenset((r.ea_x, r.oa_x)) in PALINDROMIC, axis=1)
    near_half = m.eaf_x.between(*palindromic_eaf)
    m = m[~(pal & near_half)]
    return m.rename(columns={"beta_x": "bx", "se_x": "sx", "beta_y": "by", "se_y": "sy"})[["snp", "bx", "sx", "by", "sy"]]


def f_statistic(bx, sx):
    """Instrument strength per variant. Below about 10 counts as weak."""
    return (np.asarray(bx) / np.asarray(sx)) ** 2


def select_instruments(h: pd.DataFrame, min_f: float = 10.0) -> pd.DataFrame:
    return h[f_statistic(h.bx, h.sx) >= min_f].reset_index(drop=True)


def wald_ratio(bx, by, sy):
    bx, by, sy = map(np.asarray, (bx, by, sy))
    return by / bx, np.abs(sy / bx)


def ivw(h: pd.DataFrame) -> dict:
    """Inverse-variance weighted estimate with a random-effects standard error when heterogeneous."""
    w = h.bx ** 2 / h.sy ** 2
    beta = float((h.bx * h.by / h.sy ** 2).sum() / w.sum())
    se_fixed = float(1 / np.sqrt(w.sum()))
    q = float((((h.by - beta * h.bx) / h.sy) ** 2).sum())
    df = len(h) - 1
    se = se_fixed * max(1.0, np.sqrt(q / df)) if df > 0 else se_fixed
    return {"beta": beta, "se": se, "p": float(2 * stats.norm.sf(abs(beta / se))),
            "cochran_q": q, "q_df": df, "q_p": float(stats.chi2.sf(q, df)) if df > 0 else np.nan,
            "i2_gx": None}


def egger(h: pd.DataFrame) -> dict:
    """MR-Egger: the intercept tests for directional pleiotropy; the slope is the corrected effect."""
    sign = np.where(h.bx < 0, -1, 1)
    x, y, w = (h.bx * sign).to_numpy(), (h.by * sign).to_numpy(), (1 / h.sy ** 2).to_numpy()
    X = np.column_stack([np.ones(len(x)), x])
    xtwx = X.T @ (w[:, None] * X)
    coef = np.linalg.solve(xtwx, X.T @ (w * y))
    resid = y - X @ coef
    s2 = max(1.0, float((w * resid ** 2).sum() / (len(x) - 2)))
    se = np.sqrt(np.diag(np.linalg.inv(xtwx)) * s2)
    t = stats.t(df=len(x) - 2)
    return {"intercept": float(coef[0]), "intercept_se": float(se[0]), "intercept_p": float(2 * t.sf(abs(coef[0] / se[0]))),
            "beta": float(coef[1]), "se": float(se[1]), "p": float(2 * t.sf(abs(coef[1] / se[1])))}


def weighted_median(h: pd.DataFrame, reps: int = 1000, seed: int = 42) -> dict:
    """Consistent if at least half the weight comes from valid instruments."""
    rng = np.random.default_rng(seed)

    def wm(bx, by, sy):
        ratio, se = by / bx, np.abs(sy / bx)
        order = np.argsort(ratio)
        ratio, w = ratio[order], (1 / se ** 2)[order]
        w = w / w.sum()
        cum = np.cumsum(w) - 0.5 * w
        below = np.max(np.flatnonzero(cum < 0.5)) if (cum < 0.5).any() else 0
        below = min(below, len(ratio) - 2)
        return ratio[below] + (ratio[below + 1] - ratio[below]) * (0.5 - cum[below]) / (cum[below + 1] - cum[below])

    bx, by, sy = h.bx.to_numpy(), h.by.to_numpy(), h.sy.to_numpy()
    beta = float(wm(bx, by, sy))
    boots = [wm(bx, rng.normal(by, sy), sy) for _ in range(reps)]
    se = float(np.std(boots, ddof=1))
    return {"beta": beta, "se": se, "p": float(2 * stats.norm.sf(abs(beta / se)))}


def mr_summary(exposure: pd.DataFrame, outcome: pd.DataFrame, min_f: float = 10.0) -> dict:
    """Harmonise, filter weak instruments, then run all estimators and flag warnings."""
    h = select_instruments(harmonise(exposure, outcome), min_f)
    if len(h) < 3:
        return {"status": "inconclusive", "reason": "fewer than three usable instruments", "n_snps": len(h)}
    res = {"status": "estimated", "n_snps": len(h), "mean_f": float(f_statistic(h.bx, h.sx).mean()),
           "ivw": ivw(h), "egger": egger(h), "weighted_median": weighted_median(h), "warnings": []}
    if res["ivw"]["q_p"] < 0.05:
        res["warnings"].append("heterogeneity across variants (Cochran Q p<0.05): check pleiotropy")
    if res["egger"]["intercept_p"] < 0.05:
        res["warnings"].append("MR-Egger intercept differs from zero: directional pleiotropy likely")
    return res
