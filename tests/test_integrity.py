import numpy as np
import pandas as pd

from lbidsm.integrity import QualityPolicy, apply_gate, audit_cohort, audit_subject, sha256_file
from lbidsm.synthetic_cohort import synthetic_cohort


def clean(n=600):
    return pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=n, freq="5min", tz="UTC"),
        "glucose_mg_dl": 120 + 25 * np.sin(np.arange(n) / 20) + np.random.default_rng(1).normal(0, 2, n),
    })


def test_clean_record_passes():
    # REQ: L0-001
    report = audit_subject(clean(), "a")
    assert report.passed, report.reasons
    assert report.metrics["coverage"] > 0.99


def test_large_gaps_fail():
    # REQ: L0-002
    df = clean()
    df = pd.concat([df.iloc[:100], df.iloc[300:]])
    report = audit_subject(df, "gap", QualityPolicy(min_coverage=0.9))
    assert not report.passed
    assert any("coverage" in r for r in report.reasons)


def test_stuck_sensor_fails():
    # REQ: L0-003
    df = clean()
    df.loc[200:215, "glucose_mg_dl"] = 100.0
    assert any("identical" in r for r in audit_subject(df, "flat").reasons)


def test_out_of_range_and_duplicates_are_counted_not_hidden():
    # REQ: L0-004
    df = clean()
    df.loc[5:30, "glucose_mg_dl"] = 9999
    df = pd.concat([df, df.iloc[40:60]])
    report = audit_subject(df, "bad")
    assert report.metrics["out_of_range_rows"] == 26
    assert report.metrics["duplicate_timestamps"] == 20
    assert not report.passed


def test_gate_drops_failed_subjects_only():
    # REQ: L0-005
    cohort = synthetic_cohort(n_subjects=6, days=3)
    bad = cohort.subject_id == "S002"
    cohort.loc[bad & (cohort.index % 3 != 0), "glucose_mg_dl"] = np.nan
    reports = audit_cohort(cohort)
    kept = apply_gate(cohort, reports)
    assert "S002" not in set(kept.subject_id)
    assert set(kept.subject_id) == {r.subject_id for r in reports if r.passed}


def test_file_fingerprint_changes_with_content(tmp_path):
    # REQ: L0-006
    p = tmp_path / "x.csv"
    p.write_text("a,b\n1,2\n")
    first = sha256_file(p)
    p.write_text("a,b\n1,3\n")
    assert first != sha256_file(p)
