"""Subject-level metabolic, genetic and treatment covariates for the prediction models.

Research-only. Covariates are *static baseline* values, one row per subject_id,
measured before the first prediction window. They are joined to window-level
examples and enter the same logistic-regression pipeline as the CGM features.

Genetic inputs are optional and must be pseudonymised, purpose-limited and
approved for use; this module never reads raw genotype files, only a derived
table (for example a polygenic risk score or SNP allele dosage 0/1/2).
"""
from __future__ import annotations
import numpy as np
import pandas as pd

METABOLIC = ["age_years", "bmi", "hba1c_percent", "fasting_glucose_mg_dl", "fasting_insulin_uU_ml",
             "homa_ir", "triglycerides_mg_dl", "hdl_mg_dl", "egfr", "diabetes_duration_years"]
GENETIC = ["prs_t2d", "tcf7l2_dosage", "kcnj11_dosage"]
TREATMENT = ["on_sulfonylurea", "on_insulin"]
ALL_COVARIATES = METABOLIC + GENETIC + TREATMENT


def prepare_covariates(cov: pd.DataFrame) -> pd.DataFrame:
    """Validate a one-row-per-subject table and derive HOMA-IR when possible.

    HOMA-IR = fasting glucose (mg/dL) x fasting insulin (uU/mL) / 405.
    Unknown columns are ignored; known columns are coerced to numeric.
    """
    if "subject_id" not in cov.columns:
        raise ValueError("Covariate table needs a subject_id column")
    out = cov.copy()
    out["subject_id"] = out["subject_id"].astype(str)
    if out.subject_id.duplicated().any():
        raise ValueError("Covariates must have exactly one row per subject_id (baseline values only)")
    for c in ALL_COVARIATES:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    if "homa_ir" not in out.columns and {"fasting_glucose_mg_dl", "fasting_insulin_uU_ml"} <= set(out.columns):
        out["homa_ir"] = out.fasting_glucose_mg_dl * out.fasting_insulin_uU_ml / 405.0
    keep = ["subject_id"] + [c for c in ALL_COVARIATES if c in out.columns]
    return out[keep]


def attach_covariates(examples: pd.DataFrame, cov: pd.DataFrame, min_coverage: float = 0.8) -> pd.DataFrame:
    """Left-join baseline covariates onto windows; refuse if too few subjects are covered."""
    cov = prepare_covariates(cov)
    covered = examples.subject_id.isin(cov.subject_id).groupby(examples.subject_id).first().mean()
    if covered < min_coverage:
        raise ValueError(f"Only {covered:.0%} of subjects have covariates; need at least {min_coverage:.0%}")
    return examples.merge(cov, on="subject_id", how="left", validate="m:1")


def available(frame: pd.DataFrame, group: list[str]) -> list[str]:
    """Columns of a group that are present and not entirely missing."""
    return [c for c in group if c in frame.columns and frame[c].notna().any()]


def synthetic_covariates(subject_ids, seed: int = 42, n_groups: int = 3, separation: float = 1.0) -> pd.DataFrame:
    """Synthetic baseline covariates with planted groups, for tests and demonstrations only.

    The planted structure exists to check that the code can recover groups. It says
    nothing about real physiology; do not cite results on these data as evidence.
    """
    rng = np.random.default_rng(seed)
    ids = [str(s) for s in subject_ids]
    grp = rng.integers(0, n_groups, len(ids))
    centres = {0: dict(bmi=24, hba1c=7.2, ins=7, tg=120, prs=-0.6, sulf=0.2),     # insulin-deficient-like
               1: dict(bmi=32, hba1c=7.8, ins=22, tg=210, prs=0.5, sulf=0.1),     # insulin-resistant-like
               2: dict(bmi=27, hba1c=8.6, ins=12, tg=150, prs=0.0, sulf=0.6)}     # mixed / high HbA1c
    mid = {key: float(np.mean([v[key] for v in centres.values()])) for key in centres[0]}
    rows = []
    for sid, k in zip(ids, grp):
        raw = centres[int(k) % 3]
        c = {key: mid[key] + separation * (raw[key] - mid[key]) for key in raw}
        glu = rng.normal(125, 12)
        ins = max(2.0, rng.normal(c["ins"], 3))
        rows.append({"subject_id": sid, "age_years": rng.normal(58, 8), "bmi": rng.normal(c["bmi"], 2.5),
                     "hba1c_percent": rng.normal(c["hba1c"], 0.5), "fasting_glucose_mg_dl": glu,
                     "fasting_insulin_uU_ml": ins, "triglycerides_mg_dl": rng.normal(c["tg"], 25),
                     "hdl_mg_dl": rng.normal(45, 7), "egfr": rng.normal(85, 12),
                     "diabetes_duration_years": abs(rng.normal(8, 4)),
                     "prs_t2d": rng.normal(c["prs"], 0.6),
                     "tcf7l2_dosage": int(rng.binomial(2, 0.3 + 0.1 * (k == 0))),
                     "on_sulfonylurea": int(rng.random() < c["sulf"]), "on_insulin": int(rng.random() < 0.15)})
    return prepare_covariates(pd.DataFrame(rows))
