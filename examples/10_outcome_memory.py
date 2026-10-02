#!/usr/bin/env python3
"""Example 10 · Tier 0: Outcome memory — record outcomes, route by confidence.

The two scripts of the "Track outcomes and confidence" tutorial, in one file:

  [1] how belief moves with each confirmation, contradiction and partial outcome;
  [2] routing a refund rule per customer segment (auto, sampled, reviewed or
      switched off), then saving and restoring the ledger.

HelixorBeliefLedger is standalone: evaluate() does not read or write it. Belief
is a conservative routing score (contradictions count three times by default),
not a calibrated probability. The snapshot is written to a temporary directory,
not into the clone.

Tutorial: https://helixor.dev/tutorials/outcome-memory.html
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from helixor_runtime import HelixorBeliefLedger

CLAIM = "refunds.auto_approve_under_50"
REVIEW_BELOW = 0.70


def how_belief_moves() -> None:
    ledger = HelixorBeliefLedger()
    claim = CLAIM

    print("unobserved             :", round(ledger.belief(claim), 3))

    for _ in range(4):
        ledger.record(claim, "CONFIRM", context="segment:returning")
    print("4 confirms             :", round(ledger.belief(claim, context="segment:returning"), 3))

    ledger.record(claim, "CONTRADICT", context="segment:returning")
    print("4 confirms, 1 contra   :", round(ledger.belief(claim, context="segment:returning"), 3))

    ledger.record(claim, "PARTIAL", strength=0.5, context="segment:returning")
    print("+ PARTIAL 0.5          :", round(ledger.belief(claim, context="segment:returning"), 3))

    print("other context          :", round(ledger.belief(claim, context="segment:new"), 3))
    print("all contexts           :", round(ledger.belief(claim), 3))


def load_ledger(state: Path) -> HelixorBeliefLedger:
    """Restore the ledger from its last snapshot, or start empty."""
    if state.exists():
        return HelixorBeliefLedger.restore(json.loads(state.read_text()))
    return HelixorBeliefLedger()


def save_ledger(ledger: HelixorBeliefLedger, state: Path) -> None:
    """Write a snapshot atomically: a crash leaves the previous file intact."""
    tmp = state.with_suffix(".tmp")
    tmp.write_text(json.dumps(ledger.snapshot()))
    os.replace(tmp, state)


def route(ledger, claim, context) -> str:
    """What the application does with the next decision made by this rule."""
    if ledger.is_dead(claim, context=context):
        return "disable_rule"
    if ledger.is_bedrock(claim, context=context):
        return "auto"
    if ledger.belief(claim, context=context) < REVIEW_BELOW:
        return "auto_with_review"
    return "auto_sampled"


def route_by_confidence(state: Path) -> None:
    ledger = load_ledger(state)

    # Outcomes reported after the rule auto-approved refunds, per customer segment.
    history = {
        "segment:returning": ["CONFIRM"] * 24,
        "segment:new": ["CONFIRM"] * 6 + ["CONTRADICT"] * 2,
        "segment:reseller": ["CONTRADICT"] * 4 + ["CONFIRM"],
    }
    for context, outcomes in history.items():
        for outcome in outcomes:
            ledger.record(CLAIM, outcome, context=context)

    print(f"{'context':20} {'belief':>7}  bedrock  dead   route")
    for context in history:
        print(f"{context:20} {ledger.belief(CLAIM, context=context):7.3f}  "
              f"{ledger.is_bedrock(CLAIM, context=context)!s:7}  "
              f"{ledger.is_dead(CLAIM, context=context)!s:5}  {route(ledger, CLAIM, context)}")

    # One chargeback in the returning segment.
    ledger.record(CLAIM, "CONTRADICT", context="segment:returning")
    print("\nafter one chargeback in segment:returning:")
    print(f"  belief={ledger.belief(CLAIM, context='segment:returning'):.3f} "
          f"bedrock={ledger.is_bedrock(CLAIM, context='segment:returning')} "
          f"route={route(ledger, CLAIM, 'segment:returning')}")

    # Restart: save a snapshot, restore it, and check nothing was lost.
    save_ledger(ledger, state)
    restored = load_ledger(state)
    same = all(
        restored.belief(CLAIM, context=c) == ledger.belief(CLAIM, context=c) for c in history
    )
    print(f"\nsnapshot {json.loads(state.read_text())['schema_version']}: beliefs identical: {same}")
    print(f"evidence in segment:new: {restored.evidence_mass(CLAIM, context='segment:new')}, "
          f"posterior (alpha, beta): {restored.posterior(CLAIM, context='segment:new')}")


def main() -> int:
    print("=" * 70)
    print(" HELIXOR DECISION RUNTIME — OUTCOME MEMORY ")
    print("=" * 70)
    print("\n[1] How belief moves")
    how_belief_moves()
    print("\n[2] Route decisions by confidence, then persist the ledger")
    with tempfile.TemporaryDirectory() as tmp:
        route_by_confidence(Path(tmp) / "ledger.json")
    print("\n" + "=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
