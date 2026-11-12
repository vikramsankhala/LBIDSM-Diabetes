# Public-data benchmark: protocol and verification

**Status (13 November 2026):** Implementation of a reproducible *benchmark pipeline*; **no public cohort has yet been downloaded, run, or independently validated in this repository**. Do not report performance metrics until the source is acquired and the exact experiment is executed.

## Primary source: ShanghaiT2DM

- Dataset publication: Zhao et al., *Chinese diabetes datasets for data-driven machine learning*, Scientific Data (2023), https://www.nature.com/articles/s41597-023-01940-7
- Public dataset collection: https://doi.org/10.6084/m9.figshare.c.6310860
- Study: 100 people with type 2 diabetes, 3–14 days of CGM recordings plus clinical, laboratory, medication and dietary records.
- **Important:** ShanghaiT2DM uses approximately 15-minute CGM sampling, not the 5-minute synthetic example. This pipeline works with irregular/15-minute data but requires no gap >16 minutes. Source files may need harmonization from XLS/XLSX to the required CSV; do not relabel T1DM subjects as T2DM.
- Dataset rights and terms must be checked at the publisher before redistributing files. Do not commit participant-level data to GitHub.

Other reproducibility resources: [Glucose-ML-Project](https://github.com/Augmented-Health-Lab/Glucose-ML-Project) (public-data acquisition and harmonization), and [GlucoBench](https://github.com/cblk/GlucoBench). These are independent projects; verify their preprocessing, patient IDs and licensing before use.

## Required harmonized CSV

```csv
subject_id,timestamp,glucose_mg_dl
T2_001,2026-01-01T00:00:00+08:00,128
T2_001,2026-01-01T00:15:00+08:00,131
T2_001,2026-01-01T00:30:00+08:00,133
```

The above is **format illustration only**, not real patient data. Preserve original patient IDs and source timestamps. If the raw data are in mmol/L, convert with a documented factor (typically ×18.0182), preserve source units in a separate manifest, and confirm units from the data dictionary.

## Execution

```bash
python -m pip install -e '.[benchmark]'
python scripts/run_public_benchmark.py --csv /path/to/shanghai_t2dm_harmonized.csv --dataset-name ShanghaiT2DM --source-url https://doi.org/10.6084/m9.figshare.c.6310860 --out benchmark_results/shanghai_t2dm
```

Outputs: `metrics.csv` and `provenance.json` (including SHA-256, sample counts, patient counts, event prevalence, random seed). Do not commit outputs with patient-level records.

## Predeclared outcome and model comparators

- **Primary target:** at least one observed CGM sample <54 mg/dL in the following 60 minutes. This is a *sample-level surrogate*, not an adjudicated event and is especially sensitive to sampling frequency.
- **History:** previous 60 minutes; no future values in features. Use contiguous windows only, discard gaps >16 minutes; stride 30 minutes.
- **M0:** last glucose.
- **M1:** last glucose and recent 15-minute slope.
- **M2:** conventional CGM summary (60-minute mean, SD, min, max, slope, circadian features).
- **Model:** standardized logistic regression; separate patient-held-out calibration (Platt scaling); no hyperparameter selection on test.
- **Split:** disjoint subjects, 60% training / 20% calibration / 20% locked test; seed 42.
- **Metrics:** AUROC, AUPRC, Brier score, log loss, event count, sample prevalence.
- **Failure gate:** abort when any split has only one outcome class. Do not substitute fabricated values.

## Limitations and next research gate

The dataset has a limited cohort and potentially few level 2 events; prevalence must be checked before any claims. Overlapping outcome windows are correlated; patient-clustered bootstrap confidence intervals and event-level alert burden are needed before publishable estimates. The benchmark is **retrospective internal holdout**, not external validation. External validation requires a separate eligible cohort with the same endpoint and sensor assumptions. The feature set does not include medication, comorbidities, genetic information or mechanistic state estimation.

The program will only write metrics when the user provides the source CSV; there are no invented results.
