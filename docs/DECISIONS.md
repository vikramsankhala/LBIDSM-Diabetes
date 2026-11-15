# Provisional decisions (v0.3.1)

**Status:** working choices so the project can proceed. Research code, synthetic data only. Not clinically approved. Each decision below needs written sign-off in the study protocol before real data are used. The code values live in `src/lbidsm/protocol.py` and `src/lbidsm/eligibility.py`.

## 1. Qualification thresholds
**Choice:** at least 20 event-positive people, at least 50 independent episodes (30-minute separation), planned AUROC half-width at most 0.10, planning AUROC 0.75, assumed within-person similarity (ICC) 0.3.
**Why:** the half-width limit is the real requirement. A true AUROC near 0.75 with half-width 0.10 keeps the lower bound at 0.65, clearly above chance. The planning formula then fixes the counts: 20 people and 50 episodes over about 280 patient-days give 0.097 at ICC 0.3. 50 episodes is the lower end of the deck's figure, and 20 people gives the person-level bootstrap more than a handful of clusters. The repository's rule against a universal event count is respected: the numbers are derived from a precision target, not asserted.
**Sensitivity:** at ICC 0.1 the half-width is 0.087; at ICC 0.5 it is 0.107 and the gate fails. The ICC assumption must therefore be justified or estimated from development data.
**Limit:** 0.10 is wide enough to show a model beats chance, not to show it beats the M0 baseline. A comparison against M0 needs more events.

## 2. Severity weights
**Choice:** no single weight. The one harm modelled is a level 2 low, scored at 1, 3 and 10 times the value of one unit of benefit, and options are ranked by their worst case across the three.
**Why:** the weight is a value judgement that data cannot supply. A max-min ranking over a wide range means an option is preferred only if it holds up whichever weight clinicians and patients later choose, so the project need not wait for one number. Clinicians and patients should confirm or replace the range.

## 3. Eligibility rule table
**Choice:** fail closed. With no approved table, every option is ineligible. The table must carry a version, approver and date, and a missing patient value makes an option ineligible. The code contains no clinical rule.
**Why:** an eligibility rule is a clinical safety statement (for example a kidney-function limit). Writing one without clinicians would be inventing medicine. Failing closed means nothing reaches a clinician as a worthwhile option until a clinician has approved the rules that allow it.

## 4. Escalate before Abstain
**Choice:** keep the order. A verified reading below 54 mg/dL escalates even if data quality failed, and the message says the reading is unverified.
**Why:** the harms are asymmetric. An unneeded escalation costs a check; a suppressed escalation for a real low may cost far more. The message only tells a person to follow the established care plan and confirm the reading. It executes nothing. A clinical safety reviewer should still confirm this in writing.

## 5. Meaning of Review
**Choice:** keep the code's definition. Review means an eligible option has net utility above the minimum worth showing. Each option carries a flag: "interval excludes zero" or "interval crosses zero".
**Why:** the deck's wording reserves Review for the crossing-zero case. That leaves an option with clear benefit and no category to land in. Review is the only category that puts options in front of a clinician, and the repository forbids autonomous drug actions, so a clearly beneficial option must also go there. The flag preserves the deck's distinction without losing the option.

## Still open
Policy risk thresholds (`escalate_risk` 0.40, `max_risk_interval_width` 0.30, `review_min_utility` 0.02, `assess_risk` 0.15) are placeholders until calibration on a qualified cohort shows what they mean.
