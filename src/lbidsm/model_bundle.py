"""Frozen, auditable hypoglycaemia models (M0, M1, M2). Research use only.

Each model is a scaler, a logistic regression and a Platt calibrator. All three
are plain numbers, so a trained model is stored as JSON, not as a pickle.
A pickle can run code when loaded and cannot be read by a reviewer.
The fingerprint (SHA-256 of the parameters) is what "locked before unblinding"
means in practice: record it before any external data is opened, then check it.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from .prediction import FEATURES_BASIC, FEATURES_CGM

FEATURE_SETS = {"M0": ["last_glucose"], "M1": FEATURES_BASIC, "M2": FEATURES_CGM}
LABEL = "event_lt54"


@dataclass(frozen=True)
class FrozenModel:
    name: str
    features: tuple
    mean: tuple
    scale: tuple
    coef: tuple
    intercept: float
    platt_a: float
    platt_b: float
    event_definition: str
    trained_on: dict
    code_version: str = "lbidsm-0.3"

    def fingerprint(self) -> str:
        """SHA-256 over every parameter. Any retraining or tuning changes it."""
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_json(self) -> str:
        return json.dumps({**asdict(self), "fingerprint": self.fingerprint()}, indent=2, sort_keys=True)

    @staticmethod
    def from_json(text: str) -> "FrozenModel":
        d = json.loads(text)
        claimed = d.pop("fingerprint", None)
        for key in ("features", "mean", "scale", "coef"):
            d[key] = tuple(d[key])
        model = FrozenModel(**d)
        if claimed is not None and claimed != model.fingerprint():
            raise ValueError("Model file was altered: fingerprint does not match its parameters")
        return model


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -35, 35)))


def train_frozen(train: pd.DataFrame, calibration: pd.DataFrame, name: str = "M2", seed: int = 42) -> FrozenModel:
    """Fit on the training subjects, calibrate on separate subjects, then freeze."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    features = FEATURE_SETS[name]
    if set(train.subject_id) & set(calibration.subject_id):
        raise ValueError("Training and calibration subjects must be different people")
    for label, frame in (("train", train), ("calibration", calibration)):
        if frame[LABEL].nunique() != 2:
            raise ValueError(f"{label} data lack both outcome classes")
    scaler = StandardScaler().fit(train[features])
    clf = LogisticRegression(max_iter=1000, random_state=seed).fit(scaler.transform(train[features]), train[LABEL])
    raw = clf.predict_proba(scaler.transform(calibration[features]))[:, 1]
    platt = LogisticRegression(max_iter=1000, random_state=seed).fit(raw.reshape(-1, 1), calibration[LABEL])
    return FrozenModel(
        name=name, features=tuple(features),
        mean=tuple(map(float, scaler.mean_)), scale=tuple(map(float, scaler.scale_)),
        coef=tuple(map(float, clf.coef_[0])), intercept=float(clf.intercept_[0]),
        platt_a=float(platt.coef_[0, 0]), platt_b=float(platt.intercept_[0]),
        event_definition="any observed CGM sample <54 mg/dL within the next 60 minutes (surrogate)",
        trained_on={"train_subjects": int(train.subject_id.nunique()), "train_rows": len(train),
                    "train_events": int(train[LABEL].sum()),
                    "calibration_subjects": int(calibration.subject_id.nunique()), "seed": seed},
    )


def predict(model: FrozenModel, frame: pd.DataFrame) -> np.ndarray:
    """Calibrated probability of a level 2 low in the next 60 minutes. NumPy only."""
    x = (frame[list(model.features)].to_numpy(float) - np.array(model.mean)) / np.array(model.scale)
    raw = _sigmoid(x @ np.array(model.coef) + model.intercept)
    return np.clip(_sigmoid(model.platt_a * raw + model.platt_b), 1e-6, 1 - 1e-6)
