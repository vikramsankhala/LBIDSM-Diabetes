import json

import pandas as pd

from lbidsm.access import (AccessGuard, AuditLog, authorize, find_restricted_files, suppress_small_cells)

ENCLAVE = {"mfa": True, "dua_id": "DUA-001", "environment": "enclave", "session_minutes": 10}


def test_deny_by_default():
    # REQ: SEC-001
    assert not authorize("ci_service", "read", "restricted_data", ENCLAVE)[0]
    assert not authorize("nobody", "read", "code")[0]
    assert not authorize("researcher", "export", "restricted_data", ENCLAVE)[0]
    assert not authorize("researcher", "read", "not_a_resource")[0]


def test_restricted_data_needs_mfa_dua_enclave_and_fresh_session():
    # REQ: SEC-002
    assert authorize("statistician", "read", "restricted_data", ENCLAVE)[0]
    for broken in ({"mfa": False}, {"dua_id": ""}, {"environment": "laptop"}, {"session_minutes": 120}):
        assert not authorize("statistician", "read", "restricted_data", {**ENCLAVE, **broken})[0]


def test_export_rules():
    # REQ: SEC-003
    assert not authorize("statistician", "export", "aggregate_results")[0]
    assert authorize("statistician", "export", "aggregate_results", {"disclosure_reviewed": True})[0]
    assert not authorize("data_custodian", "export", "restricted_data", ENCLAVE)[0]
    assert authorize("data_custodian", "export", "restricted_data", {**ENCLAVE, "egress_approval_id": "E-9"})[0]


def test_model_changes_need_a_change_ticket():
    # REQ: SEC-004
    assert not authorize("release_manager", "write", "model_bundle")[0]
    assert authorize("release_manager", "write", "model_bundle", {"change_ticket": "CHG-12"})[0]


def test_every_attempt_is_logged_and_chain_verifies():
    # REQ: SEC-005
    guard = AccessGuard()
    guard.check("u1", "researcher", "read", "code")
    guard.check("u1", "researcher", "read", "restricted_data")
    assert [e["allowed"] for e in guard.log.entries] == [True, False]
    assert guard.log.verify() == (True, None)


def test_editing_history_is_detected(tmp_path):
    # REQ: SEC-006
    log = AuditLog()
    for i in range(5):
        log.append(actor=f"u{i}", action="read", allowed=True)
    path = tmp_path / "audit.jsonl"
    log.save(path)
    loaded = AuditLog.load(path)
    assert loaded.verify() == (True, None)
    loaded.entries[2]["allowed"] = False
    assert loaded.verify() == (False, 2)
    loaded.entries = loaded.entries[:1] + loaded.entries[2:]     # deleting an entry also breaks the chain
    assert not loaded.verify()[0]


def test_small_cells_are_suppressed():
    # REQ: SEC-007
    t = pd.DataFrame({"site": ["a", "b", "c", "d"], "participants": [12, 4, 5, 0], "events": [30, 3, 9, 1]})
    out = suppress_small_cells(t, ["participants", "events"], k=5)
    assert list(out.participants) == [12, "<5", 5, "<5"]
    assert list(out.events) == [30, "<5", 9, "<5"]
    assert t.participants.iloc[1] == 4                     # the input is not modified
    assert list(suppress_small_cells(t, ["participants"], suppress_zero=False).participants) == [12, "<5", 5, 0]


def test_patient_level_files_are_flagged(tmp_path):
    # REQ: SEC-008
    (tmp_path / "ok.md").write_text("notes")
    bad = tmp_path / "cgm.csv"
    bad.write_text("subject_id,timestamp,glucose_mg_dl\nS1,2026-01-01,100\n")
    fine = tmp_path / "table.csv"
    fine.write_text("site,count\na,10\n")
    blob = tmp_path / "x.parquet"
    blob.write_bytes(b"x")
    flagged = {p for p, _ in find_restricted_files([tmp_path / "ok.md", bad, fine, blob])}
    assert flagged == {str(bad), str(blob)}


def test_audit_entries_are_json_serialisable():
    # REQ: SEC-009
    guard = AccessGuard()
    guard.check("u", "auditor", "read", "audit_log")
    json.dumps(guard.log.entries)
