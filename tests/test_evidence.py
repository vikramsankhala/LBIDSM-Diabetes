import json

import pytest

from lbidsm.evidence import build_pack, release_blockers, trace_matrix, write_pack
from lbidsm.model_bundle import train_frozen
from lbidsm.prediction import cohort_split, make_examples
from lbidsm.synthetic_cohort import synthetic_cohort


@pytest.fixture(scope="module")
def model():
    train, cal, _ = cohort_split(make_examples(synthetic_cohort(n_subjects=40, days=14, seed=3)))
    return train_frozen(train, cal, "M1")


def pack_for(model, tmp_tests, **kw):
    args = dict(intended_use="", model=model, qualification={"passed": False}, validation={"status": "inconclusive"},
                validation_independent=False, data_manifest={}, tripod={"1": "draft", "2": "not_started"},
                requirements={"A-1": "first", "A-2": "second"}, tests_dir=tmp_tests, regulatory_review=None)
    args.update(kw)
    return build_pack(**args)


@pytest.fixture
def tests_dir(tmp_path):
    (tmp_path / "test_a.py").write_text("def test_one():\n    # REQ: A-1\n    pass\n")
    return tmp_path


def test_trace_matrix_finds_tags_and_gaps(tests_dir):
    # REQ: REG-001
    t = trace_matrix({"A-1": "x", "A-2": "y"}, tests_dir)
    assert t["matrix"]["A-1"]["tests"] == ["test_a.py::test_one"]
    assert t["uncovered"] == ["A-2"]


def test_incomplete_pack_lists_every_blocker(model, tests_dir):
    # REQ: REG-002
    blockers = release_blockers(pack_for(model, tests_dir))
    text = " | ".join(blockers)
    for expected in ("intended-use", "hashed data manifest", "independent external validation",
                     "TRIPOD+AI items not complete", "A-2", "regulatory review"):
        assert expected in text


def test_complete_pack_has_no_blockers(model, tests_dir):
    # REQ: REG-003
    (tests_dir / "test_b.py").write_text("def test_two():\n    # REQ: A-2\n    pass\n")
    pack = pack_for(model, tests_dir, intended_use="Research only: retrospective evaluation.",
                    validation={"status": "estimated"}, validation_independent=True,
                    data_manifest={"cohort.csv": "ab" * 32}, tripod={"1": "complete", "2": "not_applicable"},
                    regulatory_review={"outcome": "documented", "reviewer": "regulatory specialist"})
    assert release_blockers(pack) == []


def test_pack_is_written_with_its_own_hash(model, tests_dir, tmp_path):
    # REQ: REG-004
    digest = write_pack(pack_for(model, tests_dir), tmp_path / "pack.json")
    saved = json.loads((tmp_path / "pack.json").read_text())
    assert len(digest) == 64 and saved["release_blockers"] and saved["model"]["fingerprint"] == model.fingerprint()


def test_unknown_tripod_status_is_rejected(model, tests_dir):
    # REQ: REG-005
    with pytest.raises(ValueError):
        pack_for(model, tests_dir, tripod={"1": "done-ish"})
