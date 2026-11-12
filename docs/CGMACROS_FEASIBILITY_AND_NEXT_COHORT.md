# CGMacros external-validation feasibility result and next-cohort protocol

**Study classification:** Successful independent-cohort *pipeline feasibility* experiment; **statistically insufficient hypoglycemia events for reliable external validation of predictive performance**.

**Execution:** [GitHub Actions run 43332132292](https://github.com/vikramsankhala/LBIDSM-Diabetes/actions/runs/43332132292), successful. [Aggregate audit artifact 13995935633](https://github.com/vikramsankhala/LBIDSM-Diabetes/actions/runs/43332132292/artifacts/13995935633). Automated tests: [run 43332170100](https://github.com/vikramsankhala/LBIDSM-Diabetes/actions/runs/43332170100), successful.

## Verified observations

- External dataset: CGMacros v1.0.0, PhysioNet, DOI 10.13026/3z8q-x658; official archive SHA-256 `05c8b0e6f1a2757050aced55ce4bf6ab2ac9b30f2fd8ca193056812d9c621d4d`.
- Eligible T2D-group subjects: **14**; CGM prediction windows: **6,594**; positive windows: **7** (approximately **0.106%**); patients contributing positive windows: **2**.
- The cohort was selected by the source study's HbA1c >6.4% proxy; this is not independently adjudicated diabetes diagnosis.
- The target is any observed glucose reading <54 mg/dL in the next 60 minutes, a *sample-level surrogate*. Seven positive windows are **not** seven independent hypoglycemia episodes.
- Frozen ShanghaiT2DM training: 60 subjects, with a separate 20-subject calibration set; no external CGMacros outcomes used for training or recalibration.

| Model | AUROC | AUPRC | Brier | Log loss | Calibration intercept | Calibration slope |
|---|---:|---:|---:|---:|---:|---:|
| M0 current glucose | 0.972478 | 0.394083 | 0.000849 | 0.007144 | 18.192523 | 4.310429 |
| M1 glucose + slope | 0.963228 | 0.401728 | 0.000766 | 0.006708 | 4.743616 | 2.021537 |
| M2 CGM history | 0.977900 | 0.410379 | 0.000769 | 0.006580 | -0.177015 | 1.168996 |

These are **descriptive point estimates only**, not evidence of comparative superiority. With just two event-positive participants, patient-clustered uncertainty may be very large or unstable; consult the artifact for bootstrap intervals and event-level analysis. The 1-minute CGMacros tables contain interpolated values, and nominal 5-minute subsampling has not been demonstrated to recover original device-native timestamps or sensor samples.

## Formal conclusion

**The independent CGMacros workflow executed successfully and demonstrated reproducible cohort acquisition, harmonization, locked-model inference and aggregate metric generation. However, only seven positive prediction windows across two patients were observed. This is statistically insufficient to establish reliable external hypoglycemia-prediction performance, comparative model superiority, calibration, event-level sensitivity or clinical utility. The study is therefore classified as an external-validation feasibility experiment, not a successful predictive external validation.**

## Next research priority: larger independent T2D CGM cohort

**Do not change the <54 mg/dL / 60-minute endpoint post hoc to obtain a favorable result.** Identify a distinct cohort with a larger number of *independent observed level-2 hypoglycemia episodes* and a meaningful number of event-positive participants. Prefer raw, native sensor readings over interpolated or resampled tables.

### Prespecified acquisition and sensor-integrity audit

1. Record dataset owner, access terms, study design, participant selection, diabetes type, therapy distribution, sensor make/model, sampling cadence, dates and cohort independence from ShanghaiT2DM and CGMacros.
2. Verify download URL, source version, checksums and licensing; preserve a machine-readable acquisition manifest. Do not publish participant-level records.
3. Inspect device-native timestamps and measurements: timezone and daylight-saving handling, clock drift, duplicates, nonmonotonic timestamps, gaps, impossible values, device warmup, calibration, censoring, interpolation and imputation. Retain flags for raw versus derived readings.
4. Define episode onset, termination and minimum separation *before inspecting model performance*; distinguish <54 mg/dL sample labels, episodes, patients with episodes, and time under threshold. Consider sensitivity analysis requiring sustained low readings.
5. Produce a blinded feasibility count: eligible participants, person-days, native CGM readings, independent episodes, episode-positive participants, and episode frequency by therapy subgroup. If sparse, report inconclusive feasibility and seek another cohort.
6. Freeze Shanghai-only model weights, preprocessing, calibration and thresholds; version all artifacts and ensure no subject overlap or data leakage. Apply without external-outcome tuning.
7. Evaluate AUROC, AUPRC versus event prevalence, Brier/log loss, calibration intercept/slope and reliability plots; report patient-clustered confidence intervals and paired differences.
8. Evaluate alert episodes (deduplicated), episode sensitivity, false alarms per patient-day, median lead time, and performance across patients, devices and relevant clinical subgroups. Include uncertainty and prespecified thresholds.
9. Document sample-size feasibility using *independent episode and event-positive patient counts*, not just overlapping prediction windows; involve clinical and biostatistical review before specifying a definitive validation sample size.
10. Publish an audit-ready scientific report with protocol deviations, limitations, negative findings and reproducibility instructions. No autonomous medical decision support or treatment recommendations.

**Gate:** No claim of external predictive validation until the new cohort has adequate independent events, verified native sensor provenance, stable patient-clustered uncertainty, and clinically interpretable episode-level results.
