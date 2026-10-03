"""The classification demo reports actual recorded predictions and admission."""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "classification"


def run(root=ROOT, *args):
    return subprocess.run([sys.executable, "-S", str(root / "review.py"), *args],
                          capture_output=True, text=True, timeout=20)


def test_recorded_json_has_scores_and_separate_withheld_admission():
    result = run(ROOT, "--case", "ontology.test.00.02", "--json")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["mode"] == "recorded_inference"
    assert data["admission_threshold"] is None
    case, = data["cases"]
    assert case["category"] == "expedite"
    assert case["scores"] == {"fulfillment": 0.0076, "expedite": 0.9789, "unsupported": 0.0135}
    assert case["accepted"] is False


def test_confident_error_is_not_presented_as_a_correct_answer():
    result = run(ROOT, "--case", "ontology.test.03.27")
    assert result.returncode == 0, result.stderr
    assert "expedite=98.38%" in result.stdout
    assert "Expected label: unsupported (ERROR)" in result.stdout
    assert "Accepted: false" in result.stdout


@pytest.mark.parametrize("forge_admission", [False, True])
def test_changed_or_falsely_admitted_record_stops_the_demo(tmp_path, forge_admission):
    root = tmp_path / "classification"
    shutil.copytree(ROOT, root)
    path = root / "predictions.json"
    rows = json.loads(path.read_text())
    rows[0]["accepted"] = True
    path.write_text(json.dumps(rows))
    if forge_admission:
        manifest_path = root / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest))
    result = run(root)
    assert result.returncode == 2
    assert not result.stdout
    assert "EVIDENCE_INVALID" in result.stderr


def test_unknown_case_does_not_return_a_prediction():
    result = run(ROOT, "--case", "not-a-case", "--json")
    assert result.returncode == 2
    assert not result.stdout
