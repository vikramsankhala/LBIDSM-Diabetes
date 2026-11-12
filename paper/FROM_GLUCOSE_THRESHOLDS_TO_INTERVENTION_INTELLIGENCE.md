# From Glucose Thresholds to Intervention Intelligence

## A Layered, Causally Informed and Uncertainty-Aware Decision-Support Architecture for Type 2 Diabetes and Metabolic Regulation

**Vikram Singh Sankhala** · Independent research white paper · **13 November 2026**

**Suggested citation (APA 7):** Sankhala, V. S. (2026). *From glucose thresholds to intervention intelligence: A layered, causally informed and uncertainty-aware decision-support architecture for type 2 diabetes and metabolic regulation* [White paper].

> **STATUS:** Proposed research architecture and implementation blueprint. No original patient data have been analyzed; no prediction model has been trained or externally validated; no clinical benefit is claimed.

**Source:** Author-supplied six-page PDF `LBIDSM_DM_White_Paper_Vikram_Singh_Sankhala(1).pdf`. This Markdown edition preserves its scientific sections, figures/tables as text, and references; the original PDF has not been uploaded as a binary GitHub asset.

## Executive summary

Conventional diabetes management uses clinically validated measures such as HbA1c, glucose thresholds and continuous glucose monitoring (CGM) summaries. These measures are indispensable but do not, by themselves, fully characterize predisposition, dynamic deterioration, intervention responsiveness or uncertainty. This paper proposes LBIDSM-DM, an eight-layer, auditable research architecture that separates (i) established safety and guideline rules, (ii) personalized outcome prediction, and (iii) causal evaluation of possible interventions. The proposed initial use case is short-horizon prediction of level 2 hypoglycemia in adults with type 2 diabetes, followed by medium-term glycemic deterioration and longer-term cardiorenal risk. The design prioritizes clinical oversight, prospective validation, privacy, and abstention when data are inadequate.

## 1. Problem statement and contribution

A single glucose value is a snapshot; its meaning depends on the direction and speed of change, medication exposure, renal function, prior hypoglycemia, clinical status and the outcome horizon. Equally, high predicted risk does not prove that changing treatment improves outcomes. The central contribution is an explicit separation of risk stratification from intervention effect estimation and decision policy. This is an architectural proposal, not an experimentally established advance.

## 2. Clinical scope, population and intended use

**Target population:** Nonpregnant adults with type 2 diabetes, initially in research datasets with CGM and time-stamped medication records. Exclude or separately model pregnancy, type 1 diabetes, acute inpatient care and major data gaps. **Primary target:** Future CGM-confirmed glucose <54 mg/dL within a prespecified 30–120-minute horizon; event definitions must account for sensor artifacts and minimum episode duration. **Secondary targets:** Severe hypoglycemia requiring assistance (clinical adjudication), 7–30-day glycemic deterioration and separate longer-horizon kidney/cardiovascular outcomes.

**Intended user:** Researcher and, after validation and governance, a qualified clinician. The initial software operates in silent/read-only mode and cannot prescribe, adjust doses, or actuate medical devices.

## 3. Established clinical foundations and boundaries

| Measure / rule | Evidence-based reference | Interpretation / caution |
|---|---|---|
| Level 1 hypoglycemia | 54 to <70 mg/dL | Clinically important low glucose; follow approved protocol. |
| Level 2 hypoglycemia | <54 mg/dL | Requires immediate action; never await model score. |
| Level 3 hypoglycemia | Severe event requiring assistance | Clinical definition independent of glucose reading. |
| HbA1c target | <7% for many nonpregnant adults | Individualize for comorbidities, frailty, treatment burden. |
| CGM TIR | >70% in 70–180 mg/dL for many adults | Management goal, not emergency trigger. |
| CGM TBR | <4% below 70; <1% below 54 | Higher-risk older adults may need stricter low-glucose limits. |
| CGM variability | CV ≤36% | Population guidance; not a stand-alone decision rule. |
| CGM sufficiency | ~14 days with ≥70% active data | For pattern assessment; acute predictions need separate data checks. |

These figures are drawn from the American Diabetes Association (ADA) 2026 Standards of Care, especially Section 6 and Section 13 [1–2]. Clinical rules must be versioned, scoped and reviewed by qualified clinicians. Thresholds for inpatient care and pregnancy differ and are outside this prototype.

## 4. Eight-layer model specification

| Layer | Core inputs / processing | Outputs |
|---|---|---|
| L0 Data integrity | Time alignment, CGM quality, units, provenance, missingness | Usability flags and audit record |
| L1 Predisposition | Family history, diabetes duration, genetics where valid, age at diagnosis | Baseline susceptibility features |
| L2 Clinical vulnerability | CKD/eGFR, ASCVD, heart failure, prior events, frailty, medicines | Clinical risk modifiers |
| L3 Current state | CGM, HbA1c, TIR/TBR/TAR, renal and metabolic labs | Current state and target deviations |
| L4 Dynamics | Glucose slope, acceleration, CV, recovery, residual change points | Temporal and mechanistic features |
| L5 Prediction | Outcome-specific calibrated models and horizons | Event probability with uncertainty |
| L6 Causal evaluation | Evidence-backed treatment effects, harms, eligibility | Action-specific expected net benefit |
| L7 Governance/decision | Safety rules, uncertainty, clinician targets and review | Escalation / review / monitor / abstain |

## 5. Mathematical formulation

### 5.1 Patient state and predisposition

Let `Z_i = (G_i, F_i, H_i, C_i, M_i, E_i)` denote genetics, family history, prior history, comorbidities, medication exposure and environmental factors. Let `X_i(t)` be current physiological measurements, `D_i(t)` time-varying dynamic features, and `H_i(t)` the complete available history. For event `Y` within horizon `T`, estimate `p_i(t,T) = P[Y_i(t,t+T)=1 | H_i(t)]`. Models are trained for specific outcomes and horizons, not a universal disease score.

### 5.2 CGM features and dynamics

For valid equally spaced glucose readings `g_j`, `TIR = 100 × mean(70 ≤ g_j ≤ 180)`; `TBR70 = 100 × mean(g_j < 70)`; `TBR54 = 100 × mean(g_j < 54)`; `CV = 100 × SD(g)/mean(g)`. For irregular sampling, duration-weighted calculations are required. Glucose velocity `v(t) ≈ [g(t) − g(t−Δt)]/Δt`. Candidate research features include excursion recovery time, forecast residual variance and change-point probability. Feature extraction must not use readings after the prediction timestamp.

### 5.3 Mechanistic and stability analysis

A conceptual nonlinear model has `dx/dt = f(x,u,w,θ)`, with metabolic state `x`, interventions `u`, disturbances `w` and individual parameters `θ`. Near a state `x*`, linearization gives `δẋ = Jδx + Bδu + Eδw`. Eigenvalues of `J` describe local modes; `σ_max(exp(Jt))` describes worst-case transient state amplification for a chosen norm. These quantities are mathematical research candidates, not established diabetes intervention indicators. Physiological nonstationarity, unobserved insulin activity and model-identification uncertainty limit their interpretation.

### 5.4 Causal benefit–harm evaluation

For eligible intervention `a`, estimate `p_a = P(Y_T(a)=1 | H_t)` and `ARR(a) = p_0 − p_a`. Compare multiple outcomes using `U(a) = −Σ_k w_k P(Y_k(a)=1 | H_t) − C(a) − B(a)`, with clinically agreed weights, costs and treatment burdens. Optimize `a* = argmax_a U(a)` subject to clinical eligibility and safety constraints. Observational estimation requires a target-trial specification, exchangeability assumptions, positivity checks, time-varying confounding management and sensitivity analyses. Prognostic accuracy alone cannot validate these causal effects.

### 5.5 Uncertainty and abstention

Report calibration, interval estimates and quality flags, not just a point probability. Distinguish aleatoric variability, model uncertainty, and missing or stale data. If essential records are missing, the patient lies outside the model’s validated domain, or uncertainty exceeds prespecified criteria, the decision layer must abstain and request clinical review. Safety protocols override any model-generated low-risk estimate.

## 6. Decision policy and clinical safety

| Decision category | Basis | Permitted system behavior |
|---|---|---|
| Safety escalation | Verified condition-specific urgent rule or concerning symptoms | Show approved protocol and clinical escalation; no autonomous therapy |
| Intervention review | Validated risk and evidence-supported net benefit | Present options and trade-offs for clinician decision |
| Additional assessment | Uncertain prediction, discordant data, missing inputs | Request measurements/reconciliation; abstain |
| Routine monitoring | No urgent rule; validated policy does not favor action | Continue scheduled reassessment |

The model must never use a synthetic composite index to initiate or withhold treatment. The previously discussed exploratory 0–100 prioritization score is excluded from clinical decision logic.

## 7. Data model, interoperability and security

Recommended entities: patients; predisposition; conditions; medications (ingredient, dose, route, exposure intervals); observations (value, unit, timestamp, source, quality); CGM samples; clinical events (onset, severity, adjudication); interventions; predictions (model/version/horizon/interval); decisions (rule, reviewer, override, rationale). All tables require pseudonymous IDs, valid-time semantics and immutable audit history. Use FHIR-compatible interfaces and standard terminologies where feasible. Apply role-based access, encryption, consent governance, retention controls and jurisdiction-specific data protection review. Genetic data require especially restrictive access and explicit purpose limitation.

## 8. Reference implementation blueprint

Research stack: Python, Pandas/Polars, NumPy/SciPy, scikit-learn and statsmodels; survival-analysis tools for long-term outcomes; CVXPY for constrained optimization experiments; PostgreSQL and Parquet; FastAPI service interfaces; Streamlit research dashboard; pytest, reproducible pipelines and model registry. Separate services: (1) ingestion/validation, (2) feature engineering, (3) clinical rules, (4) risk inference, (5) causal evidence evaluation, (6) decision/audit, (7) monitoring. Rules and ML models must have independent version histories and approval processes.

### 8.1 Illustrative schema contract

```text
observations(patient_id, observed_at_utc, code, value_numeric, unit, source_id, quality_flag);
medications(patient_id, ingredient_code, dose_value, dose_unit, route, start_at, end_at, verified);
predictions(patient_id, as_of_time, outcome_code, horizon_minutes, probability, interval_low, interval_high,
            model_version, data_quality_status);
decisions(patient_id, decision_time, rule_version, category, evidence_summary,
          clinician_action, override_reason).
```

### 8.2 Reproducible execution sequence

Validate and align inputs → apply urgent safety rules → calculate CGM features → check model eligibility and drift → generate calibrated outcome probabilities → quantify uncertainty → compare only evidence-supported intervention options → present rationale and abstention status → record clinical review and follow-up outcomes.

## 9. Research hypotheses and experimental design

- **H1:** Dynamic glucose features improve prediction beyond current glucose, recent CGM history and standard clinical variables.
- **H2:** Prior severe hypoglycemia, renal function and glucose-lowering medication class modify predictive relationships.
- **H3:** State-space stability or transient-gain features provide incremental benefit beyond conventional CGM metrics.
- **H4:** Causal benefit–harm evaluation improves decision utility compared with risk-only review policies.
- **H5:** Uncertainty-aware abstention reduces misleading alerts and inappropriate recommendations.

Prespecify a primary outcome and horizon, baseline comparators, sample-size/event-count justification, temporal and patient-level splits, missingness policy and locked evaluation plan. Avoid leakage from future CGM, laboratory results or interventions. Compare logistic/regularized baselines with gradient boosting and dynamic models. Do not use random row splits for serial CGM data.

## 10. Validation and acceptance gates

| Phase | Evidence required | Gate |
|---|---|---|
| A. Retrospective | Discrimination, calibration, event sensitivity, lead time, false alerts per patient-day | Reproducible results; no leakage |
| B. External | Independent institutions, devices, demographics, treatment patterns | Prespecified generalization and subgroup criteria |
| C. Silent prospective | Live data quality, drift, alert burden, prospective calibration | No care influence; safety review |
| D. Impact evaluation | Clinical outcomes, harms, clinician workload, net benefit | Ethics/regulatory approval before clinical use |

Report AUROC, AUPRC, calibration intercept/slope, Brier score, event-level sensitivity, positive predictive value, false alerts per patient-day, warning lead time, subgroup calibration and decision-curve net benefit. Use patient-clustered uncertainty intervals. Report in accordance with TRIPOD+AI where applicable [3]. Clinical impact requires prospective evidence; statistical performance is not sufficient.

## 11. Limitations, ethical considerations and research agenda

Physiological observability is incomplete; CGM measures interstitial glucose and can be noisy or delayed; medication adherence and meal timing may be misrecorded; genetic scores may not generalize; retrospective intervention comparisons are confounded; and dynamics derived from a local Jacobian may fail under nonlinear regime shifts. The architecture does not establish any novel clinical threshold, approved treatment algorithm or universal robustness index. Patient autonomy, informed consent, fairness, transparent uncertainty and clinician accountability are necessary design constraints.

Near-term research priorities are (i) a well-adjudicated level 2 hypoglycemia cohort; (ii) external evaluation of dynamic features; (iii) medication and renal-function interaction studies; (iv) a target-trial protocol for a narrowly specified intervention; and (v) prospective silent-mode testing.

## 12. Conclusion

LBIDSM-DM proposes a progression from threshold-centric monitoring to an auditable, personalized and intervention-aware diabetes decision-support framework. Its distinctive methodological requirement is separation of established clinical rules, probabilistic prognosis, causal treatment effects and governance. The architecture is feasible as a research program, but claims of predictive superiority or clinical utility must await external and prospective validation.

## References (APA 7)

1. American Diabetes Association Professional Practice Committee. (2026). 6. Glycemic goals, hypoglycemia, and hyperglycemic crises: Standards of Care in Diabetes—2026. *Diabetes Care, 49*(Suppl. 1). https://doi.org/10.2337/dc26-S006
2. American Diabetes Association Professional Practice Committee. (2026). 13. Older adults: Standards of Care in Diabetes—2026. *Diabetes Care, 49*(Suppl. 1). https://doi.org/10.2337/dc26-S013
3. Collins, G. S., et al. (2024). TRIPOD+AI statement: Updated guidance for reporting clinical prediction models that use regression or machine learning methods. *BMJ, 385*, e078378. https://doi.org/10.1136/bmj-2023-078378
4. Battelino, T., et al. (2019). Clinical targets for continuous glucose monitoring data interpretation: Recommendations from the international consensus on time in range. *Diabetes Care, 42*(8), 1593–1603. https://doi.org/10.2337/dci19-0028
5. Hernán, M. A., & Robins, J. M. (2016). Using big data to emulate a target trial when a randomized trial is not available. *American Journal of Epidemiology, 183*(8), 758–764. https://doi.org/10.1093/aje/kwv254
6. Vickers, A. J., & Elkin, E. B. (2006). Decision curve analysis: A novel method for evaluating prediction models. *Medical Decision Making, 26*(6), 565–574. https://doi.org/10.1177/0272989X06295361

## Author note and disclosure

Vikram Singh Sankhala. This document is an independently proposed conceptual research white paper, prepared with AI-assisted drafting and formatting. The author should verify final citations, affiliations, technical claims and any institutional permissions before public release. No clinical study, patient dataset, independent peer review or regulatory evaluation is represented.
