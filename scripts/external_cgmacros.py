"""Locked-model external validation: ShanghaiT2DM -> CGMacros T2DM.

The official CGMacros archive is public but large (~627 MB). All patient-level
data stay on the ephemeral GitHub runner. Do not treat interpolated 1-minute
readings as independent CGM measurements.
"""
import argparse
import hashlib
import io
import json
import re
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from lbidsm.prediction import FEATURES_BASIC, FEATURES_CGM, make_examples
from scripts.expanded_validation import scores, calibration_summary, cluster_bootstrap, episodes_and_alerts

ROOT = "https://physionet.org/files/cgmacros/1.0.0/"
ARCHIVE = "CGMacros_dateshifted365.zip"
MODELS = {"M0_current_glucose":["last_glucose"],
          "M1_glucose_slope":FEATURES_BASIC, "M2_cgm_history":FEATURES_CGM}

def download(out):
    out.mkdir(parents=True, exist_ok=True)
    path = out / ARCHIVE
    urllib.request.urlretrieve(ROOT + ARCHIVE, path)
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = urllib.request.urlopen(ROOT+"SHA256SUMS.txt",timeout=60).read().decode()
    matching = [line for line in manifest.splitlines() if ARCHIVE in line]
    if not matching:
        raise RuntimeError("Official checksum manifest does not identify archive")
    expected = matching[0].split()[0]
    if checksum.lower() != expected.lower():
        raise RuntimeError("CGMacros archive SHA-256 differs from official PhysioNet manifest")
    return path, checksum

def choose_t2dm(bio):
    """Select by explicit phenotype label if present; otherwise published HbA1c >6.4.

    HbA1c selection is a study-specific cohort proxy, not an individual diagnosis.
    Fail rather than silently include non-T2DM participants.
    """
    cols = {str(c).strip().lower():c for c in bio.columns}
    idcol = next((cols[k] for k in ("id","participant id","participant_id","subject id","subject_id","participant","subject") if k in cols),None)
    if idcol is None:
        raise ValueError("bio.csv participant identifier column not recognized: "+str(list(bio.columns)))
    phenotype = next((cols[k] for k in ("diabetes status","diabetes_status","group","diabetes","status") if k in cols),None)
    if phenotype is not None:
        value = bio[phenotype].astype(str).str.strip().str.lower()
        mask = value.isin(["t2d","t2dm","type 2 diabetes","type ii diabetes"])
        if not mask.any():
            raise ValueError("Phenotype column found but no explicit T2DM labels; review bio.csv coding")
        rule = "explicit phenotype label"
    else:
        a1c = next((cols[k] for k in ("a1c pdl (lab)","hba1c","a1c","hba1c (%)") if k in cols),None)
        if a1c is None:
            raise ValueError("No verified T2DM phenotype or HbA1c field")
        mask = pd.to_numeric(bio[a1c],errors="coerce") > 6.4
        rule = "study-defined HbA1c >6.4% proxy; NOT independently verified diagnosis"
    ids = set()
    for v in bio.loc[mask,idcol]:
        m = re.search(r"(\d+)",str(v))
        if m: ids.add(int(m.group(1)))
    if not ids:
        raise ValueError("No eligible T2DM identifiers")
    return ids,rule

def harmonize(archive, sensor="Dexcom GL"):
    with zipfile.ZipFile(archive) as z:
        csvs = [n for n in z.namelist() if n.lower().endswith(".csv") and not n.startswith("__MACOSX/")]
        bio_files = [n for n in csvs if Path(n).name.lower()=="bio.csv"]
        if len(bio_files)!=1: raise ValueError("Expected exactly one bio.csv; found "+str(bio_files))
        bio = pd.read_csv(io.BytesIO(z.read(bio_files[0])),encoding="utf-8-sig")
        ids,rule = choose_t2dm(bio)
        tables=[]
        audit=[]
        for name in csvs:
            match = re.search(r"cgmacros[-_]?0*(\d+)\.csv$",Path(name).name,re.I)
            if not match: continue
            pid=int(match.group(1))
            if pid not in ids: continue
            frame=pd.read_csv(io.BytesIO(z.read(name)),encoding="utf-8-sig",low_memory=False)
            columns={str(c).strip().lower():c for c in frame.columns}
            if "timestamp" not in columns or sensor.lower() not in columns:
                audit.append({"file":name,"status":"missing required columns","columns":list(frame.columns)})
                continue
            ts=pd.to_datetime(frame[columns["timestamp"]],errors="coerce",utc=True)
            glucose=pd.to_numeric(frame[columns[sensor.lower()]],errors="coerce")
            d=pd.DataFrame({"subject_id":str(pid),"timestamp":ts,"glucose_mg_dl":glucose}).dropna()
            d=d[d.glucose_mg_dl.between(40,400)].sort_values("timestamp").drop_duplicates("timestamp")
            # Official one-minute table is interpolated; select observed-grid
            # candidate readings only. This is NOT guaranteed to recover raw sensor samples.
            # Anchor each subject to its first timestamp; sample every 5 or 15 minutes.
            period=5 if sensor=="Dexcom GL" else 15
            if len(d):
                delta=(d.timestamp-d.timestamp.iloc[0]).dt.total_seconds()/60
                d=d[np.isclose(delta%period,0,atol=0.01)]
            tables.append(d)
            audit.append({"file":name,"status":"included","sensor":sensor,"rows_after_grid":len(d)})
        if not tables: raise ValueError("No eligible CGMacros sensor files: "+json.dumps(audit[:10]))
        result=pd.concat(tables,ignore_index=True)
        if result.subject_id.nunique()<2: raise ValueError("Fewer than two external subjects")
        return result,{"selection_rule":rule,"eligible_ids_in_bio":len(ids),
                       "eligible_ids_with_sensor":int(result.subject_id.nunique()),
                       "sensor":sensor,"sensor_grid_note":"1-minute interpolated table subsampled to nominal sensor interval; phase may differ from true sampling times",
                       "files":audit}

def frozen_train(shanghai,seed=42):
    """Train on Shanghai only; calibrate on Shanghai only; no external refitting."""
    from lbidsm.prediction import cohort_split
    ex=make_examples(shanghai)
    train,cal,_=tuple(cohort_split(ex,seed))
    frozen={}
    for name,cols in MODELS.items():
        base=make_pipeline(StandardScaler(),LogisticRegression(max_iter=1000,random_state=seed))
        base.fit(train[cols],train.event_lt54)
        pc=base.predict_proba(cal[cols])[:,1]
        calibrator=LogisticRegression(max_iter=1000,random_state=seed)
        calibrator.fit(pc.reshape(-1,1),cal.event_lt54)
        frozen[name]=(base,calibrator,cols)
    return frozen,{"training_subjects":int(train.subject_id.nunique()),
                   "calibration_subjects":int(cal.subject_id.nunique()),
                   "train_events":int(train.event_lt54.sum()),
                   "calibration_events":int(cal.event_lt54.sum())}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--shanghai",required=True)
    ap.add_argument("--out",default="benchmark_results/external")
    ap.add_argument("--sensor",choices=["Dexcom GL","Libre GL"],default="Dexcom GL")
    ap.add_argument("--bootstrap",type=int,default=1000)
    a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    archive,digest=download(out)
    external,audit=harmonize(archive,a.sensor)
    frozen,training=frozen_train(pd.read_csv(a.shanghai))
    ex=make_examples(external)
    if ex.empty: raise ValueError("No eligible external prediction windows")
    meta={"dataset":"CGMacros v1.0.0","doi":"10.13026/3z8q-x658",
          "official_archive_sha256":digest, "external_subjects":int(ex.subject_id.nunique()),
          "external_windows":len(ex),"external_positive_windows":int(ex.event_lt54.sum()),
          "external_positive_subjects":int(ex.loc[ex.event_lt54==1,"subject_id"].nunique()),
          "source":audit,"frozen_training":training,
          "external_outcome_used_for_training_or_calibration":False}
    (out/"eligibility.json").write_text(json.dumps(meta,indent=2))
    if ex.event_lt54.nunique()<2:
        (out/"INCONCLUSIVE.txt").write_text("External cohort has only one event class. AUROC/AUPRC/calibration not estimable; no validation claim.\n")
        print(json.dumps(meta,indent=2))
        return
    preds={}
    for name,(base,cal,cols) in frozen.items():
        raw=base.predict_proba(ex[cols])[:,1]
        preds[name]=np.clip(cal.predict_proba(raw.reshape(-1,1))[:,1],1e-7,1-1e-7)
    rows=[]
    curves={}
    for name,p in preds.items():
        try: c=calibration_summary(ex.event_lt54,p)
        except Exception as err: c={"intercept":None,"slope":None,"curve":[],"error":str(err)}
        rows.append({"model":name,**scores(ex.event_lt54,p),"calibration_intercept":c["intercept"],"calibration_slope":c["slope"]})
        curves[name]=c
    pd.DataFrame(rows).to_csv(out/"external_metrics.csv",index=False)
    (out/"external_calibration.json").write_text(json.dumps(curves,indent=2))
    try:
        boot=cluster_bootstrap(ex,preds,repetitions=a.bootstrap)
        intervals=[{"statistic":col,"low":float(boot[col].quantile(.025)),"high":float(boot[col].quantile(.975)),"valid_resamples":len(boot)}
                   for col in boot.columns if col!="bootstrap"]
        pd.DataFrame(intervals).to_csv(out/"external_cluster_intervals.csv",index=False)
    except ValueError as err:
        (out/"bootstrap_inconclusive.txt").write_text(str(err))
    alerts=episodes_and_alerts(external,ex,preds)
    (out/"external_event_alert_analysis.json").write_text(json.dumps(alerts,indent=2))
    print(json.dumps(meta,indent=2))
    print(pd.DataFrame(rows).to_string(index=False))

if __name__=="__main__":
    main()
