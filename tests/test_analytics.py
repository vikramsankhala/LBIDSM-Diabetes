import pandas as pd
import pytest
from lbidsm.analytics import metrics, validate_cgm
from lbidsm.rules import observations
from lbidsm.simulation import synthetic_cgm

def test_synthetic_metrics():
    m = metrics(synthetic_cgm(days=1))
    assert 0 <= m["tir_70_180_percent"] <= 100
    assert m["observed_hours"] > 23

def test_missing_columns():
    with pytest.raises(ValueError):
        validate_cgm(pd.DataFrame({"foo": [1]}))

def test_low_glucose_annotation():
    assert "level 2" in observations(50)[0]

def test_gap_exclusion():
    d = pd.DataFrame({
        "timestamp": ["2026-01-01T00:00:00Z", "2026-01-01T00:05:00Z", "2026-01-01T03:00:00Z"],
        "glucose_mg_dl": [100, 110, 120],
    })
    assert metrics(d)["observed_hours"] == 0.08
