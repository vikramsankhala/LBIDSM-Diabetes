# Prespecified validation roadmap

1. Establish clinical use case and fixed event labels (e.g., next-60-minute level 2 glucose event); specify sensor confirmation and repeated-event grouping before training.
2. Retrospectively construct person-specific timelines and patient-grouped train/validation/test partitions. Reserve external sites and future periods for locked evaluation.
3. Compare M0 last glucose/slope, M1 conventional CGM windows, M2 patient history/medications, M3 state-space resilience features. Perform ablations.
4. Train and calibrate without future information, using held-out patient groups. Compare against clinically accepted baselines.
5. Report event-level sensitivity, false alarms/patient-day, AUROC/AUPRC, Brier score, calibration curves, alert lead-time distribution, clinical utility and interval uncertainty.
6. Audit sensor gaps, interstitial measurement artifacts, age/comorbidity groups, medications, care settings, demographic representativeness and dataset shift.
7. For intervention effects, specify an emulated target trial, treatment assignment, time zero, censoring, confounders, positivity and competing risks. Use credible methods and trial anchoring.
8. Prospectively evaluate in silent mode, then undertake safety and effectiveness studies subject to ethics/regulatory review.

**Release gates:** No clinical claims without independent external validation; no causal recommendations from predictive risk alone; no autonomous drug actions. Document TRIPOD+AI reporting and local regulatory review.
