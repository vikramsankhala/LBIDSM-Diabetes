# Data contract (research prototype)

## Implemented CSV

| Column | Required | Type | Constraint |
|---|---|---|---|
| timestamp | Yes | ISO 8601 with timezone | Parsed as UTC; no future leakage in feature windows |
| glucose_mg_dl | Yes | Numeric | Sanity filter 20–600 mg/dL; validity range is not a clinical diagnostic rule |

Exact duplicate timestamps are dropped after sorting, and invalid values are excluded. The descriptive metrics use *sample-and-hold* weighting over valid adjacent intervals at most 15 minutes long. Long gaps are omitted; this is not sensor coverage certification. A valid sensor trace and clinically adequate wear-time are separate concepts.

## Planned longitudinal entities

`patients(patient_id, consent_status, time_zone, phenotype_version)`

`observations(patient_id, observed_at_utc, ingested_at_utc, code, value, unit, source, quality_flag)`

`medications(patient_id, ingredient, dose, route, start_at, end_at, provenance)`

`conditions(patient_id, concept_code, onset_at, verified_at)`

`events(patient_id, event_type, event_start, event_end, adjudication_status)`

`decisions(patient_id, as_of_utc, model_version, rule_version, action_set, abstention_reason, reviewer_id)`

**Leakage restriction:** For a decision at time `t`, use only facts available by `t`; ingestion timestamps can differ from measurement times. No identifying data should be committed to this public repository.
