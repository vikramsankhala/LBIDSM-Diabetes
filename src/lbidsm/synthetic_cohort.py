"""Synthetic multi-subject CGM cohort for tests and demos. Not physiological."""
import numpy as np
import pandas as pd


def synthetic_cohort(n_subjects=30, days=14, seed=42, dip_rate_per_day=0.35):
    """Five-minute CGM for several subjects, with occasional deep dips below 54 mg/dL.

    Every subject has its own baseline so events cluster in some people, as in
    real cohorts. The dips are injected by construction; this is a test fixture,
    not a model of glucose physiology.
    """
    rng = np.random.default_rng(seed)
    n = days * 288
    t = np.arange(n)
    frames = []
    for s in range(n_subjects):
        baseline = rng.normal(118, 14)
        phase = rng.uniform(0, 2 * np.pi)
        noise = np.zeros(n)
        for i in range(1, n):
            noise[i] = 0.85 * noise[i - 1] + rng.normal(0, 4.5)
        meals = sum(28 * np.exp(-0.5 * ((t % 288 - k) / 10) ** 2) for k in (90, 160, 230))
        g = baseline + 16 * np.sin(2 * np.pi * t / 288 + phase) + meals + noise
        n_dips = rng.poisson(dip_rate_per_day * days * rng.uniform(0.3, 2.0))
        for start in rng.integers(40, n - 40, size=n_dips):
            depth = rng.uniform(35, 52)
            width = int(rng.integers(3, 8))
            ramp = np.concatenate([np.linspace(0, 1, 6), np.ones(width), np.linspace(1, 0, 6)])
            end = min(n, start + len(ramp))
            g[start:end] = (g[start:end] * (1 - ramp[: end - start]) + depth * ramp[: end - start]
                            + rng.normal(0, 1.5, end - start))   # sensor noise: real traces are never flat
        g = np.clip(g, 30, 400)
        frames.append(pd.DataFrame({
            "subject_id": f"S{s:03d}",
            "timestamp": pd.date_range("2026-01-01", periods=n, freq="5min", tz="UTC"),
            "glucose_mg_dl": g,
        }))
    return pd.concat(frames, ignore_index=True)
