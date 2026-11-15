"""Access control, audit trail and disclosure control. Research use only.

Three habits make a system safe to run with real people's data:
deny by default, record every decision where it cannot be quietly edited, and
let only aggregate, small-cell-suppressed results leave. This module is a
reference design and test bed. Production use needs the organisation's identity
provider, key management and write-once log storage behind these same rules.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

RESOURCES = ("code", "synthetic_data", "restricted_data", "aggregate_results", "model_bundle", "decision_records", "audit_log")

PERMISSIONS = {   # role -> resource -> allowed actions. Anything absent is denied.
    "researcher":        {"code": {"read", "write"}, "synthetic_data": {"read", "write"}, "restricted_data": {"read"},
                          "aggregate_results": {"read"}, "model_bundle": {"read"}},
    "statistician":      {"code": {"read", "write"}, "synthetic_data": {"read"}, "restricted_data": {"read"},
                          "aggregate_results": {"read", "write", "export"}, "model_bundle": {"read"}},
    "clinician_reviewer": {"aggregate_results": {"read"}, "decision_records": {"read", "approve"}},
    "data_custodian":    {"restricted_data": {"read", "write", "export"}, "aggregate_results": {"read", "approve"}},
    "release_manager":   {"code": {"read"}, "model_bundle": {"read", "write", "approve"}, "aggregate_results": {"read"}},
    "auditor":           {"audit_log": {"read"}, "decision_records": {"read"}},
    "ci_service":        {"code": {"read"}, "synthetic_data": {"read"}},
}


def authorize(role: str, action: str, resource: str, ctx: dict | None = None) -> tuple[bool, str]:
    """Pure decision function: (allowed, reason). Extra conditions come from `ctx`."""
    ctx = ctx or {}
    if resource not in RESOURCES:
        return False, "unknown resource"
    if action not in PERMISSIONS.get(role, {}).get(resource, set()):
        return False, "not permitted for this role (deny by default)"
    if resource == "restricted_data":
        need = [("mfa", "multi-factor sign-in required"), ("dua_id", "approved data-use agreement ID required")]
        for key, why in need:
            if not ctx.get(key):
                return False, why
        if ctx.get("environment") != "enclave":
            return False, "restricted data may only be used inside the approved secure enclave"
        if ctx.get("session_minutes", 0) > 60:
            return False, "session too old: sign in again"
        if action == "export" and not ctx.get("egress_approval_id"):
            return False, "export needs a recorded egress approval"
    if action == "export" and resource == "aggregate_results" and not ctx.get("disclosure_reviewed"):
        return False, "aggregate results need disclosure review before export"
    if resource == "model_bundle" and action in {"write", "approve"} and not ctx.get("change_ticket"):
        return False, "model changes need a change-control ticket"
    return True, "allowed"


class AuditLog:
    """Append-only, hash-chained log. Editing or deleting any past entry breaks every later hash."""

    def __init__(self):
        self.entries: list[dict] = []

    @staticmethod
    def _hash(entry: dict) -> str:
        body = {k: v for k, v in entry.items() if k != "hash"}
        return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def append(self, **fields) -> dict:
        entry = {"seq": len(self.entries), "utc": datetime.now(timezone.utc).isoformat(), **fields,
                 "prev": self.entries[-1]["hash"] if self.entries else "0" * 64}
        entry["hash"] = self._hash(entry)
        self.entries.append(entry)
        return entry

    def verify(self) -> tuple[bool, int | None]:
        """(True, None) if intact, else (False, index of the first bad entry)."""
        prev = "0" * 64
        for i, e in enumerate(self.entries):
            if e["prev"] != prev or e["hash"] != self._hash(e) or e["seq"] != i:
                return False, i
            prev = e["hash"]
        return True, None

    def save(self, path) -> None:
        Path(path).write_text("\n".join(json.dumps(e, sort_keys=True) for e in self.entries))

    @classmethod
    def load(cls, path) -> "AuditLog":
        log = cls()
        text = Path(path).read_text().strip()
        log.entries = [json.loads(line) for line in text.splitlines()] if text else []
        return log


class AccessGuard:
    """authorize() plus a log entry for every attempt, allowed or denied."""

    def __init__(self, log: AuditLog | None = None):
        self.log = log or AuditLog()

    def check(self, user: str, role: str, action: str, resource: str, ctx: dict | None = None) -> bool:
        ok, why = authorize(role, action, resource, ctx)
        self.log.append(actor=user, role=role, action=action, resource=resource, allowed=ok, reason=why)
        return ok


def suppress_small_cells(table: pd.DataFrame, count_columns: list, k: int = 5, suppress_zero: bool = True) -> pd.DataFrame:
    """Blank counts below k (DUA clause 4.3). Zero is suppressed too, following the clause literally.

    Not covered: secondary suppression (totals or margins that let a reader subtract a hidden cell).
    Have the custodian's disclosure reviewer check complete tables before release.
    """
    out = table.copy()
    for col in count_columns:
        small = out[col] < k if suppress_zero else (out[col] < k) & (out[col] > 0)
        out[col] = out[col].astype("object").where(~small, f"<{k}")
    return out


PATIENT_COLUMNS = {"patient_id", "subject_id", "participant_id", "mrn", "patient"}
DATA_SUFFIXES = {".csv", ".tsv", ".parquet", ".xlsx", ".xls", ".h5", ".feather", ".zip"}


def find_restricted_files(paths, allow: tuple = ("data/README.md",)) -> list:
    """Flag tracked files that look like patient-level data. For CI: fail the build on any hit."""
    hits = []
    for p in map(Path, paths):
        if str(p) in allow or p.suffix.lower() not in DATA_SUFFIXES or not p.exists():
            continue
        if p.suffix.lower() in {".csv", ".tsv"}:
            header = p.read_text(errors="ignore").splitlines()[:1]
            cols = {c.strip().strip('"').lower() for c in (header[0].replace("\t", ",").split(",") if header else [])}
            if cols & PATIENT_COLUMNS or {"timestamp", "glucose_mg_dl"} <= cols:
                hits.append((str(p), "looks like patient-level or CGM data"))
        else:
            hits.append((str(p), "data file type not allowed in the public repository"))
    return hits
