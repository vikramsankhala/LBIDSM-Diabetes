# Eight-layer research architecture

**The implemented application covers data validation, basic CGM analytics and a synthetic-data interface.** Other layers below are future development goals and must not be treated as deployed clinical functions.

| Layer | Input | Research responsibility | Status |
|---|---|---|---|
| L0 Data provenance | CGM, laboratory, EHR, medication records | Validate, align, timestamp and audit | CGM CSV prototype only |
| L1 Predisposition | Age, family/genetic history, prior events | Long-horizon vulnerability | Planned |
| L2 Clinical context | CKD, cardiovascular disease, frailty, therapies | Contraindications, baseline risk | Planned |
| L3 Observed state | CGM and laboratory data | Clinical definitions, quality gates | Descriptive analytics |
| L4 Dynamics | Longitudinal measurements | State estimation, recovery, change points | Rolling features only |
| L5 Prediction | Historical features and calibrated outcome labels | Horizon-specific event probability | Planned |
| L6 Causality | Eligibility, treatment assignment, outcomes | Benefit–harm counterfactuals | Planned |
| L7 Governance | Evidence, uncertainty, action eligibility | Human review and abstention | Specified, not deployed |

## Target computational interfaces

`validate(observations, as_of) → QualityReport`

`estimate_state(history, theta) → StatePosterior`

`predict_event(history, horizon) → CalibratedRisk`

`estimate_action_effect(history, action, horizon) → EffectInterval`

`optimize_review_policy(risks, effects, evidence, eligibility) → ResearchRecommendationOrAbstain`

Every call must carry timestamp, cohort eligibility, provenance, model version, sensor conditions, missingness indicators, and decision audit data. No treatment action is executable.

## Key mathematical models

State dynamics: `x[t+1] = f_theta(x[t], u[t], w[t]) + process_noise`; observation: `y[t] = h_theta(x[t]) + measurement_noise`.

Event risk: `P(min_{s in (t,t+T]} glucose[s] < 54 | history as-of t)`.

Causal effect: `ARR_a(T|H) = P(Y^0_T=1|H) - P(Y^a_T=1|H)`.

Robust evaluation: `max_a min_{q in Q} E_q[net_benefit(a)]` with clinical admissibility and abstention.

These formulas are **research targets**. Model identifiability, causal assumptions, uncertainty calibration and safety constraints must be evaluated prior to clinical use.
