"""L0 data integrity: audit CGM data before any modelling. Research use only.

`analytics.validate_cgm` quietly drops bad rows. This module does the opposite:
it counts what was wrong, applies a written policy and returns pass or fail
with reasons, so a failed record is stopped instead of repaired.
The thresholds are placeholders. A real study must fix them in its protocol
and have them signed off before any outcome is examined.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class QualityPolicy:
    version: str = "l0-0.1-placeholder"
    min_glucose: float = 20.0          # same sanity range as analytics.validate_cgm
    max_glucose: float = 600.0
    nominal_minutes: float = 5.0
    max_gap_minutes: float = 15.0      # same limit as the data contract
    min_coverage: float = 0.70         # observed samples / expected samples
    max_gap_fraction: float = 0.10     # share of intervals longer than max_gap_minutes
    max_flat_run: int = 6              # identical consecutive values: stuck sensor or fill
    max_invalid_fraction: float = 0.02  # unparseable or out-of-range rows
    max_duplicate_fraction: float = 0.02


@dataclass
class QualityReport:
    subject_id: str
    passed: bool
    reasons: list = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    policy_version: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def sha256_file(path, chunk=1 << 20) -> str:
    """Fingerprint a raw input file so results can be tied to exact bytes."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def audit_subject(frame: pd.DataFrame, subject_id: str = "", policy: QualityPolicy = QualityPolicy()) -> QualityReport:
    """Audit one subject's readings (columns: timestamp, glucose_mg_dl)."""
    raw_n = len(frame)
    ts = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    g = pd.to_numeric(frame["glucose_mg_dl"], errors="coerce")
    unparsable = int((ts.isna() | g.isna()).sum())
    d = pd.DataFrame({"t": ts, "g": g}).dropna()
    out_of_range = int((~d.g.between(policy.min_glucose, policy.max_glucose)).sum())
    d = d[d.g.between(policy.min_glucose, policy.max_glucose)]
    out_of_order = int((d.t.diff().dt.total_seconds() < 0).sum())
    d = d.sort_values("t")
    duplicates = int(d.t.duplicated().sum())
    d = d.drop_duplicates("t")

    metrics = {"raw_rows": raw_n, "valid_rows": len(d), "unparsable_rows": unparsable,
               "out_of_range_rows": out_of_range, "duplicate_timestamps": duplicates,
               "out_of_order_rows": out_of_order}
    reasons = []
    if len(d) < 2:
        reasons.append("fewer than two valid readings")
        return QualityReport(str(subject_id), False, reasons, metrics, policy.version)

    minutes = d.t.diff().dt.total_seconds().to_numpy()[1:] / 60
    span = float((d.t.iloc[-1] - d.t.iloc[0]).total_seconds() / 60)
    expected = span / policy.nominal_minutes + 1
    flat = d.g.diff().fillna(1).ne(0).cumsum()
    longest_flat = int(d.groupby(flat).size().max())
    metrics.update({
        "median_interval_minutes": round(float(np.median(minutes)), 2),
        "coverage": round(len(d) / expected, 3),
        "gap_fraction": round(float((minutes > policy.max_gap_minutes).mean()), 3),
        "longest_gap_minutes": round(float(minutes.max()), 1),
        "longest_flat_run": longest_flat,
        "observed_days": round(span / 1440, 2),
    })

    if (out_of_range + unparsable) / max(raw_n, 1) > policy.max_invalid_fraction:
        reasons.append("too many unparsable or out-of-range rows")
    if duplicates / max(raw_n, 1) > policy.max_duplicate_fraction:
        reasons.append("too many duplicate timestamps")
    if out_of_order:
        reasons.append("timestamps not in time order in the source")
    if abs(metrics["median_interval_minutes"] - policy.nominal_minutes) > 0.5:
        reasons.append(f"median interval {metrics['median_interval_minutes']} min is not the nominal {policy.nominal_minutes} min")
    if metrics["coverage"] < policy.min_coverage:
        reasons.append("coverage below policy")
    if metrics["gap_fraction"] > policy.max_gap_fraction:
        reasons.append("too many gaps longer than the allowed maximum")
    if longest_flat > policy.max_flat_run:
        reasons.append("long run of identical values (stuck sensor or filled data)")
    return QualityReport(str(subject_id), not reasons, reasons, metrics, policy.version)


def audit_cohort(df: pd.DataFrame, policy: QualityPolicy = QualityPolicy()) -> list[QualityReport]:
    """Audit every subject (columns: subject_id, timestamp, glucose_mg_dl)."""
    if not {"subject_id", "timestamp", "glucose_mg_dl"}.issubset(df.columns):
        raise ValueError("Need columns subject_id, timestamp, glucose_mg_dl")
    return [audit_subject(g, sid, policy) for sid, g in df.groupby("subject_id", sort=True)]


def apply_gate(df: pd.DataFrame, reports: list[QualityReport]) -> pd.DataFrame:
    """Keep only subjects that passed. Failed subjects are reported, never repaired."""
    keep = {r.subject_id for r in reports if r.passed}
    return df[df.subject_id.astype(str).isin(keep)].copy()


def summarise(reports: list[QualityReport]) -> pd.DataFrame:
    rows = [{"subject_id": r.subject_id, "passed": r.passed, "reasons": "; ".join(r.reasons), **r.metrics}
            for r in reports]
    return pd.DataFrame(rows)
