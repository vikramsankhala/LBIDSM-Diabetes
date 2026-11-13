# Independent T2D CGM Cohort Qualification Report

**Assessment date:** 2026-11-13  
**Project:** LBIDSM-Diabetes  
**Purpose:** Source qualification and access/provenance review only. **Not a performance benchmark.**

## Decision

**Priority 1: Hypo-METRICS — CONDITIONAL / DATA ACCESS REQUIRED.**  
**Priority 2: DiaGame — CONDITIONAL / DATA ACCESS AND EVENT FEASIBILITY REQUIRED.**  
**No cohort is currently qualified for a new locked-model external-validation comparison.**

Evidence labels below:
- **PUBLISHED:** a paper or institutional catalogue establishes a claim, not access to raw data.
- **VERIFIED DOWNLOAD:** patient-level CGM files have actually been acquired, inspected and hashed by this project.
- **UNRESOLVED:** not established; do not assume availability or suitability.

## Candidate A — Hypo-METRICS

**Published evidence:** Prospective observational study at nine clinical centers across five European countries; approximately 10 weeks of blinded CGM monitoring, using a modified Abbott FreeStyle Libre 2 sensor collecting at 5-minute intervals. The primary relationship paper reports 321 participants with insulin-treated type 2 diabetes and median sensor-detected episodes <54 mg/dL of 0.2 per week (IQR 0.0–0.5). A subsequent CKD subgroup analysis reports 313 T2D participants; these are overlapping study analyses, **not independent cohorts**. Participants were selected for prior hypoglycemia, creating spectrum/selection-bias concerns.

**Verified downloadable patient-level data:** NONE. We have verified published descriptions, not acquired raw patient records.

**Access:** The CKD analysis states: data supporting the findings available from the corresponding author upon reasonable request. Need documented data-use permission, transfer process, data dictionary, sensor export provenance, anonymization restrictions and ability to publish aggregate results.

**Open questions:** Can an approved external investigator receive deidentified subject-level native 5-minute CGM exports and corresponding diabetes type, therapy and sensor metadata? How many distinct <54 mg/dL episodes and episode-positive patients exist in the shareable T2D subset under our prespecified episode rule? Are timestamps device-native, shifted, interpolated, rounded or otherwise processed? Can they be used for external AI benchmarking and reproducible aggregate publication?

**Decision:** Prioritize an investigator data-access inquiry; **not approved for benchmarking**.

Sources:
- https://www.repository.cam.ac.uk/items/5e65514d-bd68-49fa-b19f-e64506279e41
- https://link.springer.com/article/10.1007/s00125-024-06233-1
- https://pmc.ncbi.nlm.nih.gov/articles/PMC13646342/

## Candidate B — DiaGame

**Published evidence:** Eindhoven University of Technology dataset record, made available January 24, 2026, describes 60 participants (52 T2D and 8 T1D), approximately 14 days of interstitial glucose monitoring using FreeStyle Libre Pro IQ and multimodal records. A study publication reports 77,683 CGM measurements across the whole cohort, with nominal 15-minute glucose measurements.

**Verified downloadable patient-level data:** NONE. An institutional dataset catalogue page exists; its presence is **not proof of an accessible patient-level download**. A preprint explicitly says data available upon reasonable request to the authors.

**Open questions:** Which access portal or investigator provides actual deidentified CGM records? Are raw sensor timestamps and readings retained or resampled? What is the T2D-specific count of independently defined <54 mg/dL episodes and event-positive patients? Are dataset license and consent compatible with external predictive benchmarking?

**Decision:** Secondary access inquiry; **not approved for benchmarking**. Do not presume sufficient hypoglycemia events from overall CGM sample count.

Sources:
- https://research.tue.nl/p/en/datasets/the-diagame-study-lifestyle-and-blood-glucose
- https://catalogus.healthdata.nl/en/datasets/948f97ef-a0ff-458f-a1bb-b65d3c8ab0fd
- https://journals.sagepub.com/doi/10.1177/29986702261416447
- https://www.medrxiv.org/content/10.1101/2024.12.13.24318201v1

## Qualification gate — mandatory before evaluation

1. **Access:** obtain actual patient-level CGM files under valid permission and document legal/ethical reuse restrictions.
2. **Independence:** verify no participant overlap with ShanghaiT2DM, CGMacros or model-development data.
3. **T2D phenotype:** documented clinical T2D classification, participant inclusion/exclusion and therapies; describe any hypoglycemia-enriched recruitment.
4. **Native CGM provenance:** sensor manufacturer/model, nominal cadence, exact native timestamps, timezone, date shifting, interpolation, duplicates, missingness, gaps, sensor warmup and plausibility. Hash raw files and version acquisition scripts.
5. **Event feasibility:** prespecify level-2 CGM hypoglycemia (<54 mg/dL), minimum duration/separation, and event onset; report independent episodes, patients with episodes, patient-days and per-patient distribution. Do not equate overlapping positive prediction windows with independent episodes.
6. **Statistical adequacy:** perform a prespecified precision/power assessment based on *event-positive patients and independent episodes*, and patient-clustered uncertainty; do not invent a universal minimum count.
7. **Frozen transfer:** verify Shanghai-only preprocessing, weights, calibration and thresholds are locked before examining external outcomes; avoid threshold or endpoint tuning.
8. **Approval:** sign off on a dated cohort-qualification memo before running AUROC, AUPRC, calibration or alert-level model comparisons.

**Current gate outcome: FAIL (access/provenance/event adequacy unresolved) for both candidates.**

## Next action

Send a targeted data-access inquiry to the Hypo-METRICS corresponding author and, in parallel, a DiaGame access inquiry to the institutional dataset contact. Request a deidentified data dictionary, native-CGM sampling details, terms of use and *aggregate feasibility counts* before negotiating full data transfer. No patient-level data or individual identifiers should be placed in public GitHub artifacts.

## Proposed Hypo-METRICS inquiry

**Subject:** Research Data Access Request — Hypo-METRICS T2D CGM Cohort (Research Proposal Attached)

Dear Hypo-METRICS Research Team,

I am writing to enquire about access to deidentified participant-level continuous glucose monitoring (CGM) data from the Hypo-METRICS study for independent academic research.

My project, LBIDSM-Diabetes, is developing a mathematical and AI-based research framework for diabetes intervention decision support. I have completed retrospective experiments using ShanghaiT2DM and a feasibility evaluation using CGMacros. The latter demonstrated external evaluation workflow feasibility but did not establish reliable predictive performance because of insufficient observed hypoglycemia events.

My immediate research objective is to independently evaluate frozen prediction models for glucose readings below 54 mg/dL within the subsequent 60 minutes, without retraining, recalibration or outcome-driven model selection on the external cohort.

I would be grateful for guidance on:

1. Availability of deidentified participant-level CGM time series for the type 2 diabetes cohort.
2. Availability of original device-native glucose measurements and timestamps, rather than interpolated or resampled data.
3. Aggregate counts of independent hypoglycemia episodes below 54 mg/dL and the number of participants experiencing these episodes.
4. Availability of relevant clinical metadata, including diabetes classification, insulin treatment and CGM device characteristics.
5. Applicable ethical approvals, data-use agreements, access procedures and publication restrictions.

For your consideration, I have attached a formal research proposal outlining the study objectives, proposed methodology and intended data governance safeguards.

I am willing to complete the applicable ethics and institutional approval processes, enter into an appropriate data-use agreement, and implement the data security and confidentiality requirements specified by your institution before receiving participant-level data. No patient-level information would be published or uploaded to my public project repository.

My project repository is available at:

https://github.com/vikramsankhala/LBIDSM-Diabetes

Thank you for considering my request. I would appreciate your guidance on the appropriate process and contact person.

Kind regards,  
**Vikram Singh Sankhala**  
LBIDSM-Diabetes Research Project

**Attachment:** Hypo-METRICS Research Data Access and Independent External Validation Proposal (PDF)

## Proposed DiaGame inquiry

Subject: DiaGame participant-level CGM data access and sensor provenance

Dear DiaGame data custodians,

I am assessing independent type 2 diabetes CGM cohorts for a non-clinical external-validation study of glucose <54 mg/dL prediction within 60 minutes. Your institutional dataset record describes 52 T2D participants with FreeStyle Libre Pro IQ monitoring.

Could you clarify whether deidentified participant-level CGM data can be accessed, the required authorization process and reuse license, and whether timestamps and glucose measurements are native sensor exports or interpolated/resampled values? If available, could you share aggregate counts of independent <54 mg/dL episodes and participants with such episodes in the T2D subset, plus the data dictionary and acquisition documentation?

No model evaluation would be performed until cohort independence, data provenance and event adequacy are established.

Kind regards,  
Vikram Singh Sankhala
