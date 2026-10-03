#!/usr/bin/env python3
"""Audit published observations. Does not load a model or authorize execution."""
import hashlib
import json
import math
import statistics
from pathlib import Path


def load_verified(root):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest.get("schema") != "helixor.public.native_evidence.v1":
        raise ValueError("Unsupported evidence schema")
    expected = {"predictions.json", "calibration.json", "provider-regression.json"}
    if set(manifest["files"]) != expected:
        raise ValueError("Unexpected evidence files")
    data = {}
    for name, digest in manifest["files"].items():
        raw = (root / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError(f"Evidence digest mismatch: {name}")
        data[name] = json.loads(raw)
    return manifest, data


def summarize(root):
    manifest, data = load_verified(root)
    rows = data["predictions.json"]
    answers = manifest["allowed_answers"]
    if len(rows) != manifest["splits"]["test"] or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Wrong test count or duplicate case IDs")
    for row in rows:
        scores = row["scores"]
        if set(scores) != set(answers) or row["expected"] not in answers:
            raise ValueError("Observation differs from the declared answer set")
        if any(not math.isfinite(v) or not 0 <= v <= 1 for v in scores.values()):
            raise ValueError("Invalid probability")
        if abs(sum(scores.values()) - 1) > 0.001:
            raise ValueError("Probability mass does not sum to one")
        if row["choice"] != max(scores, key=scores.get):
            raise ValueError("Choice is not the maximum finite score")
        if type(row["accepted"]) is not bool:
            raise ValueError("Acceptance must be explicit")
        if not math.isfinite(row["inference_ms"]) or row["inference_ms"] <= 0:
            raise ValueError("Invalid inference timing")
    accepted = [r for r in rows if r["accepted"]]
    correct = sum(r["choice"] == r["expected"] for r in rows)
    supported = [r for r in rows if r["expected"] != "unsupported"]
    unsupported = [r for r in rows if r["expected"] == "unsupported"]
    pairs = {}
    for row in rows:
        if row["pair_id"]:
            pairs.setdefault(row["family"], []).append(row)
    if any(len(pair) != 2 for pair in pairs.values()):
        raise ValueError("Incomplete contrast family")
    slices = {}
    for category in sorted({r["category"] for r in rows}):
        group = [r for r in rows if r["category"] == category]
        slices[category] = {"correct": sum(r["choice"] == r["expected"] for r in group), "cases": len(group)}
    calibration = data["calibration.json"]
    if len({r["id"] for r in calibration}) != len(calibration):
        raise ValueError("Duplicate calibration ID")
    if set(r["partition"] for r in calibration) != {"temperature", "gate"}:
        raise ValueError("Unknown calibration partition")
    gate = [r for r in calibration if r["partition"] == "gate"]
    temperature = [r for r in calibration if r["partition"] == "temperature"]
    if len(gate) != manifest["splits"]["gate"] or len(temperature) != manifest["splits"]["temperature"]:
        raise ValueError("Calibration partition counts differ")
    candidates = []
    for row in gate:
        probs = row["probabilities"]
        if len(probs) != len(answers) or any(not math.isfinite(v) or not 0 <= v <= 1 for v in probs) or abs(sum(probs) - 1) > 0.001:
            raise ValueError("Invalid calibration probabilities")
        if type(row["label"]) is not int or row["label"] not in range(len(answers)):
            raise ValueError("Invalid calibration label")
        choice = max(range(len(probs)), key=probs.__getitem__)
        if choice != answers.index("unsupported"):
            candidates.append((round(probs[choice], 4), choice == row["label"]))
    subsets = []
    for threshold in sorted({p for p, _ in candidates}):
        subset = [ok for probability, ok in candidates if probability >= threshold]
        subsets.append({"threshold": threshold, "accepted": len(subset), "correct": sum(subset), "precision": sum(subset) / len(subset)})
    policy = manifest["calibration"]
    sized = [s for s in subsets if s["accepted"] >= policy["minimum_accepted"]]
    qualifying = [s for s in sized if s["precision"] >= policy["target_observed_precision"]]
    calculated_threshold = qualifying[0]["threshold"] if qualifying else None
    if calculated_threshold != policy["threshold"]:
        raise ValueError("Recorded gate differs from calibration observations")
    if policy["threshold"] is None and accepted:
        raise ValueError("A null gate cannot admit a case")
    warm = sorted(r["inference_ms"] for r in rows[1:])
    # Preserve the recorded evaluator's lower-rank percentile convention.
    p95 = warm[int(0.95 * (len(warm) - 1))]
    for provider in data["provider-regression.json"]:
        timing = provider["timing"]
        before, after = timing["raw_ms"]["before"], timing["raw_ms"]["after"]
        if len(before) != timing["n"] or len(after) != timing["n"]:
            raise ValueError("Paired timing sample is incomplete")
        if any(not math.isfinite(v) or v <= 0 for v in before + after):
            raise ValueError("Invalid paired timing")
        measured = {
            "median_before_ms": statistics.median(before),
            "median_after_ms": statistics.median(after),
            "median_paired_delta_ms": statistics.median(b - a for a, b in zip(before, after)),
        }
        if any(not math.isclose(value, timing[key], abs_tol=1e-9) for key, value in measured.items()):
            raise ValueError("Timing summary differs from paired observations")
        if provider["cases"] != len(rows) or not 0 <= provider["choices_preserved"] <= provider["cases"]:
            raise ValueError("Invalid provider replay count")
        if not 0 <= provider["admitted"] <= provider["cases"] or not 0 <= provider["max_probability_delta"] <= 1:
            raise ValueError("Invalid provider replay outcome")
    return {
        "cases": len(rows), "correct": correct, "accuracy_pct": correct / len(rows) * 100,
        "supported_correct": sum(r["choice"] == r["expected"] for r in supported), "supported": len(supported),
        "unsupported_rejected": sum(r["choice"] == "unsupported" for r in unsupported), "unsupported": len(unsupported),
        "pairs_correct": sum(all(r["choice"] == r["expected"] for r in pair) for pair in pairs.values()), "pairs": len(pairs),
        "accepted": len(accepted), "accepted_precision": sum(r["choice"] == r["expected"] for r in accepted) / len(accepted) if accepted else None,
        "coverage_pct": len(accepted) / len(rows) * 100, "threshold": calculated_threshold,
        "best_sized_gate": max(sized, key=lambda s: (s["precision"], s["accepted"])) if sized else None,
        "largest_error_free_gate": max((s for s in subsets if s["precision"] == 1), key=lambda s: s["accepted"], default=None),
        "median_ms": statistics.median(warm), "p95_ms": p95, "warm_observations": len(warm), "slices": slices,
    }


if __name__ == "__main__":
    print(json.dumps(summarize(Path(__file__).resolve().parent), indent=2, allow_nan=False))
