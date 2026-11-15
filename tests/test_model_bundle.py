import numpy as np
import pandas as pd
import pytest

from lbidsm.model_bundle import FrozenModel, predict, train_frozen
from lbidsm.prediction import cohort_split, make_examples
from lbidsm.synthetic_cohort import synthetic_cohort


@pytest.fixture(scope="module")
def splits():
    examples = make_examples(synthetic_cohort(n_subjects=40, days=14, seed=3))
    return tuple(cohort_split(examples))


def test_round_trip_and_same_predictions(splits):
    # REQ: L5-001
    train, cal, test = splits
    model = train_frozen(train, cal, "M2")
    again = FrozenModel.from_json(model.to_json())
    assert again.fingerprint() == model.fingerprint()
    assert np.allclose(predict(model, test), predict(again, test))
    p = predict(model, test)
    assert ((p > 0) & (p < 1)).all()


def test_tampered_file_is_rejected(splits):
    # REQ: L5-002
    import json
    train, cal, _ = splits
    d = json.loads(train_frozen(train, cal, "M1").to_json())
    d["platt_b"] = d["platt_b"] + 1.0
    with pytest.raises(ValueError, match="altered"):
        FrozenModel.from_json(json.dumps(d))


def test_changing_a_parameter_changes_fingerprint(splits):
    # REQ: L5-003
    train, cal, _ = splits
    model = train_frozen(train, cal, "M0")
    d = {**model.__dict__, "intercept": model.intercept + 0.01}
    assert FrozenModel(**d).fingerprint() != model.fingerprint()


def test_calibration_subjects_must_differ(splits):
    # REQ: L5-004
    train, _, _ = splits
    with pytest.raises(ValueError):
        train_frozen(train, train, "M0")


def test_m2_is_not_worse_than_m0_on_held_out_synthetic(splits):
    # REQ: L5-005
    from sklearn.metrics import roc_auc_score
    train, cal, test = splits
    y = test.event_lt54
    a0 = roc_auc_score(y, predict(train_frozen(train, cal, "M0"), test))
    a2 = roc_auc_score(y, predict(train_frozen(train, cal, "M2"), test))
    assert a2 >= a0 - 0.05
