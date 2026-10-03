#!/usr/bin/env python3
"""Inspect recorded business examples; no policy evaluation or model inference.

Only Python's standard library is required. File hashes detect accidental drift,
not authorship or approval. Run new inputs through the Studio source integration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = frozenset({
    "shipment-release.json", "purchase-review.json", "purchase-review-v2.json",
    "cases.json", "recorded-results.json",
})


def unique_rows(rows: list[dict], key: str) -> dict[str, dict]:
    indexed = {row[key]: row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError(f"Duplicate {key} in recorded evidence")
    return indexed


def load_verified(root: Path = ROOT) -> tuple[dict, dict]:
    """Check bundle integrity and recorded-result consistency, never evaluate rules."""
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if (manifest["schema"] != "helixor.demos.recorded_business_bundle.v1"
            or manifest["mode"] != "recorded_evidence_only"
            or set(manifest["files"]) != FILES):
        raise ValueError("Unsupported recorded bundle manifest")
    data = {}
    for name, digest in manifest["files"].items():
        raw = (root / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError(f"Evidence digest mismatch: {name}")
        data[name] = json.loads(raw)
    record = data["recorded-results.json"]
    if record["schema"] != "helixor.docs.business_examples.v1":
        raise ValueError("Unsupported recorded result schema")
    inputs = {name: digest for name, digest in manifest["files"].items()
              if name != "recorded-results.json"}
    if record["files"] != inputs:
        raise ValueError("Recorded inputs differ from the bundled inputs")
    cases = unique_rows(data["cases.json"], "id")
    results = unique_rows(record["results"], "case_id")
    if cases.keys() != results.keys() or len(cases) != manifest["case_count"]:
        raise ValueError("Recorded case IDs or count differ")
    for case_id, case in cases.items():
        result = results[case_id]
        bundle = data[f"{case['bundle']}.json"]
        decision, = bundle["specification"]["decisions"]
        rule_ids = {rule["id"] for rule in bundle["draft"]["rules"]}
        if not set(result["rule_ids"]) <= rule_ids:
            raise ValueError(f"Unknown recorded rule: {case_id}")
        action = result["chosen_move"]
        if action != case["expected_action"]:
            raise ValueError(f"Recorded action differs from expectation: {case_id}")
        if action is None:
            if result["answer_kind"] != "blocked" or not result["failure_code"]:
                raise ValueError(f"Missing explicit block: {case_id}")
        elif (result["answer_kind"] != "decision" or result["failure_code"] is not None
              or action not in decision["allowed_actions"]):
            raise ValueError(f"Invalid recorded decision: {case_id}")
    return manifest, data


def show_case(case: dict, result: dict, bundle: dict, *, detailed: bool) -> None:
    outcome = result["chosen_move"] or f"BLOCKED ({result['failure_code']})"
    print(f"  {case['id']}: {outcome}")
    print(f"    {case['business_reason']}")
    if detailed:
        print(f"    Recorded input: {json.dumps(case['state'], sort_keys=True)}")
        print(f"    Recorded rules: {', '.join(result['rule_ids']) or '(none)'}")
        draft = bundle["draft"]
        cited = [rule for rule in draft["rules"] if rule["id"] in result["rule_ids"]]
        if not cited and result["answer_kind"] == "decision":
            cited = draft["nominal_choices"]
        for item in cited:
            for citation in item["citations"]:
                print(f"    Policy {citation['paragraph_id']}: {citation['quote']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--case", help="show one case, its input, and cited policy")
    parser.add_argument("--check", action="store_true", help="check recorded evidence only")
    args = parser.parse_args(argv)
    try:
        manifest, data = load_verified()
        cases = data["cases.json"]
        if args.case and args.case not in {case["id"] for case in cases}:
            parser.error(f"unknown case {args.case!r}; run without --case to list all cases")
        print("RECORDED EVIDENCE ONLY - no new policy execution or model inference")
        print(f"Verified {len(manifest['files'])} artifact hashes; "
              f"{len(cases)}/{len(cases)} recorded outcomes match the example expectations.")
        if args.check:
            return 0
        record = data["recorded-results.json"]
        results = unique_rows(record["results"], "case_id")
        print(f"Recorded run: {record['run_date']}. Inputs are illustrative structured facts.")
        for name in dict.fromkeys(case["bundle"] for case in cases):
            selected = [case for case in cases if case["bundle"] == name
                        and (not args.case or case["id"] == args.case)]
            if selected:
                bundle = data[f"{name}.json"]
                print(f"\n{bundle['source']['title']}")
                for case in selected:
                    show_case(case, results[case["id"]], bundle, detailed=bool(args.case))
        if not args.case:
            revision = record["policy_revision"]
            print("\nRecorded purchasing policy change (v1 -> v2)")
            print(f"  Same input: {json.dumps(revision['state'], sort_keys=True)}")
            print(f"  {revision['before']} -> {revision['after']}")
        print("\nRun new inputs: follow domain_packs/README.md for Studio setup and review.")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"EVIDENCE_INVALID: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
