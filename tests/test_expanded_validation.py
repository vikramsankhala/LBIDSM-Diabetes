import numpy as np
import pandas as pd
from scripts.expanded_validation import scores, calibration_summary, cluster_bootstrap

def test_scores_perfect():
    result = scores([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9])
    assert result["auroc"] == 1.0
    assert result["auprc"] == 1.0

def test_calibration_curve():
    y = [0, 0, 0, 1, 1, 1]
    p = [0.1, 0.2, 0.3, 0.7, 0.8, 0.9]
    c = calibration_summary(y, p)
    assert np.isfinite(c["slope"])
    assert len(c["curve"]) > 0

def test_patient_cluster_bootstrap():
    ids = np.repeat([str(i) for i in range(20)], 10)
    y = np.tile([0,0,0,0,0,1,1,1,1,1], 20)
    frame = pd.DataFrame({"subject_id": ids, "event_lt54": y})
    p = np.where(y == 1, 0.8, 0.2)
    result = cluster_bootstrap(frame, {k: p for k in ("M0_current_glucose","M1_glucose_slope","M2_cgm_history")}, repetitions=110)
    assert len(result) == 110
    assert np.allclose(result["M2_minus_M0_auroc"], 0)
