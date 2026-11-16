"""Research-only CGM event prediction and leakage-aware cohort construction.

NOT a validated clinical model. Data input must contain subject_id, timestamp,
glucose_mg_dl; each subject is handled independently.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

FEATURES_BASIC = ["last_glucose", "slope_15"]
FEATURES_CGM = FEATURES_BASIC + ["mean_60", "sd_60", "min_60", "max_60", "slope_60", "hour_sin", "hour_cos"]

def make_examples(df: pd.DataFrame, horizon_minutes: int = 60, history_minutes: int = 60,
                  stride_minutes: int = 30, max_gap_minutes: int = 16,
                  min_history_points: int = 4) -> pd.DataFrame:
    """Construct causal windows; target is any *observed* future CGM value <54.

    Only fully observed continuous history and future intervals are accepted.
    The event is a CGM sample-level surrogate, NOT adjudicated clinical hypoglycemia.
    """
    required = {"subject_id", "timestamp", "glucose_mg_dl"}
    if not required.issubset(df.columns):
        raise ValueError(f"Missing columns: {sorted(required - set(df.columns))}")
    if horizon_minutes <= 0 or history_minutes <= 0 or stride_minutes <= 0:
        raise ValueError("Horizons and stride must be positive")
    d = df[list(required)].copy()
    d["timestamp"] = pd.to_datetime(d["timestamp"], utc=True, errors="coerce")
    d["glucose_mg_dl"] = pd.to_numeric(d["glucose_mg_dl"], errors="coerce")
    d = d.dropna().loc[lambda z: z.glucose_mg_dl.between(20, 600)]
    rows = []
    for sid, group in d.groupby("subject_id", sort=True):
        group = group.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
        times = group.timestamp.astype("int64").to_numpy() / 60e9
        glucose = group.glucose_mg_dl.to_numpy(dtype=float)
        if len(glucose) < min_history_points + 2:
            continue
        # Split at gaps so no feature or label spans missing observations.
        boundaries = np.r_[0, np.flatnonzero(np.diff(times) > max_gap_minutes) + 1, len(times)]
        for left, right in zip(boundaries[:-1], boundaries[1:]):
            t, g = times[left:right], glucose[left:right]
            if len(g) < min_history_points + 2:
                continue
            next_anchor = t[0] + history_minutes
            for j in range(len(t)):
                if t[j] < next_anchor:
                    continue
                if t[j] + horizon_minutes > t[-1]:
                    break
                if t[j] < next_anchor:
                    continue
                h = (t >= t[j] - history_minutes) & (t <= t[j])
                f = (t > t[j]) & (t <= t[j] + horizon_minutes)
                if h.sum() < min_history_points or not f.any():
                    continue
                # Require sufficient time support at the edges; no interpolation.
                if t[j] - t[h][0] > history_minutes + 1 or t[j] - t[h][0] < history_minutes - max_gap_minutes:
                    continue
                if t[f][-1] < t[j] + horizon_minutes - max_gap_minutes:
                    continue
                gh, th = g[h], t[h]
                slope_15_mask = th >= t[j] - 15
                recent = gh[slope_15_mask]
                recent_t = th[slope_15_mask]
                slope15 = float((recent[-1] - recent[0]) / (recent_t[-1] - recent_t[0])) if len(recent) > 1 and recent_t[-1] > recent_t[0] else 0.0
                hour = pd.Timestamp(int(t[j] * 60e9), tz="UTC").hour
                rows.append({
                    "subject_id": str(sid),
                    "as_of": pd.Timestamp(int(t[j] * 60e9), tz="UTC"),
                    "last_glucose": float(gh[-1]),
                    "slope_15": slope15,
                    "mean_60": float(gh.mean()),
                    "sd_60": float(gh.std(ddof=0)),
                    "min_60": float(gh.min()),
                    "max_60": float(gh.max()),
                    "slope_60": float((gh[-1] - gh[0]) / (th[-1] - th[0])),
                    "hour_sin": float(np.sin(2 * np.pi * hour / 24)),
                    "hour_cos": float(np.cos(2 * np.pi * hour / 24)),
                    "event_lt54": int((g[f] < 54).any()),
                })
                next_anchor = t[j] + stride_minutes
    return pd.DataFrame(rows)

def cohort_split(examples: pd.DataFrame, seed: int = 42):
    """Disjoint subjects: train 60%, calibration 20%, held-out test 20%."""
    ids = np.array(sorted(examples.subject_id.unique()))
    if len(ids) < 10:
        raise ValueError("At least 10 distinct subjects required for 60/20/20 patient-held-out evaluation")
    rng = np.random.default_rng(seed)
    ids = rng.permutation(ids)
    ntrain = int(0.6 * len(ids))
    ncal = int(0.2 * len(ids))
    tr, ca, te = [set(x) for x in (ids[:ntrain], ids[ntrain:ntrain+ncal], ids[ntrain+ncal:])]
    assert not (tr & ca or tr & te or ca & te)
    return (examples[examples.subject_id.isin(s)].copy() for s in (tr, ca, te))

def benchmark(examples: pd.DataFrame, seed: int = 42) -> tuple[pd.DataFrame, dict]:
    """Fit baseline and extended logistic models, calibrate on separate subjects.

    No result is considered clinically validated; prevalence and event counts are
    reported and the procedure refuses single-class splits.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss
    from sklearn.isotonic import IsotonicRegression
    train, calibration, test = tuple(cohort_split(examples, seed))
    report = {"seed": seed, "subjects": {}, "rows": {}, "positives": {}, "event_definition": "any observed CGM sample <54 mg/dL within next 60 minutes (surrogate)"}
    for name, frame in (("train", train), ("calibration", calibration), ("test", test)):
        report["subjects"][name] = int(frame.subject_id.nunique())
        report["rows"][name] = len(frame)
        report["positives"][name] = int(frame.event_lt54.sum())
        if frame.event_lt54.nunique() != 2:
            raise ValueError(f"{name} split lacks both outcome classes; do not publish performance estimates")
    result = []
    for name, columns in (("current_glucose", ["last_glucose"]), ("glucose_plus_slope", FEATURES_BASIC), ("cgm_history", FEATURES_CGM)):
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight=None, random_state=seed))
        model.fit(train[columns], train.event_lt54)
        raw_cal = model.predict_proba(calibration[columns])[:, 1]
        raw_test = model.predict_proba(test[columns])[:, 1]
        # Platt scaling on independent calibration subjects, not test.
        calibrator = LogisticRegression(max_iter=1000, random_state=seed)
        calibrator.fit(raw_cal.reshape(-1, 1), calibration.event_lt54)
        pred = np.clip(calibrator.predict_proba(raw_test.reshape(-1, 1))[:, 1], 1e-6, 1 - 1e-6)
        y = test.event_lt54.to_numpy()
        result.append({
            "model": name, "n_test": len(y), "test_events": int(y.sum()),
            "prevalence": float(y.mean()),
            "auroc": float(roc_auc_score(y, pred)),
            "auprc": float(average_precision_score(y, pred)),
            "brier": float(brier_score_loss(y, pred)),
            "log_loss": float(log_loss(y, pred)),
        })
    return pd.DataFrame(result), report


def benchmark_extended(examples: pd.DataFrame, covariates: pd.DataFrame, seed: int = 42, C_static: float = 0.1):
    """Compare CGM-only logistic regression with versions that add baseline covariates.

    Models: cgm_history; + metabolic; + metabolic, genetic and treatment; + preliminary endotype.
    Imputation, scaling and clustering are fitted on training subjects only. Static covariates
    are constant within a subject, so effective sample size is the number of subjects, not
    windows; they are L2-penalised (C_static) and the report gives subject counts. Research only.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss
    from sklearn.pipeline import make_pipeline
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler
    from .covariates import attach_covariates, available, METABOLIC, GENETIC, TREATMENT
    from .endotypes import EndotypeClusterer, endotype_features

    data = attach_covariates(examples, covariates)
    train, calibration, test = tuple(cohort_split(data, seed))
    report = {"seed": seed, "subjects": {}, "positives": {},
              "event_definition": "any observed CGM sample <54 mg/dL within next 60 minutes (surrogate)"}
    for name, frame in (("train", train), ("calibration", calibration), ("test", test)):
        report["subjects"][name] = int(frame.subject_id.nunique())
        report["positives"][name] = int(frame.event_lt54.sum())
        if frame.event_lt54.nunique() != 2:
            raise ValueError(f"{name} split lacks both outcome classes; do not publish performance estimates")

    metab = available(train, METABOLIC)
    gen = available(train, GENETIC) + available(train, TREATMENT)
    sub_cov = covariates.assign(subject_id=covariates.subject_id.astype(str))
    sub_cov = sub_cov[sub_cov.subject_id.isin(train.subject_id.unique())]
    try:
        clus = EndotypeClusterer(seed=seed).fit(sub_cov)
        all_cov = covariates.assign(subject_id=covariates.subject_id.astype(str))
        labels = clus.transform(all_cov)
        for f in (train, calibration, test):
            f[[f"endotype_{j}" for j in range(1, clus.k_)]] = endotype_features(labels, clus.k_, f.subject_id)
        endo_cols = [f"endotype_{j}" for j in range(1, clus.k_)]
        report["endotype_quality"] = clus.quality_
        report["endotype_selection"] = clus.selection_.round(3).to_dict("records")
        report["endotype_profile"] = clus.profile(sub_cov).reset_index().to_dict("records")
    except ValueError as exc:
        endo_cols, report["endotype_quality"] = [], {"skipped": str(exc)}

    specs = [("cgm_history", FEATURES_CGM, [], 1.0),
             ("cgm_plus_metabolic", FEATURES_CGM, metab, C_static),
             ("cgm_plus_metabolic_genetic_treatment", FEATURES_CGM, metab + gen, C_static)]
    if endo_cols:
        specs.append(("cgm_plus_endotype", FEATURES_CGM, endo_cols, C_static))
    result = []
    for name, cgm_cols, static_cols, C in specs:
        cols = cgm_cols + static_cols
        if name != "cgm_history" and not static_cols:
            continue
        model = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                              LogisticRegression(C=C, max_iter=2000, random_state=seed))
        model.fit(train[cols], train.event_lt54)
        raw_cal = model.predict_proba(calibration[cols])[:, 1]
        raw_test = model.predict_proba(test[cols])[:, 1]
        calibrator = LogisticRegression(max_iter=1000, random_state=seed).fit(raw_cal.reshape(-1, 1), calibration.event_lt54)
        pred = np.clip(calibrator.predict_proba(raw_test.reshape(-1, 1))[:, 1], 1e-6, 1 - 1e-6)
        y = test.event_lt54.to_numpy()
        result.append({"model": name, "n_static_features": len(static_cols), "n_test": len(y), "test_events": int(y.sum()),
                       "prevalence": float(y.mean()), "auroc": float(roc_auc_score(y, pred)),
                       "auprc": float(average_precision_score(y, pred)), "brier": float(brier_score_loss(y, pred)),
                       "log_loss": float(log_loss(y, pred))})
    return pd.DataFrame(result), report
