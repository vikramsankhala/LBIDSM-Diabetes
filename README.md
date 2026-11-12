# LBIDSM-DM — Layered Biological Intervention Decision Support for Diabetes

**Author:** Vikram Singh Sankhala · **Version:** 0.1.0 · **Status:** Computational research demonstrator (**not clinically validated**)

> **Medical safety:** This software is not a medical device. It must not be used to diagnose illness, estimate validated patient-specific risk, make medication adjustments, or handle emergencies. All bundled data are synthetic.

## Why this project exists

**A Proposed Mathematical and AI Architecture for Personalized Intervention Decision Support, for Diabetes** explores a progression from descriptive glucose thresholds to longitudinal signals, mathematical state estimation, calibrated prediction, causal treatment-effect evaluation and robust decision optimization. The repository deliberately keeps **working analytics** distinct from **future research modules**.

### Available now

- Reproducible synthetic, five-minute CGM readings.
- CSV upload, timestamp/unit validation, duplicate removal and sampling-gap exclusions.
- Time-weighted time-in-range, time-below-range, time-above-range, coefficient of variation and glucose summary metrics.
- Historical glucose velocity, rolling mean and dispersion.
- Interactive Plotly/Streamlit charts, descriptive threshold annotations and unit tests.
- Scientific manuscript in [paper/WHITE_PAPER.md](paper/WHITE_PAPER.md), with [implementation plan](docs/ARCHITECTURE.md), [data contract](docs/DATA_CONTRACT.md) and [validation protocol](docs/VALIDATION.md).

### Not implemented / not validated

Trained hypoglycemia prediction, patient-specific causal effects, genetics, personalized medical recommendations, optimized treatments, clinical-grade data pipelines, external validation, regulatory compliance and production access controls. These are **research specifications only**.

## Getting started

Requires Python 3.10–3.13.

```bash
git clone https://github.com/vikramsankhala/LBIDSM-Diabetes.git
cd LBIDSM-Diabetes
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[dev]"
streamlit run app.py
```

Run tests: `python -m pytest -q`.

## Data format

```csv
timestamp,glucose_mg_dl
2026-01-01T00:00:00Z,121
2026-01-01T00:05:00Z,124
2026-01-01T00:10:00Z,128
```

Use only synthetic or appropriately consented, de-identified research data. Public deployments and uploaded health data require separate privacy and security review.

## Project layout

```text
app.py                       Research dashboard
src/lbidsm/analytics.py      CGM validation, time-weighted metrics and trends
src/lbidsm/simulation.py     Reproducible synthetic examples
src/lbidsm/rules.py          Descriptive annotations (not treatment rules)
tests/                      Automated unit tests
paper/WHITE_PAPER.md        Authored computational white paper
docs/                       Architecture, data contract and validation plan
.github/workflows/ci.yml    Python tests on GitHub Actions
```

## Reproducibility and limits

The simulated CGM series is not a physiologically validated glucose–insulin model. Metrics integrate across valid adjacent intervals no longer than 15 minutes and do **not** establish sensor wear-time adequacy. The research hypotheses require preregistered experiments, patient-level held-out validation, appropriate causal methods and prospective clinical assessment.

**Citation:** Sankhala, V. S. (2026). *A proposed mathematical and AI architecture for personalized intervention decision support, for diabetes* (research white paper, version 2.0). Project repository.

**License:** MIT for software; scholarly citation is requested for the separately authored research text. No clinical warranty is provided.
