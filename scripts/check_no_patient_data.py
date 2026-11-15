"""Fail if any tracked file looks like patient-level data. Run in CI before every merge.

    python scripts/check_no_patient_data.py
"""
import subprocess
import sys

from lbidsm.access import find_restricted_files


def main() -> int:
    tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout.split("\n")
    hits = find_restricted_files([p for p in tracked if p])
    for path, why in hits:
        print(f"BLOCKED {path}: {why}")
    print("No patient-level files found." if not hits else f"{len(hits)} file(s) must not be committed.")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
