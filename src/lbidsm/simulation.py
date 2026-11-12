"""Synthetic data only. Not a validated glucose-insulin physiological simulator."""
import numpy as np
import pandas as pd

def synthetic_cgm(days=14, seed=42):
    rng = np.random.default_rng(seed)
    n = days * 288
    t = np.arange(n)
    circadian = 19 * np.sin(2 * np.pi * t / 288 - 1)
    meals = sum(35 * np.exp(-0.5 * ((t % 288 - k) / 11) ** 2) for k in [90, 155, 230])
    noise = np.zeros(n)
    for i in range(1, n):
        noise[i] = 0.88 * noise[i - 1] + rng.normal(0, 5)
    g = np.clip(130 + circadian + meals + noise, 45, 350)
    return pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=n, freq="5min", tz="UTC"),
        "glucose_mg_dl": g,
    })
