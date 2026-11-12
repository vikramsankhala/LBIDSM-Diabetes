"""Expanded retrospective ShanghaiT2DM validation. No clinical deployment.

Inputs are independently downloaded CGM records. Outputs contain only aggregate
statistics and deidentified subject counts; no individual traces or identifiers.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss,
                             log_loss, roc_auc_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from lbidsm.prediction import FEATURES_BASIC, FEATURES_CGM, cohort_split, make_examples

MODELS = {
    "M0_current_glucose": ["last_glucose"],
    "M1_glucose_slope": FEATURES_BASIC,
    "M2_cgm_history": FEATURES_CGM,
}
METRICS = ("auroc", "auprc", "brier", "log_loss")

def scores(y, p):
    y = np.asarray(y, dtype=int)
    p = np.clip(np.asarray(p, dtype=float), 1e-7, 1 - 1e-7)
    if len(np.unique(y)) < 2:
        return None
    return {
        "auroc": float(roc_auc_score(y, p)),
        "auprc": float(average_precision_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p)),
    }

def fit_models(train, calibration, test, seed):
    out = {}
    for name, features in MODELS.items():
        base = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=seed))
        base.fit(train[features], train.event_lt54)
        pc = base.predict_proba(calibration[features])[:, 1]
        calibrator = LogisticRegression(max_iter=1000, random_state=seed)
        calibrator.fit(pc.reshape(-1, 1), calibration.event_lt54)
        pt = base.predict_proba(test[features])[:, 1]
        out[name] = np.clip(calibrator.predict_proba(pt.reshape(-1, 1))[:, 1], 1e-7, 1-1e-7)
    return out

def cluster_bootstrap(test, predictions, seed=42, repetitions=1000):
    rng = np.random.default_rng(seed + 17)
    subjects = np.asarray(sorted(test.subject_id.unique()))
    indices = {s: np.flatnonzero(test.subject_id.to_numpy() == s) for s in subjects}
    y = test.event_lt54.to_numpy()
    estimates = []
    diffs = []
    for _ in range(repetitions):
        sampled = rng.choice(subjects, size=len(subjects), replace=True)
        idx = np.concatenate([indices[s] for s in sampled])
        if len(np.unique(y[idx])) != 2:
            continue
        row = {"bootstrap": len(estimates)}
        for name, p in predictions.items():
            for k, v in scores(y[idx], p[idx]).items():
                row[f"{name}_{k}"] = v
        for k in METRICS:
            row[f"M2_minus_M0_{k}"] = row[f"M2_cgm_history_{k}"] - row[f"M0_current_glucose_{k}"]
            row[f"M2_minus_M1_{k}"] = row[f"M2_cgm_history_{k}"] - row[f"M1_glucose_slope_{k}"]
        estimates.append(row)
    if len(estimates) < 100:
        raise ValueError("Too few valid patient-clustered bootstrap resamples")
    return pd.DataFrame(estimates)

def calibration_summary(y, p):
    y = np.asarray(y, dtype=int)
    p = np.clip(np.asarray(p), 1e-6, 1-1e-6)
    # Calibration intercept and slope estimated jointly by logistic recalibration.
    logit = np.log(p/(1-p)).reshape(-1, 1)
    lr = LogisticRegression(penalty=None, max_iter=1000)
    lr.fit(logit, y)
    observed, predicted = calibration_curve(y, p, n_bins=10, strategy="quantile")
    return {"intercept": float(lr.intercept_[0]), "slope": float(lr.coef_[0,0]),
            "curve": [{"predicted": float(a), "observed": float(b)}
                      for a,b in zip(predicted, observed)]}

def episodes_and_alerts(raw, test, predictions, threshold=0.10, horizon=60):
    """Observed low-glucose episode proxy; 30-min separation and 15-min gaps.

    Alerts are 30-min spaced windows. Alert matching is within next 60 min.
    These are sensor-level proxies, not adjudicated clinical events.
    """
    test = test.copy()
    for name, p in predictions.items():
        test[name] = p
    subjects = set(test.subject_id)
    summary = {"alert_threshold": threshold, "horizon_minutes": horizon,
               "episode_definition": "start of consecutive CGM <54 mg/dL samples, with new episode after >=30 minutes above threshold or gap >15 minutes",
               "models": {}}
    # Build episode starts from original readings; no subject IDs in outputs.
    event_times = {}
    for sid, grp in raw[raw.subject_id.astype(str).isin(subjects)].groupby("subject_id"):
        grp = grp.sort_values("timestamp").drop_duplicates("timestamp")
        low = grp.glucose_mg_dl.to_numpy() < 54
        times = grp.timestamp.reset_index(drop=True)
        starts = []
        prev_low_time = None
        for t, islow in zip(times, low):
            if not islow:
                continue
            if prev_low_time is None or (t - prev_low_time).total_seconds() >= 30*60:
                starts.append(t)
            prev_low_time = t
        event_times[str(sid)] = starts
    summary["observed_episode_starts_all_test_subjects"] = int(sum(len(v) for v in event_times.values()))
    for name in predictions:
        matched = 0
        total_eligible = 0
        total_alerts = 0
        false_alerts = 0
        lead = []
        total_days = 0.0
        for sid, grp in test.groupby("subject_id"):
            grp = grp.sort_values("as_of")
            t = grp.as_of.reset_index(drop=True)
            alert_t = [time for time, p in zip(t, grp[name]) if p >= threshold]
            events = event_times.get(str(sid), [])
            total_alerts += len(alert_t)
            # Label a false alert when no observed episode onset in next horizon.
            for at in alert_t:
                if not any(at < ev <= at + pd.Timedelta(minutes=horizon) for ev in events):
                    false_alerts += 1
            first, last = t.iloc[0], t.iloc[-1]
            total_days += max(0, (last-first).total_seconds()/86400)
            for ev in events:
                if not (first < ev <= last + pd.Timedelta(minutes=horizon)):
                    continue
                total_eligible += 1
                eligible_alerts = [at for at in alert_t if at < ev <= at + pd.Timedelta(minutes=horizon)]
                if eligible_alerts:
                    matched += 1
                    lead.append((ev-min(eligible_alerts)).total_seconds()/60)
        summary["models"][name] = {
            "eligible_episode_starts": total_eligible,
            "detected_episode_starts": matched,
            "episode_sensitivity": matched/total_eligible if total_eligible else None,
            "alert_windows": total_alerts,
            "false_alert_windows": false_alerts,
            "false_alert_windows_per_observed_day": false_alerts/total_days if total_days else None,
            "median_warning_minutes": float(np.median(lead)) if lead else None,
            "observed_test_days": total_days,
            "caveat": "Overlapping windows, 30-minute alert cadence; this is NOT an alarm policy or clinically adjudicated event analysis.",
        }
    return summary

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument("--out", default="benchmark_results/expanded")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--bootstrap", type=int, default=1000)
    p.add_argument("--alert-threshold", type=float, default=0.10)
    a = p.parse_args()
    if not 0 < a.alert_threshold < 1:
        raise ValueError("Alert threshold must lie between 0 and 1")
    path = Path(a.csv)
    raw = pd.read_csv(path)
    raw["timestamp"] = pd.to_datetime(raw.timestamp, utc=True, errors="coerce")
    raw["glucose_mg_dl"] = pd.to_numeric(raw.glucose_mg_dl, errors="coerce")
    raw["subject_id"] = raw.subject_id.astype(str)
    raw = raw.dropna(subset=["timestamp","glucose_mg_dl"])
    examples = make_examples(raw)
    if examples.empty:
        raise ValueError("No eligible prediction windows")
    train, cal, test = tuple(cohort_split(examples, seed=a.seed))
    splits = {"source_subjects": int(raw.subject_id.nunique()),
              "eligible_subjects": int(examples.subject_id.nunique()),
              "eligible_windows": int(len(examples)),
              "eligible_positive_windows": int(examples.event_lt54.sum()),
              "splits": {}}
    for name, df in (("train", train), ("calibration", cal), ("test", test)):
        if df.event_lt54.nunique() < 2:
            raise ValueError(f"{name} lacks both event classes")
        splits["splits"][name] = {
            "patients": int(df.subject_id.nunique()),
            "windows": int(len(df)),
            "positive_windows": int(df.event_lt54.sum()),
            "patients_with_positive_windows": int(df.loc[df.event_lt54 == 1, "subject_id"].nunique()),
            "prevalence": float(df.event_lt54.mean()),
        }
    predictions = fit_models(train, cal, test, a.seed)
    y = test.event_lt54.to_numpy()
    rows = [{"model": name, **scores(y, prob), **{k:v for k,v in calibration_summary(y, prob).items() if k != "curve"}}
            for name, prob in predictions.items()]
    boot = cluster_bootstrap(test, predictions, seed=a.seed, repetitions=a.bootstrap)
    intervals = []
    for col in boot.columns:
        if col == "bootstrap":
            continue
        intervals.append({"statistic": col, "ci_low_2_5": float(boot[col].quantile(.025)),
                          "ci_high_97_5": float(boot[col].quantile(.975)),
                          "valid_resamples": len(boot)})
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out/"metrics_with_calibration.csv", index=False)
    pd.DataFrame(intervals).to_csv(out/"cluster_bootstrap_intervals.csv", index=False)
    curves = {name: calibration_summary(y, prob)["curve"] for name, prob in predictions.items()}
    (out/"calibration_curves.json").write_text(json.dumps(curves, indent=2))
    alerts = episodes_and_alerts(raw, test, predictions, threshold=a.alert_threshold)
    (out/"event_alert_analysis.json").write_text(json.dumps(alerts, indent=2))
    provenance = {
        **splits,
        "source_csv_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "seed": a.seed, "bootstrap_requested": a.bootstrap,
        "bootstrap_valid": len(boot), "bootstrap_unit": "patient",
        "test_grouping": "disjoint patients; 60/20/20",
        "horizon_minutes": 60, "history_minutes": 60, "stride_minutes": 30,
        "warning": "Research-only retrospective validation, not external validation or medical advice."
    }
    (out/"eligibility_and_provenance.json").write_text(json.dumps(provenance, indent=2))
    print(json.dumps(provenance, indent=2))
    print(pd.DataFrame(rows).to_string(index=False))
    print(json.dumps(alerts, indent=2))

if __name__ == "__main__":
    main()
