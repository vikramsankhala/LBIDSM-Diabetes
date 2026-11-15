# Synthetic teaching sample

**Synthetic data only. No real person is in these files.** They exist so the demo's worked results (see `docs/DEMO_USER_MANUAL.md`, "Worked results") can be traced to real rows, for example in a lecture.

| File | Contents |
|---|---|
| `synthetic_cgm_sample.csv` | Five synthetic people (S000 to S004), 14 days each, one reading every 5 minutes (20,160 rows). Columns: `subject_id`, `timestamp` (UTC), `glucose_mg_dl` |
| `example_windows.csv` | 20 hour-long windows from S000: the nine model inputs, the outcome `event_lt54` (a reading below 54 mg/dL in the next 60 minutes) and `model_M2_risk`, the risk the demo's frozen M2 model gives. Ten windows are followed by a low and ten are not |

They are the first five people of the demo's 40-person development cohort (seed 3). The full cohort is generated in memory by `scripts/demo_research_pipeline.py` and is not stored.

Regenerate or verify them:

```powershell
python scripts/make_sample_data.py           # write the files
python scripts/make_sample_data.py --check   # fail if the committed files differ
python scripts/worked_results.py             # reproduce every number in the manual's Worked results
```

The patient-data guard (`scripts/check_no_patient_data.py`) allows these two files by exact name and only while every `subject_id` looks synthetic (`S` and three digits). Never save real data under these names.
