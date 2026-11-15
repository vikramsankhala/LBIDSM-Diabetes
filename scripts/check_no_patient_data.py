"""Fail if any tracked file looks like patient-level data. Run in CI before every merge.

    python scripts/check_no_patient_data.py

The two synthetic teaching files in data/sample/ are allowed by exact name, and only while every
subject_id in them looks synthetic (S followed by three digits). A real file saved under one of those
names is blocked.
"""
import re
import subprocess
import sys
from pathlib import Path

from lbidsm.access import find_restricted_files

SYNTHETIC_SAMPLES = ("data/sample/synthetic_cgm_sample.csv", "data/sample/example_windows.csv")
SYNTHETIC_ID = re.compile(r"^S\d{3}$")


def check_synthetic_samples() -> list:
    problems = []
    for name in SYNTHETIC_SAMPLES:
        path = Path(name)
        if not path.exists():
            continue
        lines = path.read_text().splitlines()
        header = lines[0].split(",") if lines else []
        if "subject_id" not in header:
            problems.append((name, "no subject_id column to check"))
            continue
        col = header.index("subject_id")
        bad = {row.split(",")[col] for row in lines[1:] if not SYNTHETIC_ID.match(row.split(",")[col])}
        if bad:
            problems.append((name, f"subject ids do not look synthetic: {sorted(bad)[:3]}"))
    return problems


def main() -> int:
    tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout.split("\n")
    hits = find_restricted_files([p for p in tracked if p], allow=("data/README.md",) + SYNTHETIC_SAMPLES)
    hits += check_synthetic_samples()
    for path, why in hits:
        print(f"BLOCKED {path}: {why}")
    print("No patient-level files found." if not hits else f"{len(hits)} file(s) must not be committed.")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
