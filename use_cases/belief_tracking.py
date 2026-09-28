#!/usr/bin/env python3
"""Use Case: Epistemic Belief Tracking for Operational Hypotheses.

Business Problem:
    An operations team tracks confidence in business rules and behavioral
    hypotheses across different contexts (regions, segments, time periods).
    Some beliefs reach "bedrock" status (proven reliable), while others
    are falsified and marked "dead" — all tracked with Bayesian rigor.

Features Demonstrated:
    • Conjugate Beta posterior updating
    • Asymmetric falsification (contradictions hurt more than confirmations help)
    • Contextual belief isolation
    • Bedrock detection (high confidence) and dead detection (falsified)
"""

from helixor_runtime import HelixorBeliefLedger


def main() -> None:
    print("=" * 70)
    print(" USE CASE: EPISTEMIC BELIEF TRACKING ")
    print("=" * 70)

    ledger = HelixorBeliefLedger(pain_multiplier=3.0)

    # ── Track belief in "Premium customers churn less" ──
    claim = "premium_customers_churn_less"
    print(f'\n[Claim]: "{claim}"')

    # Record observations across two contexts
    for _ in range(15):
        ledger.record(claim, "CONFIRM", context="north_america")
    for _ in range(2):
        ledger.record(claim, "CONTRADICT", context="north_america")

    for _ in range(3):
        ledger.record(claim, "CONFIRM", context="europe")
    for _ in range(8):
        ledger.record(claim, "CONTRADICT", context="europe")

    na_belief = ledger.belief(claim, context="north_america")
    eu_belief = ledger.belief(claim, context="europe")

    print(f"  North America: belief = {na_belief:.3f}  bedrock = {ledger.is_bedrock(claim, context='north_america')}")
    print(f"  Europe:        belief = {eu_belief:.3f}  dead = {ledger.is_dead(claim, context='europe')}")

    print("\n  Insight: The same hypothesis is near-bedrock in North America")
    print("  but falsified in Europe. Context isolation prevents global pollution.")

    # ── Track a pricing hypothesis ──
    pricing = "dynamic_pricing_increases_revenue"
    print(f'\n[Claim]: "{pricing}"')

    for _ in range(50):
        ledger.record(pricing, "CONFIRM")
    ledger.record(pricing, "CONTRADICT", strength=2.0)  # One strong contradiction

    overall = ledger.belief(pricing)
    print(f"  Overall belief: {overall:.3f}")
    print(f"  Bedrock:        {ledger.is_bedrock(pricing)}")
    print(f"  Note: 50 confirmations + 1 strong contradiction (pain_multiplier=3.0)")
    print(f"  The asymmetric penalty prevents premature bedrock status.")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
