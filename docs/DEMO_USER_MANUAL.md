# Demo user manual

A step-by-step guide to running and reading `scripts/demo_research_pipeline.py`, on Windows PowerShell.

> **Status.** Research code, tested on synthetic data only. It is not a medical device, it is not clinically validated, and it must not be used for patient care. Every number the demo prints comes from made-up data. None is a finding.

## What the demo is

One script that runs all nine research areas in order on synthetic data, so you can see how the pieces fit: data checks, a frozen model, a gated outside test, a causal estimate, a genetics estimate, a ranking of options, a decision message, an access log and an evidence pack. It takes about 10 seconds on a typical laptop and needs no internet after installation.

## Before you start

| You need | Check with | Notes |
|---|---|---|
| Python 3.10 or newer | `python --version` | Tested on 3.10, 3.12 and 3.13 |
| Git | `git --version` | To copy the code |
| PowerShell | already installed | The commands below are for PowerShell |

## Part A. Install

**Step 1. Copy the code.**

```powershell
git clone https://github.com/vikramsankhala/LBIDSM-Diabetes.git
cd LBIDSM-Diabetes
```

**Step 2. Branch.** Pull request 1 has been merged, so the research modules are on `main` and you can skip this step. Only if you want the older feature branch, run the command below.

```powershell
git checkout feature/research-modules-v0.3
```

**Step 3. Create an isolated Python environment** so nothing else on your machine is changed.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Your prompt now starts with `(.venv)`. If PowerShell refuses to run the script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and repeat the second command.

**Step 4. Install the project.**

```powershell
python -m pip install -e ".[dev]"
```

**Step 5. Prove it works before you change anything.**

```powershell
python -m pytest -q
```

You should see `76 passed`. The count may grow in later versions. If any test fails, stop and see Troubleshooting.

## Part B. Run the demo

**Step 6. Run it.**

```powershell
python scripts/demo_research_pipeline.py --out demo_results
```

It prints nine numbered steps and creates a folder `demo_results` holding three files. The next section explains each printed line.

## Part C. Read the output, step by step

The numbers below are from the default run. The script uses fixed random seeds, so you should see the same numbers. The 16-character fingerprint and hash prefixes are the most likely to differ between versions.

### 1. L0 data integrity

```text
1. L0 data integrity
   subjects passing: 40 of 40
```

The script makes 40 synthetic people with 14 days of glucose readings and checks each one for gaps, impossible values and flat sensor lines. All 40 pass. In real data, failures are normal and the people who fail are removed before modelling.

### 2. Train, calibrate, freeze

```text
2. Train, calibrate, freeze (development cohort)
   fingerprint recorded BEFORE external data is opened: c3c3995eb5e31d67 ...
```

A small model (M2, nine inputs) learns to predict a glucose reading below 54 mg/dL in the next 60 minutes. It is calibrated on different people from those it learned from, then saved as `model_M2.json` with a 64-character fingerprint. The line says the fingerprint was recorded before any outside data was opened. That order is the point: it stops the model being adjusted after seeing the test.

### 3. External cohort: gate, then locked validation

```text
3. External cohort: qualification gate, then locked validation
   gate: {'positive_subjects': 29, 'independent_episodes': 171, 'planned_halfwidth': 0.069, 'passed': True}
   AUROC 0.778 (95% CI 0.756 to 0.797), patient-clustered; synthetic data
```

A second set of 30 synthetic people stands in for an outside study. The gate counts how many of them really had a low (29 people, 171 separate episodes) and plans how precise a score could be (half-width 0.069, which is under the 0.10 limit). It passes, so the locked model is scored. AUROC is a score from 0.5 (chance) to 1 (perfect); here 0.778 with a 95% interval. The interval resamples whole people, not single windows.

### 4. Patient-specific causal effect

```text
4. Patient-specific causal effect (synthetic trial)
   ARR 0.053, 95% CI 0.027 to 0.079; balance_ok=True, positivity_ok=True, E-value 2.19
```

A synthetic trial of 3,000 people where treatment lowers risk by a known amount. After weighting to make treated and untreated groups comparable, the absolute risk reduction (ARR) is 0.053 (5.3 percentage points) with a 95% interval. `balance_ok` and `positivity_ok` are the two safety checks, and both are true. The E-value says how strong an unmeasured confounder would have to be to explain the result away.

### 5. Genetics (Mendelian randomisation)

```text
5. Genetics: Mendelian randomisation on synthetic summary statistics
   IVW 0.349 Egger 0.377 warnings: []
```

Sixty synthetic gene variants, built so the true effect is 0.4. Two methods estimate it: IVW (0.349) and MR-Egger (0.377). Close agreement and an empty warnings list mean no sign of pleiotropy in this synthetic case. Real data would rarely be this clean.

### 6. Optimised treatments

```text
6. Optimised treatments: robust research ranking
   option_B: worst-case utility 0.059, eligible=True
   option_A: worst-case utility -0.494, eligible=True
   option_C: worst-case utility 0.198, eligible=False
```

Three made-up options are scored as benefit minus harm, under three views of how bad a low is (weights 1, 3 and 10). Each option is ranked by its worst score. B holds up. A has a larger benefit but its harm is large, so it fails under the strict view. C has the biggest benefit but is excluded by the demo rule table, so it is listed last. The names and numbers are invented.

### 7. L7 decision policy

```text
7. L7 decision policy
   stable      -> Monitor
   benefit     -> Review
   bad sensor  -> Abstain
   low reading -> Escalate
```

Four made-up situations, one per output. A stable person: Monitor. A person with an eligible worthwhile option: Review. A person whose data failed quality checks: Abstain (no output, a human looks). A reading of 48 mg/dL: Escalate, even though other things are unusual. A fifth output, Assess, appears when risk may be rising but nothing else applies. Nothing here doses or adjusts treatment.

### 8. Access control and audit

```text
8. Access control and audit
   attempts logged: 2 | chain intact: True
```

Two access attempts are made. The first (restricted data from a laptop) is refused; the second (synthetic data) is allowed. Both are logged in a chain where each entry holds the previous entry's hash. `chain intact: True` means no entry has been altered. Open `demo_results\audit_log.jsonl` to see the refusal and its reason.

### 9. Regulatory evidence pack

```text
9. Regulatory evidence pack
   pack hash: eb4edadb2f399dd8 ...
   release blockers (expected for a research demo):
    - no written intended-use statement
    - no hashed data manifest
    - no completed independent external validation
    - TRIPOD+AI checklist not loaded
    - local regulatory review not documented
```

The pack gathers the model fingerprint, gate result, test coverage of each requirement and more. The five blockers are correct and expected. They are the software saying it is not ready for any clinical claim. A demo that listed no blockers would be wrong.

## Part D. Look at the three output files

```powershell
Get-Content demo_results\model_M2.json | Select-Object -First 20
Get-Content demo_results\audit_log.jsonl
Get-Content demo_results\evidence_pack.json | Select-String "release_blockers" -Context 0,8
```

| File | What it is |
|---|---|
| `model_M2.json` | The whole model as readable numbers: input names, weights, calibration, fingerprint |
| `audit_log.jsonl` | The two access attempts, one per line, each chained to the previous |
| `evidence_pack.json` | The proof file, ending in the list of release blockers |

## Part E. Try things

Each experiment changes one thing so you can see what it does. Run the demo again after each.

1. **Make the outside cohort too sparse.** This copies the situation of the real CGMacros feasibility run.

   ```powershell
   python scripts/demo_research_pipeline.py --out demo_sparse --sparse-external
   ```

   Step 3 now reports 2 event-positive people, a planned half-width of 0.395, `passed: False` and `inconclusive` with three reasons, and no AUROC. This is the gate refusing to give a number it cannot support. Steps 4 to 9 are unchanged.

2. **Run faster or slower.** `--bootstrap 50` runs step 3 with fewer resamples (the whole demo took about 5 seconds instead of 10 here, with rougher intervals); `--bootstrap 1000` is slower and smoother. The default is 300.

   ```powershell
   python scripts/demo_research_pipeline.py --out demo_fast --bootstrap 50
   ```

3. **Change the harm weights.** Open `src\lbidsm\protocol.py`, find `HARM_WEIGHT_SCENARIOS` and change `(1.0, 3.0, 10.0)` to `(0.5, 1.0, 2.0)`. Rerun and watch step 6: option A's worst-case utility rises from -0.494 to about -0.019 and option B's from 0.059 to 0.075, because a low now counts for much less. Change it back afterwards with `git checkout src\lbidsm\protocol.py`.

4. **Change a policy threshold.** In the same file, change `review_min_utility=0.02` to `0.10` in `POLICY` and rerun. In step 7 the "benefit" person moves from Review to Monitor, because option B's utility is no longer worth showing a clinician. The policy tests still pass, since they supply their own thresholds. Undo with `git checkout src\lbidsm\protocol.py`. The thresholds are provisional placeholders until a clinician signs them off.

5. **Break the model on purpose.** Open `demo_results\model_M2.json`, change one number under `coef`, then run `python -m pytest tests\test_model_bundle.py -q`. The tamper test shows that a changed file is refused ("Model file was altered").

6. **Check the repository guard.**

   ```powershell
   python scripts/check_no_patient_data.py
   ```

   It should say `No patient-level files found.` It is the check that keeps real patient data out of the public repository.

## Worked results: the demo explained with its own sample data

This section explains what the demo's numbers mean, using the synthetic sample data. Everything here is reproducible: `python scripts/worked_results.py` prints every number below, and `data/sample/` holds real rows to show on screen. Numbers marked (extra) are not printed by the demo itself. They come from re-running the same seeded code.

### 1. The sample data

- The development cohort has 161,280 rows: 40 people times 4,032 readings (14 days of one reading every 5 minutes).
- The first row is person `S000`, 2026-01-01 00:00 UTC, 162.5 mg/dL. `S000` has 57 readings below 54 mg/dL.
- All 40 people pass the data-quality gate, so the demo prints "40 of 40". The generator adds sensor noise, because the first version produced perfectly flat dips and the gate rightly rejected most people.
- To show it live, open `data\sample\synthetic_cgm_sample.csv` (S000 to S004, 20,160 rows).

### 2. Turning readings into model inputs

Cutting the readings into hour-long windows gives 26,720 windows. Only 2.65% are followed by a low in the next hour, and 39 of the 40 people have at least one. Two windows from `S000`:

| Input | Window followed by a low | Window with no low |
|---|---|---|
| `last_glucose` | 156.1 | 159.6 |
| `mean_60` | 142.4 | 159.8 |
| `min_60` | 131.7 | 149.1 |
| `slope_15` | +0.80 | -0.46 |
| Outcome | 1 | 0 |
| Risk given by the model | 1.5% | 1.6% |

The model gives these two windows almost the same risk. That is realistic: the low in the first window cannot be seen in its readings. A single window is close to unpredictable, so AUROC is the fair measure. It asks whether, across many windows, the windows followed by a low are ranked higher. Twenty such windows, with all nine inputs, are in `data\sample\example_windows.csv`.

The model learned from 24 people (16,032 windows, 434 events) and was calibrated on 8 different people.

### 3. The outside test

- The outside cohort has 30 new people: 20,040 windows and 523 events (2.6%).
- The gate counted 29 event-positive people and 171 separate episodes, so it passed and the locked model was scored: AUROC 0.778, 95% interval 0.756 to 0.797.
- (extra) The average predicted risk is 0.334 for windows followed by a low and 0.017 for the others.

(extra) The outside windows split into five equal risk groups:

| Risk group | Predicted | Observed |
|---|---|---|
| Lowest four groups | about 1.5% to 1.7% | about 1.1% to 1.2% |
| Highest group | 6.4% | 8.4% |

- **Ranking works.** The top group has about 7 times the low rate of the others.
- **Calibration is rough.** It overstates the bottom groups and understates the top one. That is why the full validation reports calibration separately from AUROC.
- **Alerts (extra).** At a risk cut-off of 0.05 the model alerts on 1.5% of windows (305 alerts), catches 255 of the 523 lows (about half), and 84% of its alerts are followed by a real low. At 0.10 it gives 263 alerts, catches 241, and 92% are followed by a low.
- **Caveat.** The generator is simple and overlapping windows are correlated. These figures flatter the model. Real cohorts will be harder.

### 4. Causal effect, genetics and ranking, checked against known truths

- **Causal effect.** The synthetic trial was built so the true average risk reduction is 0.072 (extra). The demo estimates 0.053 with interval 0.027 to 0.079, which contains the truth. It is lower than the truth, so one run can miss by a bit. Both safety checks pass, and the E-value of 2.19 means a hidden confounder would have to be fairly strong to explain the result away.
- **Genetics.** The true effect built into the variants is 0.4. IVW gives 0.349 and MR-Egger gives 0.377. Both are somewhat low, they agree with each other, and there are no warnings.
- **Ranking, by hand.** Option B: 0.08 minus 10 times 0.002 gives 0.060 (the demo shows 0.059). Option A: 0.10 minus 10 times 0.06 gives -0.50 (the demo shows -0.494). Under the strictest view of lows, A's harm outweighs its benefit. Option C has benefit 0.20 and no harms, but it is ineligible, so it is listed last.

### 5. Decisions, access and evidence

- **Stable person.** The risk upper bound is 0.06, below 0.15, so the output is Monitor.
- **Benefit case.** Option B's utility of 0.059 is above the 0.02 minimum, so the output is Review.
- **Bad sensor.** Abstain.
- **Reading of 48 mg/dL.** Escalate, because 48 is below 54.
- **Audit log.** The first attempt (restricted data from a laptop) is refused and the second (synthetic data) is allowed. The chain is intact.
- **Evidence pack.** The five release blockers are the software correctly saying it is not ready for clinical use.

### 6. The sparse run

With `--sparse-external` the outside cohort has 2 event-positive people and a planned half-width of 0.395. The gate fails and no AUROC is produced. This is the contrast to show after the main run.

### A suggested 30-minute lecture flow

| Minutes | What to do |
|---|---|
| 0 to 5 | Open `data\sample\synthetic_cgm_sample.csv`. Explain one row and what the 54 mg/dL line means |
| 5 to 10 | Open `data\sample\example_windows.csv`. Show a window followed by a low and one that is not, with near-equal risks |
| 10 to 18 | Run the demo and walk through its nine steps with Part C above |
| 18 to 24 | Show the calibration table and the alert numbers (`python scripts\worked_results.py`) |
| 24 to 28 | Run `--sparse-external` and show the gate refusing a number |
| 28 to 30 | Open the evidence pack and read the five release blockers aloud |

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `python` is not recognised | Install Python 3.10 or newer from python.org and tick "Add to PATH", then reopen PowerShell |
| `Activate.ps1 cannot be loaded` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once |
| `ModuleNotFoundError: lbidsm` | The environment is not active or step 4 was skipped. Activate `.venv` and run the install again |
| `error: pathspec 'feature/research-modules-v0.3' did not match` | The branch was merged and removed. Skip step 2 |
| Tests show collection errors | Same cause as the previous but one: run `python -m pip install -e ".[dev]"` inside the active environment |
| The demo prints different numbers | You may be on a different version. Check `git log --oneline -1` and the version in `pyproject.toml` (0.3.1 at the time of writing) |
| Step 9 lists dozens of "requirements without a test" | You ran it from another folder, so it could not find `tests`. Run it from the repository's top folder |

## What the demo does not show

- No real patient data and no real cohort. Every number is synthetic.
- No clinical accuracy. The AUROC in step 3 is a property of made-up data.
- No treatment advice. The decision messages are for a human to read, and every one ends "No treatment action is executed by this software."
- None of the not-built items: time-varying causal treatment, the M3 state-space model, polygenic scores, adjudicated event labels and the prospective study.

## Where to go next

- `docs/RESEARCH_MODULES.md`: a two-page map of every module.
- `docs/DECISIONS.md`: why the provisional values were chosen.
- `docs/DATA_SOURCES.md`: real datasets and their access status.
- `data/sample/`: the synthetic teaching sample used in Worked results.
- The proposal document, Part VI: a file-by-file guide to the code.
