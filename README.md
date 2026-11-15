# LBIDSM-DM — Layered Biological Intervention Decision Support for Diabetes

**Author:** Vikram Singh Sankhala · **Version:** 0.3.0 · **Status:** Computational research demonstrator (**not clinically validated**)

> **Medical safety:** This software is not a medical device. It must not be used to diagnose illness, estimate validated patient-specific risk, make medication adjustments, or handle emergencies. All bundled data are synthetic.

## Why this project exists

**A Proposed Mathematical and AI Architecture for Personalized Intervention Decision Support, for Diabetes** explores a progression from descriptive glucose thresholds to longitudinal signals, mathematical state estimation, calibrated prediction, causal treatment-effect evaluation and robust decision optimization. The repository deliberately keeps **working analytics** distinct from **future research modules**.

### Available now

- Reproducible synthetic, five-minute CGM readings.
- CSV upload, timestamp/unit validation, duplicate removal and sampling-gap exclusions.
- Time-weighted time-in-range, time-below-range, time-above-range, coefficient of variation and glucose summary metrics.
- Historical glucose velocity, rolling mean and dispersion.
- Interactive Plotly/Streamlit charts, descriptive threshold annotations and unit tests.
- Scientific manuscript in [paper/WHITE_PAPER.md](paper/WHITE_PAPER.md), with [implementation plan](docs/ARCHITECTURE.md), [data contract](docs/DATA_CONTRACT.md) and [validation protocol](docs/VALIDATION.md). Data sources and access status are in [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md). To run the research demo step by step, see the [demo user manual](docs/DEMO_USER_MANUAL.md). A synthetic teaching sample for lectures is in [data/sample/](data/sample/README.md).

### Research code, not validated

Research modules now exist for each area below, tested **on synthetic data only** (see [docs/RESEARCH_MODULES.md](docs/RESEARCH_MODULES.md)). None is clinically validated and none may be used for patient care.

| Area | Research code | Status |
|---|---|---|
| Clinical-grade data pipelines | `integrity.py` | Quality gate with written reasons; **not** a certified clinical pipeline |
| Trained hypoglycemia prediction | `prediction.py`, `model_bundle.py` | Baseline M0, M1, M2 and hash-locked model files; **not** clinically validated |
| External validation | `validation.py`, `scripts/external_cgmacros.py` | Gate and patient-clustered intervals built; **no cohort currently qualifies** (see the qualification report) |
| Patient-specific causal effects | `causal.py` | Single time-zero emulation; time-varying models still to do |
| Genetics | `genetics.py` | Mendelian randomisation on summary statistics; not run on real data |
| Optimized treatments | `utility.py` | Research ranking with explicit value weights; **never a prescription** |
| Personalized medical recommendations | `policy.py` | Routes to a human; executes nothing |
| Regulatory compliance | `evidence.py` | Evidence pack and release blockers; **not** regulatory clearance |
| Production access controls | `access.py` | Reference design and test bed; **not** a deployed or audited system |


## Research papers (two distinct manuscripts)

1. **Computational architecture white paper:** [A Proposed Mathematical and AI Architecture for Personalized Intervention Decision Support, for Diabetes](paper/WHITE_PAPER.md). Mathematical and engineering specification.
2. **Companion conceptual white paper (author-supplied):** [From Glucose Thresholds to Intervention Intelligence](paper/FROM_GLUCOSE_THRESHOLDS_TO_INTERVENTION_INTELLIGENCE.md). Six-page original manuscript transcribed into readable Markdown, including its clinical foundations, eight-layer architecture, decision policy and validation roadmap. The original PDF can be added as a binary asset separately.

Both are **proposed research manuscripts**, not peer-reviewed or clinically validated studies. They are preserved separately, not merged or substituted.

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
src/lbidsm/prediction.py     Leakage-aware windows and M0, M1, M2 baselines
src/lbidsm/integrity.py      L0 data-quality audit and gate
src/lbidsm/model_bundle.py   Frozen, fingerprinted model files
src/lbidsm/validation.py     Cohort qualification gate, clustered intervals
src/lbidsm/causal.py         Target-trial emulation, weighting, E-value
src/lbidsm/genetics.py       Mendelian randomisation from summary statistics
src/lbidsm/utility.py        Net utility and robust ranking of options
src/lbidsm/policy.py         L7 decision policy (five governed outputs)
src/lbidsm/evidence.py       Regulatory evidence pack and release blockers
src/lbidsm/access.py         Roles, audit chain, small-cell suppression
src/lbidsm/requirements.py   Requirement register traced to tests
scripts/                     Benchmarks, demo and patient-data guard
tests/                      Automated unit tests
paper/WHITE_PAPER.md        Authored computational white paper
docs/                       Architecture, data contract and validation plan
.github/workflows/ci.yml    Python tests on GitHub Actions
```

## Reproducibility and limits

The simulated CGM series is not a physiologically validated glucose–insulin model. Metrics integrate across valid adjacent intervals no longer than 15 minutes and do **not** establish sensor wear-time adequacy. The research hypotheses require preregistered experiments, patient-level held-out validation, appropriate causal methods and prospective clinical assessment.

**Citation:** Sankhala, V. S. (2026). *A proposed mathematical and AI architecture for personalized intervention decision support, for diabetes* (research white paper, version 2.0). Project repository.

**License:** MIT for software; scholarly citation is requested for the separately authored research text. No clinical warranty is provided.
