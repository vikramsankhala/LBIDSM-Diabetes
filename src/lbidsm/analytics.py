"""CGM research analytics. Not for clinical decision-making."""
import numpy as np
import pandas as pd

def validate_cgm(df: pd.DataFrame) -> pd.DataFrame:
    required = {"timestamp", "glucose_mg_dl"}
    if not required.issubset(df.columns):
        raise ValueError(f"Missing columns: {required - set(df.columns)}")
    out = df[["timestamp", "glucose_mg_dl"]].copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out["glucose_mg_dl"] = pd.to_numeric(out["glucose_mg_dl"], errors="coerce")
    out = out.dropna().sort_values("timestamp").drop_duplicates("timestamp")
    out = out[out.glucose_mg_dl.between(20, 600)]
    if len(out) < 2:
        raise ValueError("At least two valid CGM readings required")
    return out.reset_index(drop=True)

def metrics(df: pd.DataFrame, max_gap_minutes: float = 15.0) -> dict:
    """Time-weighted summary over intervals no longer than max_gap_minutes."""
    df = validate_cgm(df)
    g = df.glucose_mg_dl.to_numpy()
    minutes = df.timestamp.diff().dt.total_seconds().shift(-1).to_numpy() / 60
    valid = np.isfinite(minutes) & (minutes > 0) & (minutes <= max_gap_minutes)
    weights = np.where(valid, minutes, 0)
    if weights.sum() <= 0:
        raise ValueError("No usable intervals: inspect sampling gaps")
    def pct(mask):
        return float(100 * np.sum(weights * mask) / weights.sum())
    mean = float(np.average(g, weights=weights))
    sd = float(np.sqrt(np.average((g - mean) ** 2, weights=weights)))
    return {
        "mean_mg_dl": round(mean, 2),
        "cv_percent": round(100 * sd / mean, 2),
        "tir_70_180_percent": round(pct((g >= 70) & (g <= 180)), 2),
        "tbr_70_percent": round(pct(g < 70), 2),
        "tbr_54_percent": round(pct(g < 54), 2),
        "tar_180_percent": round(pct(g > 180), 2),
        "tar_250_percent": round(pct(g > 250), 2),
        "observed_hours": round(float(weights.sum() / 60), 2),
        "n_samples": len(df),
    }

def features(df: pd.DataFrame) -> pd.DataFrame:
    df = validate_cgm(df)
    elapsed = df.timestamp.diff().dt.total_seconds() / 60
    df["velocity_mg_dl_min"] = df.glucose_mg_dl.diff() / elapsed.where(elapsed.between(1, 15))
    df["rolling_mean_12"] = df.glucose_mg_dl.rolling(12, min_periods=6).mean()
    df["rolling_sd_12"] = df.glucose_mg_dl.rolling(12, min_periods=6).std()
    return df
