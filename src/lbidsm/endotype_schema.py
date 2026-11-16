"""Variable layers for adult-onset diabetes endotypes (SAID, SIDD, SIRD, MOD, MARD).

Research-only. This module records which variables the standard data-driven scheme uses,
the extended layers the proposal adds, and a transparent preliminary workflow. It does not
reproduce any published cluster centres, so labels it suggests are for a clinician to confirm.

Standard scheme: six routine variables (GAD antibodies, age at diagnosis, BMI, HbA1c,
HOMA2-B, HOMA2-IR). Extended layers: L2 clinical vulnerability, L3 CGM metrics,
L4 dynamic stability (exploratory).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from .endotypes import EndotypeClusterer

ENDOTYPES = {
    "SAID": "Severe autoimmune diabetes: immune-mediated beta-cell destruction, autoantibody positive",
    "SIDD": "Severe insulin-deficient diabetes: low beta-cell function, high HbA1c",
    "SIRD": "Severe insulin-resistant diabetes: high insulin resistance",
    "MOD": "Mild obesity-related diabetes: high BMI without severe resistance or beta-cell failure",
    "MARD": "Mild age-related diabetes: older onset, mild metabolic alteration",
}

ROUTINE_SIX = ["gad_antibody_positive", "age_at_diagnosis", "bmi", "hba1c_percent", "homa2_b", "homa2_ir"]
L2_CLINICAL = ["egfr", "ckd_stage", "ascvd", "heart_failure", "medication_exposure_history"]
L3_CGM = ["cgm_mean_glucose", "tir_70_180", "tbr_70", "tbr_54", "glucose_cv"]
L4_DYNAMIC = ["return_time_tau", "transient_gain_g"]  # exploratory
LAYERS = {"routine_six": ROUTINE_SIX, "L2_clinical_vulnerability": L2_CLINICAL,
          "L3_cgm_metrics": L3_CGM, "L4_dynamic_stability_exploratory": L4_DYNAMIC}


def coverage_report(df: pd.DataFrame) -> pd.DataFrame:
    """For each layer: which variables are present and what share of subjects has each."""
    rows = []
    for layer, cols in LAYERS.items():
        for c in cols:
            have = c in df.columns
            rows.append({"layer": layer, "variable": c, "present": have,
                         "non_missing_share": float(df[c].notna().mean()) if have else 0.0})
    return pd.DataFrame(rows)


def check_homa2(df: pd.DataFrame) -> list[str]:
    """Warn when only the older HOMA1 index is available; the scheme calls for HOMA2 values."""
    notes = []
    if not {"homa2_b", "homa2_ir"} <= set(df.columns):
        notes.append("homa2_b / homa2_ir missing: compute them with the HOMA2 calculator from fasting "
                     "glucose and C-peptide or insulin. The HOMA1 value derived in covariates.py is "
                     "not the same quantity and must not be substituted silently.")
    return notes


def preliminary_endotypes(df: pd.DataFrame, k: int = 4, seed: int = 42, extra_columns: list[str] | None = None):
    """Transparent two-step preliminary workflow.

    1. Autoantibody positive subjects are set aside as SAID candidates (a rule, not a cluster).
    2. The rest are clustered on age at diagnosis, BMI, HbA1c, HOMA2-B and HOMA2-IR, plus any
       `extra_columns` from the L2 and L3 layers. k=4 mirrors the four non-autoimmune endotypes.
    Returns (labels indexed by subject_id, profile of cluster means, quality dict).
    Cluster numbers are NOT endotype names; call `suggest_names` for a heuristic starting point.
    """
    need = ["subject_id"] + ROUTINE_SIX
    miss = [c for c in need if c not in df.columns]
    if miss:
        raise ValueError(f"Missing routine variables: {miss}")
    d = df.copy()
    d["subject_id"] = d.subject_id.astype(str)
    said = d[d.gad_antibody_positive == 1]
    rest = d[d.gad_antibody_positive != 1]
    cols = ["age_at_diagnosis", "bmi", "hba1c_percent", "homa2_b", "homa2_ir"] + list(extra_columns or [])
    cl = EndotypeClusterer(columns=cols, k_range=(k,), seed=seed, n_boot=30, use_pca=False).fit(rest)
    labels = cl.transform(rest).astype(object)
    labels = pd.concat([labels, pd.Series("SAID_candidate", index=said.subject_id.values)])
    return labels, cl.profile(rest), cl.quality_


def suggest_names(profile: pd.DataFrame) -> dict:
    """Heuristic names from cluster means. Highest value of the defining variable wins; a human decides.

    SIDD: lowest HOMA2-B (tie-break high HbA1c). SIRD: highest HOMA2-IR. MOD: highest BMI.
    MARD: oldest age at diagnosis. Each name is used once; leftovers stay unnamed.
    """
    left, names = set(profile.index), {}
    for name, col, hi in [("SIDD", "homa2_b", False), ("SIRD", "homa2_ir", True),
                          ("MOD", "bmi", True), ("MARD", "age_at_diagnosis", True)]:
        if col in profile.columns and left:
            pick = profile.loc[list(left), col].idxmax() if hi else profile.loc[list(left), col].idxmin()
            names[int(pick)] = f"{name} (suggested)"
            left.discard(pick)
    return names
