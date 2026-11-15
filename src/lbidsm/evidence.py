"""Regulatory evidence pack: collect proof in one auditable file. Research use only.

Regulators and ethics boards ask the same questions: what is it for, what exactly
was tested, can you prove it, and what could go wrong. This module gathers the
answers that software can supply (hashes, gate results, test coverage of each
requirement) and lists what is still missing. A pack with no blockers does NOT
make software a medical device or clear it for clinical use.
Regulatory status is decided by regulators and qualified specialists.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .integrity import sha256_file  # noqa: F401  (re-exported for convenience)

TRIPOD_STATUSES = ("not_started", "draft", "complete", "not_applicable")
REQ_TAG = re.compile(r"^\s*#\s*REQ:\s*([A-Za-z0-9\-]+)")


def trace_matrix(requirements: dict, tests_dir) -> dict:
    """Map each requirement ID to the tests tagged `# REQ: <id>`. Untested requirements are listed."""
    found: dict = {}
    for path in sorted(Path(tests_dir).glob("test_*.py")):
        current = None
        for line in path.read_text().splitlines():
            m = re.match(r"\s*def (test_\w+)", line)
            if m:
                current = f"{path.name}::{m.group(1)}"
            tag = REQ_TAG.match(line)
            if tag and current:
                found.setdefault(tag.group(1), []).append(current)
    matrix = {rid: {"text": text, "tests": found.get(rid, [])} for rid, text in requirements.items()}
    return {"matrix": matrix, "uncovered": [r for r, v in matrix.items() if not v["tests"]],
            "unknown_tags": sorted(set(found) - set(requirements))}


def build_pack(*, intended_use: str, model, qualification: dict, validation: dict, validation_independent: bool,
               data_manifest: dict, tripod: dict, requirements: dict, tests_dir, regulatory_review: dict | None) -> dict:
    bad = set(tripod.values()) - set(TRIPOD_STATUSES)
    if bad:
        raise ValueError(f"Unknown TRIPOD+AI status values: {sorted(bad)}")
    return {
        "intended_use": intended_use,
        "model": {"name": model.name, "fingerprint": model.fingerprint(), "code_version": model.code_version,
                  "event_definition": model.event_definition, "trained_on": model.trained_on},
        "qualification": qualification,
        "validation": {"status": validation.get("status"), "independent": validation_independent,
                       "summary": {k: validation[k] for k in ("auroc", "auprc", "brier", "calibration") if k in validation}},
        "data_manifest": data_manifest,                  # file name -> SHA-256
        "tripod_ai": {"items": tripod, "counts": {s: list(tripod.values()).count(s) for s in TRIPOD_STATUSES}},
        "traceability": trace_matrix(requirements, tests_dir),
        "regulatory_review": regulatory_review,          # who reviewed, which rules, when, outcome
    }


def release_blockers(pack: dict) -> list:
    """Why this software may NOT be used for any clinical claim yet. Mirrors docs/VALIDATION.md release gates."""
    out = []
    if not pack.get("intended_use", "").strip():
        out.append("no written intended-use statement")
    if not pack.get("model", {}).get("fingerprint"):
        out.append("model not locked (no fingerprint)")
    if not pack.get("data_manifest"):
        out.append("no hashed data manifest")
    v = pack.get("validation", {})
    if v.get("status") != "estimated" or not v.get("independent"):
        out.append("no completed independent external validation")
    items = pack.get("tripod_ai", {}).get("items", {})
    open_items = [k for k, s in items.items() if s not in ("complete", "not_applicable")]
    if not items:
        out.append("TRIPOD+AI checklist not loaded")
    elif open_items:
        out.append(f"TRIPOD+AI items not complete: {len(open_items)}")
    if pack.get("traceability", {}).get("uncovered"):
        out.append("requirements without a test: " + ", ".join(pack["traceability"]["uncovered"]))
    review = pack.get("regulatory_review") or {}
    if review.get("outcome") != "documented":
        out.append("local regulatory review not documented")
    return out


def write_pack(pack: dict, path) -> str:
    """Write the pack as canonical JSON and return its own SHA-256, to be quoted in submissions."""
    text = json.dumps({**pack, "release_blockers": release_blockers(pack)}, indent=2, sort_keys=True, default=str)
    Path(path).write_text(text)
    return hashlib.sha256(text.encode()).hexdigest()
