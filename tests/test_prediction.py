import numpy as np
import pandas as pd
import pytest
from lbidsm.prediction import make_examples, cohort_split, benchmark

def mock_cohort(n=20, length=220):
    rows = []
    for sid in range(n):
        t = pd.date_range("2026-01-01", periods=length, freq="15min", tz="UTC")
        g = 90 + 42 * np.sin(np.arange(length) / 15 + sid * 0.5)
        rows.extend({"subject_id": str(sid), "timestamp": ts, "glucose_mg_dl": float(v)} for ts, v in zip(t, g))
    return pd.DataFrame(rows)

def test_future_leakage():
    data = mock_cohort(1, 40)
    examples = make_examples(data)
    assert not examples.empty
    earlier = examples.iloc[0]
    data.loc[data.timestamp > earlier.as_of, "glucose_mg_dl"] = 50
    changed = make_examples(data)
    same = changed.loc[changed.as_of == earlier.as_of].iloc[0]
    assert earlier.last_glucose == same.last_glucose
    assert earlier.mean_60 == same.mean_60
    assert same.event_lt54 == 1

def test_subject_disjointness():
    examples = make_examples(mock_cohort())
    tr, ca, te = tuple(cohort_split(examples))
    assert set(tr.subject_id).isdisjoint(ca.subject_id)
    assert set(tr.subject_id).isdisjoint(te.subject_id)
    assert set(ca.subject_id).isdisjoint(te.subject_id)

def test_benchmark_smoke():
    examples = make_examples(mock_cohort(30))
    scores, meta = benchmark(examples)
    assert len(scores) == 3
    assert scores.auroc.between(0, 1).all()
    assert meta["subjects"]["test"] == 6

def test_insufficient_subjects():
    with pytest.raises(ValueError):
        tuple(cohort_split(make_examples(mock_cohort(2))))
