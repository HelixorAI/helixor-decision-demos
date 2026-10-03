"""Recorded evidence integrity; these tests do not execute policy rules."""

import hashlib
import json
import shutil
import subprocess
import sys

import pytest

from domain_packs import review


@pytest.fixture
def bundle(tmp_path):
    for path in review.ROOT.glob("*.json"):
        shutil.copyfile(path, tmp_path / path.name)
    return tmp_path


def replace_record(root, record):
    """Refresh the outer digest so consistency validation sees a changed record."""
    path = root / "recorded-results.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_walkthrough_runs_without_installed_packages():
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(review.ROOT / "review.py")],
        capture_output=True, text=True, check=True,
    )
    assert "RECORDED EVIDENCE ONLY" in result.stdout
    assert "shipment-reserve-shortfall: hold" in result.stdout
    assert "purchase-missing-approval: BLOCKED (VALUE_MISSING)" in result.stdout
    assert "standard_process -> manager_review" in result.stdout


def test_modified_input_is_rejected_instead_of_replayed(bundle):
    path = bundle / "cases.json"
    path.write_bytes(path.read_bytes().replace(b'"quantity": 100', b'"quantity": 1'))
    with pytest.raises(ValueError, match="digest mismatch: cases.json"):
        review.load_verified(bundle)


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "wrong_action", "unknown_rule"])
def test_inconsistent_record_fails_even_with_updated_digest(bundle, mutation):
    record = json.loads((bundle / "recorded-results.json").read_text())
    if mutation == "duplicate":
        record["results"].append(record["results"][0])
    elif mutation == "missing":
        record["results"].pop()
    elif mutation == "wrong_action":
        record["results"][0]["chosen_move"] = "hold"
    else:
        record["results"][0]["rule_ids"] = ["not_a_policy_rule"]
    replace_record(bundle, record)
    with pytest.raises(ValueError):
        review.load_verified(bundle)


def test_unknown_case_fails_without_showing_a_decision(capsys):
    with pytest.raises(SystemExit) as error:
        review.main(["--case", "not-a-case"])
    assert error.value.code == 2
    assert not capsys.readouterr().out


def test_selected_case_shows_recorded_rule_and_policy(capsys):
    assert review.main(["--case", "purchase-unapproved-supplier"]) == 0
    output = capsys.readouterr().out
    assert "RECORDED EVIDENCE ONLY" in output
    assert "Recorded rules: supplier_review" in output
    assert "Policy P1: If the supplier is not approved" in output
    assert "shipment-clear:" not in output
