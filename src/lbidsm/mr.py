"""Two-sample summary-data Mendelian randomisation (MR) for drug-target filtering.

Research-only and hypothesis-generating. Nothing here is a clinical tool, and a passing
result is a Tier C *hypothesis* that a target is causally linked to the outcome, never proof.

Input is a harmonised table, one row per genetic instrument (a cis-acting pQTL or eQTL):
    snp, beta_x, se_x   effect of the variant on the exposure (protein or expression level)
    beta_y, se_y        effect of the same variant, same effect allele, on the outcome
Alleles must already be harmonised to the same effect allele; this module cannot check that.

Layout: estimators -> instrument strength -> colocalisation -> reverse MR -> safety read-across
-> stratified MR -> the combined target filter -> a synthetic generator used only by tests.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats

REQUIRED = ["snp", "beta_x", "se_x", "beta_y", "se_y"]


def _check(df: pd.DataFrame) -> pd.DataFrame:
    miss = [c for c in REQUIRED if c not in df.columns]
    if miss:
        raise ValueError(f"MR table is missing columns: {miss}")
    out = df.dropna(subset=REQUIRED).copy()
    if (out.se_x <= 0).any() or (out.se_y <= 0).any():
        raise ValueError("Standard errors must be positive")
    if out.snp.duplicated().any():
        raise ValueError("Each instrument (snp) must appear once")
    return out.reset_index(drop=True)


def _row(method: str, beta: float, se: float, n: int, df_t: float | None = None, **extra) -> dict:
    z = beta / se if se > 0 else np.nan
    p = 2 * (stats.t.sf(abs(z), df_t) if df_t else stats.norm.sf(abs(z)))
    crit = stats.t.ppf(0.975, df_t) if df_t else stats.norm.ppf(0.975)
    return {"method": method, "n_snps": n, "beta": float(beta), "se": float(se),
            "ci_low": float(beta - crit * se), "ci_high": float(beta + crit * se), "p": float(p), **extra}


# ---------------------------------------------------------------- estimators
def wald_ratio(df: pd.DataFrame) -> dict:
    """One instrument: beta = beta_y / beta_x, first-order standard error se_y / |beta_x|."""
    d = _check(df)
    if len(d) != 1:
        raise ValueError("wald_ratio needs exactly one instrument")
    r = d.iloc[0]
    return _row("Wald ratio", r.beta_y / r.beta_x, r.se_y / abs(r.beta_x), 1)


def cochran_q(df: pd.DataFrame) -> dict:
    """Heterogeneity of the per-instrument ratio estimates around the IVW estimate."""
    d = _check(df)
    ratio, se = d.beta_y / d.beta_x, d.se_y / d.beta_x.abs()
    w = 1 / se**2
    bar = (w * ratio).sum() / w.sum()
    q = float((w * (ratio - bar) ** 2).sum())
    dof = len(d) - 1
    return {"Q": q, "df": dof, "p": float(stats.chi2.sf(q, dof)) if dof > 0 else np.nan,
            "I2": float(max(0.0, (q - dof) / q)) if q > 0 and dof > 0 else 0.0}


def ivw(df: pd.DataFrame) -> dict:
    """Inverse-variance weighted estimate, no intercept, multiplicative random effects.

    The standard error is inflated by sqrt(Q/(n-1)) when there is more heterogeneity than
    chance would give, and never deflated below the fixed-effect value.
    """
    d = _check(df)
    if len(d) < 2:
        return wald_ratio(d)
    w = d.beta_x**2 / d.se_y**2
    beta = float((d.beta_x * d.beta_y / d.se_y**2).sum() / w.sum())
    se_fixed = float(1 / np.sqrt(w.sum()))
    q = cochran_q(d)
    se = se_fixed * max(1.0, np.sqrt(q["Q"] / q["df"]))
    return _row("IVW (random effects)", beta, se, len(d), Q=q["Q"], Q_p=q["p"], I2=q["I2"])


def mr_egger(df: pd.DataFrame) -> dict:
    """MR-Egger: weighted regression with a free intercept that picks up directional pleiotropy.

    Instruments are first oriented so that beta_x is positive. Needs at least 3 instruments
    and is low-powered with few; report it as a sensitivity check, not as the main estimate.
    """
    d = _check(df)
    if len(d) < 3:
        raise ValueError("MR-Egger needs at least 3 instruments")
    sign = np.sign(d.beta_x.to_numpy())
    bx, by, sy = np.abs(d.beta_x.to_numpy()), d.beta_y.to_numpy() * sign, d.se_y.to_numpy()
    X = np.column_stack([np.ones(len(d)), bx])
    W = np.diag(1 / sy**2)
    cov = np.linalg.inv(X.T @ W @ X)
    coef = cov @ X.T @ W @ by
    resid = by - X @ coef
    dof = len(d) - 2
    sigma2 = float((resid**2 / sy**2).sum() / dof)
    se = np.sqrt(np.diag(cov) * max(1.0, sigma2))
    out = _row("MR-Egger", coef[1], se[1], len(d), df_t=dof)
    out["intercept"] = float(coef[0])
    out["intercept_se"] = float(se[0])
    out["intercept_p"] = float(2 * stats.t.sf(abs(coef[0] / se[0]), dof))
    return out


def weighted_median(df: pd.DataFrame, n_boot: int = 500, seed: int = 42) -> dict:
    """Weighted median: consistent if at least half the weight comes from valid instruments."""
    d = _check(df)
    if len(d) < 3:
        raise ValueError("Weighted median needs at least 3 instruments")

    def est(bx, by, sy):
        ratio, w = by / bx, bx**2 / sy**2
        order = np.argsort(ratio)
        ratio, w = ratio[order], w[order]
        cum = np.cumsum(w) - 0.5 * w
        cum /= w.sum()
        below = np.max(np.where(cum < 0.5)) if (cum < 0.5).any() else 0
        hi = min(below + 1, len(ratio) - 1)
        return float(ratio[below] + (ratio[hi] - ratio[below]) * (0.5 - cum[below]) / (cum[hi] - cum[below]))

    bx, by, sx, sy = (d[c].to_numpy() for c in ["beta_x", "beta_y", "se_x", "se_y"])
    beta = est(bx, by, sy)
    rng = np.random.default_rng(seed)
    boots = [est(rng.normal(bx, sx), rng.normal(by, sy), sy) for _ in range(n_boot)]
    return _row("Weighted median", beta, float(np.std(boots, ddof=1)), len(d))


# ------------------------------------------------------ instrument strength
def instrument_strength(df: pd.DataFrame, min_f: float = 10.0) -> pd.DataFrame:
    """Per-instrument F = (beta_x / se_x)^2. Below 10 is conventionally a weak instrument."""
    d = _check(df)
    out = d[["snp"]].copy()
    out["F"] = (d.beta_x / d.se_x) ** 2
    out["weak"] = out.F < min_f
    return out


def steiger_direction(df: pd.DataFrame, n_x: float, n_y: float) -> dict:
    """Do the instruments explain more variance in the exposure than in the outcome?

    Variance explained is approximated from each z-score as z^2 / (z^2 + n). If the outcome
    is explained better, the assumed direction exposure -> outcome is doubtful.
    """
    d = _check(df)
    zx2, zy2 = (d.beta_x / d.se_x) ** 2, (d.beta_y / d.se_y) ** 2
    r2x, r2y = zx2 / (zx2 + n_x), zy2 / (zy2 + n_y)
    return {"share_correct_direction": float((r2x > r2y).mean()), "r2_exposure": float(r2x.sum()),
            "r2_outcome": float(r2y.sum()), "direction_ok": bool(r2x.sum() > r2y.sum())}


def run_mr(df: pd.DataFrame) -> pd.DataFrame:
    """All applicable estimators in one table: Wald ratio for one instrument, else IVW plus sensitivity."""
    d = _check(df)
    if len(d) == 0:
        raise ValueError("No usable instruments")
    if len(d) == 1:
        return pd.DataFrame([wald_ratio(d)])
    rows = [ivw(d)]
    if len(d) >= 3:
        rows += [mr_egger(d), weighted_median(d)]
    return pd.DataFrame(rows)


# ----------------------------------------------------------- colocalisation
def _logsum(x: np.ndarray) -> float:
    m = np.max(x)
    return float(m + np.log(np.exp(x - m).sum()))


def _log_abf(beta: np.ndarray, se: np.ndarray, prior_sd: float) -> np.ndarray:
    """Wakefield approximate Bayes factor on the log scale for each variant in the region."""
    z2, v = (beta / se) ** 2, se**2
    r = prior_sd**2 / (prior_sd**2 + v)
    return 0.5 * (np.log(1 - r) + r * z2)


def colocalisation(region: pd.DataFrame, p1: float = 1e-4, p2: float = 1e-4, p12: float = 1e-5,
                   prior_sd_x: float = 0.15, prior_sd_y: float = 0.2) -> dict:
    """Bayesian colocalisation (Giambartolomei et al. 2014) from summary statistics.

    `region` holds every variant in one locus present in both studies, with beta_x, se_x
    (exposure) and beta_y, se_y (outcome). It returns posterior probabilities of five
    hypotheses: H0 neither trait has a signal, H1 only exposure, H2 only outcome, H3 both
    but different causal variants, H4 both share one causal variant. PP.H4 >= 0.8 is the
    usual threshold for colocalised. The single-causal-variant assumption is a limitation.
    """
    d = _check(region)
    if len(d) < 10:
        raise ValueError("Colocalisation needs the whole locus (at least 10 variants), not just the lead variant")
    l1 = _log_abf(d.beta_x.to_numpy(), d.se_x.to_numpy(), prior_sd_x)
    l2 = _log_abf(d.beta_y.to_numpy(), d.se_y.to_numpy(), prior_sd_y)
    s1, s2, s12 = _logsum(l1), _logsum(l2), _logsum(l1 + l2)
    both = s1 + s2
    h3_inner = both + np.log1p(-np.exp(min(s12 - both, -1e-12)))
    lh = np.array([0.0, np.log(p1) + s1, np.log(p2) + s2, np.log(p1) + np.log(p2) + h3_inner,
                   np.log(p12) + s12])
    pp = np.exp(lh - _logsum(lh))
    return {"PP.H0": float(pp[0]), "PP.H1": float(pp[1]), "PP.H2": float(pp[2]),
            "PP.H3": float(pp[3]), "PP.H4": float(pp[4]), "n_variants": len(d),
            "colocalised": bool(pp[4] >= 0.8)}


# --------------------------------------------------------------- reverse MR
def reverse_mr(disease_instruments: pd.DataFrame, alpha: float = 0.05) -> dict:
    """Does the disease change the protein? Instruments are variants for the DISEASE.

    Columns: beta_x, se_x = effect on the disease (now the exposure); beta_y, se_y = effect
    on the protein level (now the outcome). A significant result means the arrow may run
    backwards, so the protein could be a consequence of diabetes, not a cause.
    """
    res = run_mr(disease_instruments).iloc[0]
    return {"beta": float(res.beta), "p": float(res.p), "n_snps": int(res.n_snps),
            "reverse_signal": bool(res.p < alpha), "method": res.method}


# -------------------------------------------------------- safety read-across
def safety_read_across(instruments: pd.DataFrame, alpha: float = 0.05) -> pd.DataFrame:
    """MR of the same target on many non-diabetes traits, to spot on-target side effects early.

    `instruments` is long format: snp, beta_x, se_x (exposure) and, per `trait`, beta_y, se_y.
    A Bonferroni threshold alpha / number_of_traits is applied; flags are prompts for a
    clinician to review, not findings.
    """
    if "trait" not in instruments.columns:
        raise ValueError("Safety read-across needs a trait column")
    rows = []
    for trait, grp in instruments.groupby("trait"):
        r = run_mr(grp.drop(columns="trait")).iloc[0]
        rows.append({"trait": trait, "method": r.method, "beta": r.beta, "se": r.se, "p": r.p})
    out = pd.DataFrame(rows)
    out["bonferroni_threshold"] = alpha / max(1, len(out))
    out["flag"] = out.p < out.bonferroni_threshold
    return out.sort_values("p").reset_index(drop=True)


# ------------------------------------------------------------ stratified MR
def stratified_mr(tables: dict[str, pd.DataFrame]) -> dict:
    """Run MR separately in each stratum (for example each endotype) and test whether they differ.

    `tables` maps stratum name -> harmonised table whose outcome statistics come from that
    stratum only. The heterogeneity test is Cochran's Q across the stratum estimates.
    Needs stratum-specific genetic summary statistics, which are rare; strata are usually
    small, so wide intervals are expected and a null difference is not evidence of no difference.
    """
    if len(tables) < 2:
        raise ValueError("Stratified MR needs at least two strata")
    rows = []
    for name, tab in tables.items():
        r = run_mr(tab).iloc[0]
        rows.append({"stratum": name, "method": r.method, "n_snps": r.n_snps, "beta": r.beta,
                     "se": r.se, "ci_low": r.ci_low, "ci_high": r.ci_high, "p": r.p})
    est = pd.DataFrame(rows)
    w = 1 / est.se**2
    bar = (w * est.beta).sum() / w.sum()
    q = float((w * (est.beta - bar) ** 2).sum())
    dof = len(est) - 1
    return {"estimates": est, "Q_between": q, "df": dof, "p_heterogeneity": float(stats.chi2.sf(q, dof)),
            "differs_between_strata": bool(stats.chi2.sf(q, dof) < 0.05)}


# ---------------------------------------------------------- the target filter
def target_filter(mr_table: pd.DataFrame, region: pd.DataFrame | None = None,
                  disease_instruments: pd.DataFrame | None = None,
                  safety: pd.DataFrame | None = None, alpha: float = 0.05) -> dict:
    """Combine the checks into one verdict that fails closed.

    A target passes only if: instruments are strong (all F >= 10); the main MR estimate is
    significant; Egger intercept (when computed) shows no directional pleiotropy; colocalisation
    PP.H4 >= 0.8; reverse MR shows no reverse signal. Any check that could not be run counts
    as NOT passed. Safety read-across never blocks a target; it lists traits to review.
    """
    reasons, d = [], _check(mr_table)
    strength = instrument_strength(d)
    main = run_mr(d)
    primary = main.iloc[0]
    checks = {"strong_instruments": bool((~strength.weak).all()),
              "mr_significant": bool(primary.p < alpha)}
    egger = main[main.method == "MR-Egger"]
    checks["no_directional_pleiotropy"] = bool(len(egger) and egger.iloc[0].intercept_p >= alpha)
    coloc = colocalisation(region) if region is not None else None
    checks["colocalised"] = bool(coloc and coloc["colocalised"])
    rev = reverse_mr(disease_instruments) if disease_instruments is not None else None
    checks["no_reverse_signal"] = bool(rev is not None and not rev["reverse_signal"])
    for name, ok in checks.items():
        if not ok:
            reasons.append(f"not met: {name}")
    flags = []
    if safety is not None:
        flags = safety_read_across(safety).query("flag").trait.tolist()
    passed = all(checks.values())
    return {"verdict": "hypothesis_supported (Tier C, hypothesis only)" if passed else "not_supported",
            "checks": checks, "reasons": reasons, "mr": main, "colocalisation": coloc,
            "reverse_mr": rev, "safety_flags_for_review": flags}


# ------------------------------------------------------ synthetic test data
def synthetic_mr_data(n_snps: int = 8, true_beta: float = 0.4, seed: int = 0, pleiotropy: float = 0.0,
                      n_x: int = 20000, n_y: int = 50000) -> pd.DataFrame:
    """Simulated instruments with a known causal effect. For tests and demos only, never evidence."""
    rng = np.random.default_rng(seed)
    bx = rng.uniform(0.08, 0.25, n_snps) * rng.choice([-1, 1], n_snps)
    sx = np.full(n_snps, 1 / np.sqrt(n_x) * 2)
    sy = np.full(n_snps, 1 / np.sqrt(n_y) * 2)
    by = true_beta * bx + pleiotropy * np.sign(bx) + rng.normal(0, sy)  # directional pleiotropy
    return pd.DataFrame({"snp": [f"rs{i}" for i in range(n_snps)], "beta_x": bx + rng.normal(0, sx),
                         "se_x": sx, "beta_y": by, "se_y": sy})


def synthetic_locus(n_variants: int = 60, shared: bool = True, seed: int = 0) -> pd.DataFrame:
    """A simulated locus: one causal variant for the exposure; the outcome shares it or uses another."""
    rng = np.random.default_rng(seed)
    se = np.full(n_variants, 0.02)
    cx, cy = 10, (10 if shared else 40)
    bx, by = rng.normal(0, 0.02, n_variants), rng.normal(0, 0.02, n_variants)
    bx[cx] += 0.2
    by[cy] += 0.16
    bx[cx - 2:cx + 3] += 0.08 * np.array([0.5, 0.8, 0, 0.8, 0.5])  # linkage-disequilibrium neighbours
    by[cy - 2:cy + 3] += 0.06 * np.array([0.5, 0.8, 0, 0.8, 0.5])
    return pd.DataFrame({"snp": [f"v{i}" for i in range(n_variants)], "beta_x": bx, "se_x": se,
                         "beta_y": by, "se_y": se})
