# Research modules (v0.3.0)

**Status:** research code tested on synthetic data only. Not a medical device. Not clinically validated. Do not use for patient care.

This page maps each item in the README's gap list to the code that now exists, what it does in plain words, and what is still missing.

## Module map

| README area | Layer | File | What it does | Still missing |
|---|---|---|---|---|
| Clinical-grade data pipelines | L0 | `src/lbidsm/integrity.py` | Audits each person's CGM record against a written policy (cadence, coverage, gaps, stuck sensor, duplicates, out-of-range). Returns pass or fail with reasons. Failed records are stopped, never repaired. Fingerprints raw files with SHA-256. | Policy thresholds are placeholders to fix in a protocol; no EHR, lab or medication ingestion; no certified quality system |
| Trained hypoglycemia prediction | L5 | `src/lbidsm/prediction.py`, `src/lbidsm/model_bundle.py` | M0, M1, M2 baselines, patient-disjoint splits, Platt calibration. `model_bundle.py` stores a trained model as JSON with a SHA-256 fingerprint, so "locked before unblinding" can be checked. | Only logistic baselines; no state-space (M3) model; no adjudicated event labels |
| External validation | L5 | `src/lbidsm/validation.py` | Qualification gate (independent episodes, event-positive people, planned precision), then locked-model scoring with patient-clustered intervals. If the gate fails, no performance number is produced. | No qualified external cohort yet (see the qualification report); thresholds must be written into a protocol |
| Patient-specific causal effects | L6 | `src/lbidsm/causal.py` | One-time-zero target-trial emulation with stabilised, truncated weights, balance and overlap checks, bootstrap intervals, E-value, per-person effect estimates. | Time-varying treatment (marginal structural model), competing risks, negative controls |
| Genetics | L1 | `src/lbidsm/genetics.py` | Mendelian randomisation from summary statistics: harmonisation, instrument strength, IVW, MR-Egger, weighted median, heterogeneity warnings. | Not run on real data; no colocalisation; no polygenic scores |
| Optimized treatments | L6 | `src/lbidsm/utility.py` | Net utility U(a) = benefit - weighted harms - cost, with a robust ranking across value scenarios. Severity weights have no defaults. | Clinically elicited weights; approved eligibility rule table |
| Personalized medical recommendations | L7 | `src/lbidsm/policy.py` | Routes evidence to Escalate, Review, Assess, Monitor or Abstain with data-contract audit fields. Executes nothing. | Clinician sign-off of thresholds and ordering; user-interface and workflow design |
| Regulatory compliance | all | `src/lbidsm/evidence.py`, `src/lbidsm/requirements.py` | Traces each requirement to its tests, collects hashes and gate results, lists release blockers mirroring `docs/VALIDATION.md`. | Intended-use statement, risk file, quality system, regulator engagement |
| Production access controls | all | `src/lbidsm/access.py`, `scripts/check_no_patient_data.py` | Deny-by-default roles, conditions for restricted data, hash-chained audit log, small-cell suppression (below 5), a CI guard against committed patient data. | Identity provider, key management, write-once log storage, penetration test |

## Run it

```powershell
git clone https://github.com/vikramsankhala/LBIDSM-Diabetes.git
cd LBIDSM-Diabetes
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/demo_research_pipeline.py --out demo_results
python scripts/demo_research_pipeline.py --out demo_sparse --sparse-external
```

The second demo mimics the CGMacros situation (few people, almost no events). The qualification gate stops and reports "inconclusive" instead of a score.

## Decisions that need a human

These are deliberate design choices that code cannot settle. Each should be written into the study protocol and signed off.

1. **Qualification thresholds.** `QualificationPolicy` has no defaults: minimum event-positive people, minimum independent episodes, largest acceptable interval width. The project documents do not agree on a universal event count, so the code refuses to invent one.
2. **Severity weights.** `utility.py` requires explicit weights for each harm. They are value judgements made with clinicians and patients.
3. **Escalate before Abstain.** `policy.py` escalates a reading below 54 mg/dL even if data-quality checks failed, and says the reading is unverified. Clinicians must approve this ordering.
4. **Eligibility rules.** Which actions are eligible for which person must come from a clinician-approved, versioned rule table. None is included.
5. **Wording.** Use "pseudonymous", not "de-identified", unless counsel confirms otherwise.

## Safety limits that stay in force

No clinical claims without independent external validation. No causal recommendations from predictive risk alone. No autonomous drug actions. TRIPOD+AI reporting and local regulatory review must be documented (see `docs/VALIDATION.md`).
