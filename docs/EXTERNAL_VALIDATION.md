# CGMacros independent external validation

**Scientific status:** Experimental workflow, not a verified external validation result.

Original open-access source: Gutierrez-Osuna et al. (2025), CGMacros v1.0.0, PhysioNet, https://doi.org/10.13026/3z8q-x658 . The dataset has 45 participants, of whom 14 meet the study's type 2 diabetes group definition. Dexcom G6 Pro records at nominal 5-minute intervals; Libre Pro records at 15-minute intervals. The distributed 1-minute tables include interpolation and dates shifted for privacy. Files are CC BY-NC-SA 4.0; do not redistribute patient-level files or use commercially without permission.

## Locked transfer protocol

1. Download ShanghaiT2DM and construct 60-minute historical CGM features; fit M0, M1 and M2 on Shanghai training subjects; Platt calibrate using Shanghai calibration subjects.
2. Download original CGMacros ZIP and verify SHA-256 against the publisher's SHA256SUMS.txt. Filter to the type 2 diabetes participants using explicit study labels, otherwise the published study's HbA1c >6.4% rule (proxy, not independently verified diagnosis).
3. Use one CGM stream only (Dexcom GL by default); do not combine Dexcom and Libre as independent observations. Select nominal 5-minute points from the interpolated minute table; this may not recover exact sensor-native readings and requires further audit.
4. Construct 60-minute historical windows and 60-minute future CGM-sample low-glucose surrogate labels, without future leakage or long-gap interpolation. Apply frozen Shanghai models without fitting or recalibration on CGMacros.
5. Report external eligible subjects, positive subjects and positive windows before AUROC/AUPRC; if only one outcome class, return **inconclusive**.
6. If estimable, report discrimination, Brier/log loss, calibration, patient-clustered confidence intervals, and sensor-level episode/alert statistics.

## Key scientific limitations

This cohort has only 14 participants with T2D and is a meal-focused study, not a hypoglycemia-enriched cohort. Low-glucose events may be absent. The one-minute tables are interpolated; the nominal-grid subsampling must not be presented as verified raw CGM. Differences in devices, recruitment, measurement schedules, patient demographics, and dates introduce distribution shift. An insufficient-event finding is an important negative feasibility result, not grounds to change the endpoint after observing outcomes.

**No clinical claims** are authorized by this retrospective workflow. External validation requires a successful completed run and a detailed sensor/data-quality audit. Even successful external discrimination does not establish clinical utility.
