# Baseline covariates, preliminary endotypes, PCA and confounder screening

**Scientific status:** research-only code, tested on synthetic data. No result on real patients is claimed.

**Why:** the principal objective is to move from generalised treatments to endotype-specific approaches. These modules are the first Phase 1 step toward it.

## What was added
- `lbidsm.covariates`: one-row-per-subject baseline metabolic (HbA1c, BMI, fasting glucose/insulin, HOMA-IR, lipids, eGFR, duration), genetic (polygenic score, SNP dosage) and treatment (sulfonylurea, insulin) columns, joined to windows.
- `prediction.benchmark_extended`: logistic regression with CGM features only, + metabolic, + metabolic/genetic/treatment, + preliminary endotype. Median imputation, scaling, PCA and clustering are fitted on training subjects only; static covariates are L2-penalised (C=0.1) because effective sample size is the number of subjects, not windows.
- `lbidsm.endotypes.EndotypeClusterer`: standardise, PCA (components to 80% variance, capped at 6), k-means for k=2..5, k chosen by bootstrap stability then silhouette. A cluster set is labelled **preliminary** if stability ARI < 0.8 or silhouette < 0.25. Baseline covariates only; whole-record CGM summaries are excluded because they would leak the outcome.
- `lbidsm.confounders.screen_confounders`: declared role per variable (mediators such as BMI/HOMA-IR are never adjusted for), then association with exposure and outcome and change-in-estimate. This ranks adjustment candidates; it does not identify causal effects, which need a causal diagram agreed in advance.

## Limits
Static covariates are constant within a subject, so a cohort of a few dozen people can overfit; report subject counts. Clusters are hypotheses until replicated in an independent cohort and tied to a mechanism or treatment response. Genetic data need consent, purpose limitation and ethics approval.
