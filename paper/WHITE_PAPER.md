# A Proposed Mathematical and AI Architecture for Personalized Intervention Decision Support, for Diabetes

**Vikram Singh Sankhala**  
Computational research white paper · Version 2.0 · 13 November 2026

> **Scientific status:** Proposed architecture and research hypotheses. No patient dataset was analyzed in preparing this manuscript; no predictive or causal model has been trained, externally validated, or authorized for medical decisions.

## Abstract

This paper presents the Layered Biological Intervention Decision Support Model for Diabetes (LBIDSM-DM), an auditable computational framework combining predisposition, time-varying clinical context, continuous glucose monitoring (CGM), state-space estimation, probabilistic risk prediction, causal intervention effects, and robust optimization. The central research proposition is that *the likelihood of deterioration* and *the expected benefit or harm of an intervention* are mathematically distinct estimands. We formulate the architecture, feature and event definitions, model comparison design, uncertainty handling, validation requirements, and clinician-governance boundaries. Stability and transient-amplification features are proposed as hypotheses, not established clinical triggers.

**Keywords:** type 2 diabetes; clinical AI; CGM; dynamical systems; causal inference; model-predictive control; uncertainty; personalized medicine.

## 1. Scope, endpoints and intended use

The target cohort is adults with type 2 diabetes under ethically approved observational or prospective study. Type 1 diabetes, pregnancy and acute metabolic crises require separate pathways and must not be assumed covered. Immediate research endpoints include next-30-, 60- and 120-minute level 2 glucose events; intermediate endpoints include changes in low-glucose burden and glycemic variability; long-horizon outcomes include adjudicated kidney and cardiovascular events.

The prototype should support **silent-mode research** and eventual **clinician-reviewed decision support**, not automated treatment. An event label requires a prespecified sensor confirmation and separation scheme; a single sensor reading does not equate to an adjudicated clinical episode. Urgent symptoms and suspected metabolic emergencies remain subject to established clinical protocols.

## 2. Computational graph and notation

The proposed dependency graph is:

```text
CGM / EHR / laboratories / medication history
        ↓
L0 provenance, units, timestamp and quality gates
        ↓
L1 predisposition + L2 comorbidities and exposures
        ↓
L3 measured metabolic state + L4 temporal dynamics
        ↓
L5 calibrated risk at prespecified horizons
        ↓
L6 causal action benefit–harm estimation
        ↓
L7 eligibility + uncertainty-aware decision gate
        ↓
Human clinical review → outcome recording → evaluation
```

Let `i` index patients, `t` denote decision time, `T` denote prediction horizon, `Z_i` represent static predisposition, `x_i(t)` be latent metabolic state, `y_i(t)` observed measurements, `u_i(t)` recorded therapies, `w_i(t)` disturbances and `H_i(t)` the strictly predecision history.

## 3. Predisposition and evolving clinical vulnerability

Baseline candidate features include age, diabetes duration, family history, prior severe hypoglycemia, kidney function, cardiovascular disease, frailty, treatment exposure and—when consented and validated—genetic markers. Genetic information needs ancestry-aware evaluation and demonstrable incremental performance. Kidney function and medications vary over time and cannot automatically be treated as fixed baseline features.

A candidate baseline risk model is

```math
logit P(Y_T = 1 | Z_i)
 = alpha_0(T) + beta' Z_i + sum_{j,k} theta_(j,k) Z_(i,j) Z_(i,k).
```

Parameters are learned with regularization and prespecified interactions, not assigned as arbitrary expert-weighted risk points. Missingness modeling needs explicit analysis of nonrandom missing data.

## 4. CGM features and established clinical reference points

For time-aligned glucose `g_j`, define

```math
TIR = 100 * sum_j Delta_t_j * 1(70 <= g_j <= 180) / sum_j Delta_t_j
TBR70 = 100 * sum_j Delta_t_j * 1(g_j < 70) / sum_j Delta_t_j
TBR54 = 100 * sum_j Delta_t_j * 1(g_j < 54) / sum_j Delta_t_j
CV = 100 * SD(g) / mean(g)
v_t = (g_t - g_(t-1)) / (t - t_(t-1)).
```

For equally spaced valid samples this reduces to sample proportions. Long gaps must be excluded and coverage reported separately. Common guidelines distinguish level 1 hypoglycemia (<70 and ≥54 mg/dL), level 2 (<54 mg/dL), and level 3 (severe event requiring assistance, regardless of glucose). For many nonpregnant adults, familiar CGM reference goals include TIR 70–180 mg/dL >70%, TBR <70 mg/dL <4%, TBR <54 mg/dL <1%, and CV ≤36%, with individualization for older or medically complex people. HbA1c <7% is often an individualized treatment goal for many adults. These are *descriptive reference points*, not universal automatic therapy triggers [1,2,5].

## 5. Dynamic state estimation and nonnormal amplification

We propose a partially observed nonlinear system:

```math
x_(t+1) = f_theta(x_t, u_t, w_t) + eta_t
y_t     = h_theta(x_t) + epsilon_t.
```

Possible latent states include plasma glucose, effective insulin action, glucose appearance and a slow insulin-sensitivity proxy; observations reflect interstitial CGM and laboratory measurements. Model identifiability and observability must be established before physiological interpretations are made.

The local Jacobian approximation is

```math
delta_x_(t+1) = A_t delta_x_t + B_t delta_u_t + E_t delta_w_t;
delta_y_t = C_t delta_x_t + epsilon_t.
```

Candidate techniques include extended or unscented Kalman filters and particle filtering. Research-only features include an estimated return time `tau ≈ -1/Re(lambda_max(A))` in appropriate stable regimes, transient gain `G(k) = sigma_max(A^k)`, change-point probability and the innovation Mahalanobis statistic `r_t' S_t^(-1) r_t`. Even a stable nonnormal system may display transient perturbation growth, but **no validated diabetes intervention cutoff is claimed for these features**.

## 6. Time-resolved risk prediction

A proposed primary estimand is

```math
p_i(t,T) = P(min_(s in (t,t+T]) G_i(s) < 54 | H_i(t), eligible, sensor_valid).
```

The experimental comparison is M0 (current glucose and recent slope), M1 (standard CGM history), M2 (history, comorbidities and medication exposures), M3 (dynamical state/resilience features). Models may include penalized logistic regression, gradient boosting, discrete-time survival models or temporal neural networks. All feature windows terminate no later than decision time `t`. Calibration is evaluated on disjoint sets.

Outcome-specific longer-term hazards can be modeled as `h_(i,k)(t) = h_(0,k)(t) exp(beta_k' Z_i + gamma_k' X_i(t))`, with competing-risk treatment where warranted. Do not merge incompatible outcomes into one uncalibrated risk score.

## 7. Causal intervention evaluation

Predicting poor glycemic control does not show that a proposed treatment change will help. For each eligible action `a`, define the target trial's time zero, comparator, allocation process, treatment adherence, censoring, outcome and observation horizon. Observational causal claims require consistency, conditional exchangeability, positivity and appropriate time-varying confounder control [4].

```math
ARR_a(T|H_t) = P(Y_T^(0)=1 | H_t) - P(Y_T^(a)=1 | H_t)
NB_a(H_t) = sum_k w_k [p_(k,0) - p_(k,a)] - C_a - Harm_a.
```

Weights must come from defensible clinical and patient preferences. Report uncertainty, alternate assumptions and sensitivity to unmeasured confounding. No causal treatment efficacy is estimated by the bundled demonstration.

## 8. Robust constrained decision evaluation

The research optimizer is defined for clinically admissible **review and information-gathering pathways**:

```math
a* = arg max_(a in A(H_t)) min_(q in Q(H_t)) E_q[NB_a(H_t)]
subject to: P_q(safety_violation | a,H_t) <= epsilon for all q in Q.
```

Here `Q` is an uncertainty set over calibrated risk and treatment effects. If the action set is empty, uncertainty excessive, sensor invalid or cohort out-of-distribution, the model abstains and requests human review. The proposed value of additional testing is `VOI(test) = E[max_a E(U(a)|H_t,new_test)] - max_a E(U(a)|H_t) - cost(test)`; this cannot be evaluated without an explicit test-outcome model.

## 9. Evidence hierarchy and governance

**Tier A:** Reviewed and versioned clinical definitions/protocols may support safety annotations. **Tier B:** Externally calibrated predictors may display probabilities with intervals and limitations. **Tier C:** Clinically credible causal estimates may show conditional benefits and harms after ethics review. **Tier D:** Novel dynamical indicators remain research-only until independently validated.

Decision order: validate units/provenance; apply independent safety protocols; check eligibility/applicability; display calibrated outcome-specific risk; assess evidence-backed causal action comparisons; abstain on uncertainty; require clinician authorization; log decisions. Predictions never override emergencies or established safety rules.

## 10. Demonstration architecture and data contracts

The accompanying Streamlit application implements synthetic CGM generation, descriptive metrics, historical rolling features and threshold annotations. It does **not** implement the full mathematical research stack. Planned data entities are `patients`, `conditions`, `observations`, `medications`, `events`, `predictions` and `decisions`, each with provenance, UTC observation/ingestion times, eligibility, unit codes and model/rule versions. See [data contract](../docs/DATA_CONTRACT.md).

## 11. Validation and falsifiability

Prespecify the cohort, outcome labels, subgroup endpoints, alert-horizon and false-alert burden. Train on patient-grouped and temporally appropriate partitions, reserve independent external sites, and prohibit future leakage. Compare nested feature sets against simpler baselines. Report calibration intercept/slope, Brier score, AUROC, AUPRC, event-level sensitivity, lead time and false alerts per patient-day with patient-clustered uncertainty intervals. Evaluate decision-curve net benefit separately from discrimination.

Hypothesis H1: adding validated historical and medication features improves external discrimination/calibration over CGM alone. H2: state-space features add incremental signal under perturbations. H3: dynamic features remain useful under distribution shift after uncertainty-aware abstention. H4: credible action-effect modeling improves decision utility over risk-only alerts. H5: constrained abstention reduces unsafe or unsupported recommendations. None is assumed true.

The required progression is retrospective development, locked external validation, prospective silent-mode evaluation, clinician-reviewed feasibility, and ultimately protocol-approved clinical impact testing. Follow TRIPOD+AI reporting guidance [3].

## 12. Risk and failure analysis

Threats include CGM compression artifacts, interstitial sensor lag, data gaps, unit errors, undocumented medications, kidney function drift, inconsistent event labels, confounding by indication, model shift, population portability, alert fatigue and automation bias. Mitigations include quality and out-of-distribution gates, time-stamped provenance, decision logging, patient-grouped evaluation, model cards, periodic audit, incident reporting and human oversight.

## 13. Conclusion

LBIDSM-DM is a proposed separation of measurement, latent-state inference, event prediction, causal intervention estimation and uncertainty-aware, constrained action review. It does not establish a novel clinical threshold or validated universal score. The next empirical milestone is an independently assessed short-horizon level 2 hypoglycemia prediction study and a safety-focused clinician-review workflow.

## References (APA style; verify full publisher metadata before scholarly submission)

1. American Diabetes Association Professional Practice Committee. (2026). Glycemic goals, hypoglycemia, and hyperglycemic crises: Standards of Care in Diabetes—2026. *Diabetes Care, 49*(Suppl. 1). https://doi.org/10.2337/dc26-S006
2. Battelino, T., et al. (2019). Clinical targets for continuous glucose monitoring data interpretation: Recommendations from the international consensus on time in range. *Diabetes Care, 42*(8), 1593–1603. https://doi.org/10.2337/dci19-0028
3. Collins, G. S., et al. (2024). TRIPOD+AI statement: Updated guidance for reporting clinical prediction models that use regression or machine learning methods. *BMJ, 385*, e078378. https://doi.org/10.1136/bmj-2023-078378
4. Hernán, M. A., & Robins, J. M. (2016). Using big data to emulate a target trial when a randomized trial is not available. *American Journal of Epidemiology, 183*(8), 758–764. https://doi.org/10.1093/aje/kwv254
5. American Diabetes Association Professional Practice Committee. (2026). Older adults: Standards of Care in Diabetes—2026. *Diabetes Care, 49*(Suppl. 1). https://doi.org/10.2337/dc26-S013

*Reference metadata and clinical recommendations should be verified against publishers and local clinical protocols before external academic publication.*
