# Expanded ShanghaiT2DM validation — prespecified report

**Status:** Pipeline implemented; numerical expanded-validation findings must be taken from a completed GitHub Actions run. No unexecuted numbers should be presented as findings.

The existing held-out benchmark is a first step, not a demonstration of clinical utility or independent external validation.

## Exact cohort eligibility
Report source subjects, eligible subjects with 60-minute observed histories and future 60-minute labels, windows per split, positive windows and number of patients with positive windows. Patient identities remain private. Patient-disjoint 60/20/20 split, seed 42.

## Hypoglycemia episode distribution
A positive prediction window is not a distinct episode. The added event analysis counts observed CGM readings <54 mg/dL and groups low readings into episode starts using a 30-minute separation. The episode algorithm is a **proxy**, not an adjudicated clinical episode definition. Report test-cohort episode starts and eligible event starts, plus detection counts. Because episodes can occur outside evaluated windows, the total and eligible counts may differ.

## Probability calibration
For M0 current glucose, M1 glucose plus slope, and M2 CGM history, compute Brier score, log loss, calibration intercept and slope, and ten quantile-binned observed-versus-predicted rates. Calibration regression on test is descriptive only and must not be used to re-fit predictions.

## Uncertainty
Use 1,000 patient-clustered bootstrap resamples from the held-out test cohort. Report percentile 95% intervals for AUROC, AUPRC, Brier, log loss and paired M2−M0/M2−M1 differences. These intervals address sampling variability conditional on this cohort, not cross-site transportability. The resampling unit is the patient, not overlapping windows.

## Alert evaluation
At a **research-only threshold** of 0.10, report number of alert windows, observed episode starts matched by alerts in the previous 60 minutes, eligible episode sensitivity, false-alert windows per observed day and median lead time. This is not a deployed alarm policy. Alert windows are 30 minutes apart; false-alert windows are not deduplicated into independent alarm episodes.

## Acceptance gates and limitations
Require valid cohort splits, nondegenerate outcomes in each split, source checksum, auditable results, clinically reviewed event definition and confidence intervals. Before claiming comparative superiority, check paired intervals, prevalence, event clustering, and calibration. A second independent cohort is required for external validation. No drug or treatment recommendations are authorized.

Run locally after original source acquisition:

```bash
python -m pip install -e '.[benchmark]'
python scripts/expanded_validation.py --csv benchmark_results/source/shanghai_t2dm_harmonized.csv --out benchmark_results/expanded --bootstrap 1000
```
