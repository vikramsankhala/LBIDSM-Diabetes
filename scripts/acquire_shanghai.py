"""Fetch and harmonize the original Figshare ShanghaiT2DM dataset.

Research only. Does not publish patient-level data. Dataset and source metadata
are stored locally as an audit trail. No implicit assumptions about glucose units.
"""
import argparse, hashlib, io, json, re, zipfile
from pathlib import Path
import pandas as pd
import requests

API = "https://api.figshare.com/v2/articles/"
ARTICLES = [21600933, 20444397, 20425518]

def sha256(b):
    return hashlib.sha256(b).hexdigest()

def acquire(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    errors = []
    for article_id in ARTICLES:
        try:
            r = requests.get(API + str(article_id), timeout=60)
            r.raise_for_status()
            meta = r.json()
            candidates = [f for f in meta.get("files", []) if f["name"].lower().endswith(".zip")]
            if not candidates:
                errors.append(f"{article_id}: no zip in {[f['name'] for f in meta.get('files', [])]}")
                continue
            for file in candidates:
                url = file.get("download_url")
                if not url:
                    continue
                r = requests.get(url, timeout=240)
                r.raise_for_status()
                raw = r.content
                if not zipfile.is_zipfile(io.BytesIO(raw)):
                    errors.append(f"{article_id}: {file['name']} not a ZIP")
                    continue
                archive = out / "source.zip"
                archive.write_bytes(raw)
                provenance = {
                    "article_id": article_id, "article_doi": meta.get("doi"),
                    "article_title": meta.get("title"), "article_url": meta.get("url"),
                    "file_name": file["name"], "download_url": url,
                    "source_zip_sha256": sha256(raw), "zip_bytes": len(raw),
                    "license": meta.get("license"),
                }
                (out / "source_provenance.json").write_text(json.dumps(provenance, indent=2))
                return archive, provenance
        except Exception as exc:
            errors.append(f"{article_id}: {type(exc).__name__}: {exc}")
    raise RuntimeError("Unable to download official ZIP: " + "; ".join(errors))

def harmonize(archive, out, unit="mg/dL"):
    out = Path(out)
    rows = []
    manifest = []
    with zipfile.ZipFile(archive) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        (out / "archive_inventory.json").write_text(json.dumps(names, indent=2))
        # Require T2DM directory name; never silently mix T1DM and T2DM.
        candidates = [n for n in names if not n.startswith("__MACOSX/") and not Path(n).name.startswith("._") and re.search(r"shanghai[_ -]?t2dm/", n, re.I) and n.lower().endswith((".csv", ".xlsx", ".xls"))]
        if not candidates:
            raise RuntimeError("No identifiable Shanghai_T2DM CGM files. Inventory saved; inspect manually.")
        for name in candidates:
            try:
                data = z.read(name)
                if name.lower().endswith(".csv"):
                    df = pd.read_csv(io.BytesIO(data))
                else:
                    df = pd.read_excel(io.BytesIO(data))
                lower = {str(c).strip().lower(): c for c in df.columns}
                date_col = next((lower[k] for k in ("date", "timestamp", "time", "datetime") if k in lower), None)
                glucose_col = next((lower[k] for k in ("cgm (mg / dl)", "cgm (mg/dl)", "cgm", "glucose", "glucose_mg_dl") if k in lower), None)
                if date_col is None or glucose_col is None:
                    manifest.append({"name": name, "status": "skipped_no_date_cgm_columns", "columns": list(map(str, df.columns))})
                    continue
                # File names include patient ID, period and date. The patient ID is
                # the first token, not the entire file stem, preventing repeat-visit leakage.
                base = Path(name).stem
                patient_id = base.split("_")[0]
                if not re.fullmatch(r"\d+", patient_id):
                    manifest.append({"name": name, "status": "skipped_unrecognized_patient_id", "columns": list(map(str, df.columns))})
                    continue
                t = pd.to_datetime(df[date_col], errors="coerce")
                if t.dt.tz is None:
                    t = t.dt.tz_localize("Asia/Shanghai", ambiguous="NaT", nonexistent="NaT")
                t = t.dt.tz_convert("UTC")
                g = pd.to_numeric(df[glucose_col], errors="coerce")
                if "mg" in str(glucose_col).lower() and unit != "mg/dL":
                    raise ValueError("Source column explicitly says mg/dL; refusing mmol/L conversion")
                if unit == "mmol/L":
                    g = g * 18.0182
                elif unit != "mg/dL":
                    raise ValueError("unit must be mmol/L or mg/dL")
                clean = pd.DataFrame({"subject_id": patient_id, "timestamp": t, "glucose_mg_dl": g}).dropna()
                clean = clean[clean.glucose_mg_dl.between(20, 600)]
                rows.append(clean)
                manifest.append({"name": name, "status": "included", "patient_id": patient_id, "rows": len(clean), "columns": list(map(str, df.columns))})
            except Exception as exc:
                manifest.append({"name": name, "status": "error", "error": str(exc)})
    (out / "harmonization_manifest.json").write_text(json.dumps(manifest, indent=2))
    if not rows:
        raise RuntimeError("No usable CGM tables. Archive inventory: " + json.dumps(names[:80]) + "; manifest: " + json.dumps(manifest[:30]))
    combined = pd.concat(rows, ignore_index=True).sort_values(["subject_id", "timestamp"])
    combined = combined.drop_duplicates(["subject_id", "timestamp"])
    path = out / "shanghai_t2dm_harmonized.csv"
    combined.to_csv(path, index=False)
    print("Harmonized:", len(combined), "readings,", combined.subject_id.nunique(), "patients")
    return path

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="benchmark_results/source")
    p.add_argument("--unit", choices=["mmol/L", "mg/dL"], default="mg/dL", help="Original files label CGM (mg / dl); conversion is not required")
    a = p.parse_args()
    archive, info = acquire(a.out)
    print("Source DOI:", info["article_doi"], "SHA-256:", info["source_zip_sha256"])
    print("CSV:", harmonize(archive, a.out, a.unit))
