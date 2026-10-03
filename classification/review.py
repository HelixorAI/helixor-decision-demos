#!/usr/bin/env python3
"""Show English-to-category predictions from the published model evaluation.

This is recorded inference, not a classifier for new text. The model's encoder
and finite prediction head produced the scores; this program serializes records.
"""

import argparse
import json
import sys
from pathlib import Path

from recompute import load_verified, summarize

ROOT = Path(__file__).resolve().parent
EXAMPLES = (
    "ontology.test.00.00",  # Check stock fulfillment.
    "ontology.test.00.02",  # Check the need for faster delivery.
    "ontology.test.00.01",  # An action instruction is outside this contract.
    "ontology.test.03.27",  # Confident error: two questions in one request.
    "ontology.test.02.34",  # Confident error: a colloquial supported question.
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--case", help="inspect any published test case by ID")
    parser.add_argument("--json", action="store_true", help="serialize the selected recorded predictions")
    args = parser.parse_args(argv)
    try:
        summary = summarize(ROOT)
        manifest, data = load_verified(ROOT)
        indexed = {row["id"]: row for row in data["predictions.json"]}
        ids = (args.case,) if args.case else EXAMPLES
        if any(case_id not in indexed for case_id in ids):
            parser.error("unknown case ID; available IDs are in classification/predictions.json")
        rows = [indexed[case_id] for case_id in ids]
        if args.json:
            output = {
                "mode": "recorded_inference",
                "run_date": manifest["run_date"],
                "admission_threshold": summary["threshold"],
                "cases": [{
                    "id": row["id"], "text": row["text"],
                    "category": row["choice"], "scores": row["scores"],
                    "expected": row["expected"], "accepted": row["accepted"],
                } for row in rows],
            }
            print(json.dumps(output, indent=2, allow_nan=False))
            return 0
        print("RECORDED MODEL INFERENCE - no model is loaded by this command")
        print("Categories: " + ", ".join(manifest["allowed_answers"]))
        print("Task: classify a question about an order already selected by the application.")
        for row in rows:
            print(f"\n{row['id']}: {row['text']}")
            print(f"  Predicted category: {row['choice']}")
            print("  Scores: " + ", ".join(f"{name}={score:.2%}" for name, score in row["scores"].items()))
            print(f"  Expected label: {row['expected']} "
                  f"({'MATCH' if row['choice'] == row['expected'] else 'ERROR'})")
            print(f"  Accepted: {str(row['accepted']).lower()}")
        print(f"\nFull test set: {summary['correct']}/{summary['cases']} "
              f"candidate matches ({summary['accuracy_pct']:.2f}%).")
        print(f"Admitted: {summary['accepted']}/{summary['cases']}; "
              f"threshold: {json.dumps(summary['threshold'])}.")
        print("The recorded gate qualified no threshold: these candidates cannot authorize routing.")
        print("Scores are not correctness guarantees. Labels are synthetic, not human business ground truth.")
        print("See classification/README.md for the model pipeline and fresh-inference prerequisites.")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"EVIDENCE_INVALID: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
