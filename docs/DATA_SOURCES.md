# Data sources

**Status:** research project. No patient-level data are stored in this repository, and none may be committed (CI blocks it). Check each dataset's licence and data-use terms before use or redistribution. Facts below come from this repository's own documents unless marked otherwise.

## Used so far (public)

| Source | Role | What the repository records | Link |
|---|---|---|---|
| ShanghaiT2DM | Model development and benchmark | 100 people with type 2 diabetes, 3 to 14 days of CGM, about 15-minute readings, plus clinical, laboratory, medication and dietary records. Do not relabel type 1 subjects as type 2. | https://doi.org/10.6084/m9.figshare.c.6310860 · paper: https://www.nature.com/articles/s41597-023-01940-7 |
| CGMacros v1.0.0 (PhysioNet) | One independent feasibility test of a frozen model | 14 type 2 participants, 6,594 windows, 7 positive windows, 2 people with any low. Pipeline feasible; too few events for a reliable score. Licence CC BY-NC-SA 4.0 (non-commercial). See `docs/CGMACROS_FEASIBILITY_AND_NEXT_COHORT.md`. | https://doi.org/10.13026/3z8q-x658 |

## Candidates (access request needed; no patient-level data held)

| Source | What is published | Status | Link |
|---|---|---|---|
| Hypo-METRICS | Prospective study, nine centres, five European countries, about 10 weeks of blinded CGM | Not approved for benchmarking until data are obtained and pass the qualification gate. Data on reasonable request to the authors. | https://www.repository.cam.ac.uk/items/5e65514d-bd68-49fa-b19f-e64506279e41 · https://link.springer.com/article/10.1007/s00125-024-06233-1 |
| DiaGame | Eindhoven University of Technology dataset record: 60 participants (52 type 2, 8 type 1), about 14 days | Catalogue entry is not proof of a downloadable file. Access route unconfirmed. | https://research.tue.nl/p/en/datasets/the-diagame-study-lifestyle-and-blood-glucose |

Both are assessed in `docs/INDEPENDENT_T2D_COHORT_QUALIFICATION_REPORT.md`.

## Possible sources (not yet assessed here)

Collections that point to many public and controlled-access CGM datasets. Most contain type 1 diabetes, so they suit pipeline testing and a later type 1 extension better than the type 2 question. Each dataset's access terms must be read at its source.

- Glucose-ML, 10 datasets (OhioT1DM, T1DEXI, DiaTrend, ShanghaiT1DM, ShanghaiT2DM, CGMacros and others): https://arxiv.org/abs/2507.14077 · code: https://github.com/Augmented-Health-Lab/Glucose-ML-Project
- MetaboNet, 21 merged type 1 datasets with a public part and a data-use-agreement part: https://arxiv.org/abs/2601.11505

## Rule for adding a source

A new cohort is used for validation only after it passes the gate in `src/lbidsm/validation.py` (enough event-positive people and independent episodes, planned precision, no overlap with development data) under the thresholds in `docs/DECISIONS.md`. Add it here with its licence and access route first.
