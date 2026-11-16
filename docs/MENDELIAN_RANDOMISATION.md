# Mendelian randomisation and endotype schema (research-only)

`src/lbidsm/mr.py` filters drug targets with two-sample summary-data MR and the safeguards
that guard against false positives. A pass is a **Tier C hypothesis**, never proof, and the
code has been exercised on simulated data only.

| Step | Function | Purpose |
| --- | --- | --- |
| Estimate | `wald_ratio`, `ivw`, `mr_egger`, `weighted_median` | causal effect of exposure on outcome |
| Strength | `instrument_strength`, `steiger_direction` | weak instruments; direction of effect |
| Colocalisation | `colocalisation` | same causal variant for protein and disease |
| Reverse MR | `reverse_mr` | does the disease move the protein? |
| Safety | `safety_read_across` | on-target effects on non-diabetes traits |
| Strata | `stratified_mr` | does the effect differ between endotypes? |
| Verdict | `target_filter` | fails closed when any check is missing |

`src/lbidsm/endotype_schema.py` records the six routine variables (GAD antibodies, age at
diagnosis, BMI, HbA1c, HOMA2-B, HOMA2-IR) and the extended layers L2 (clinical vulnerability),
L3 (CGM metrics) and L4 (dynamic stability, exploratory), with a coverage report, a HOMA2
warning and a preliminary workflow. It stores no published cluster centres.

Limits: alleles must be harmonised before use; colocalisation assumes one causal variant per
locus; stratified MR needs stratum-specific genetic summary statistics, which are rare; MR
with few instruments has low power; the synthetic generator is for tests only.
Run `python scripts/run_mr_demo.py` for the demonstration.
