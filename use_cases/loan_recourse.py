#!/usr/bin/env python3
"""Use Case: Loan Approval with Counterfactual Recourse.

Business Problem:
    A lending institution approves or denies loan applications against
    financial constraints (DTI, LTV, reserves). When an application is
    denied, the applicant should be told the smallest actionable change
    that would get it approved.

Features Demonstrated:
    - Constraint-based state evaluation with named violations
    - Counterfactual search that returns the minimum-cost passing change
    - Typed state changes: {"field": {"delta": n}} adds to the current value,
      {"field": {"set": n}} replaces it; anything else is rejected
    - Stress testing that actually perturbs the approved state

Timings printed here are measured by this script on the machine running it.
"""

from helixor_runtime import HelixorCounterfactualEngine, InterventionError

DTI_CAP = 0.43
LTV_CAP = 0.80
RESERVE_MONTHS = 3


def dti(s: dict[str, float]) -> float:
    return s["monthly_debt"] * 12 / s["income"]


def ltv(s: dict[str, float]) -> float:
    return s["requested_loan"] / s["collateral_value"]


def loan_constraints(s: dict[str, float]) -> list[str]:
    """Return the names of every violated lending constraint (empty = approved)."""
    violations = []
    if dti(s) > DTI_CAP:
        violations.append("DTI_ABOVE_43PCT")
    if ltv(s) > LTV_CAP:
        violations.append("LTV_ABOVE_80PCT")
    if s["liquid_reserves"] < RESERVE_MONTHS * s["monthly_debt"]:
        violations.append("RESERVES_BELOW_3_MONTHS")
    return violations


def main() -> None:
    print("=" * 70)
    print(" USE CASE: LOAN APPROVAL WITH COUNTERFACTUAL RECOURSE ")
    print("=" * 70)

    engine = HelixorCounterfactualEngine(
        loan_constraints,
        # How hard each field is for the applicant to change (relative-change cost).
        cost_weights={
            "monthly_debt": 1.0,
            "liquid_reserves": 1.5,
            "requested_loan": 1.2,
            "income": 3.0,
        },
    )

    applicant = {
        "income": 75000.0,
        "monthly_debt": 3200.0,
        "requested_loan": 280000.0,
        "liquid_reserves": 12000.0,
        "collateral_value": 350000.0,
    }

    print("\n[1] Evaluating loan application...")
    passed, violations = engine.evaluate_state(applicant)
    print(f"  Approved:    {passed}")
    print(f"  DTI:         {dti(applicant):.3f} (cap {DTI_CAP:.2f})")
    print(f"  LTV:         {ltv(applicant):.3f} (cap {LTV_CAP:.2f})")
    print(f"  Violations:  {violations}")

    print("\n[2] Searching for the minimum-cost recourse...")
    candidates = [
        {"monthly_debt": {"delta": -500.0}},      # Pay down $500/mo debt
        {"monthly_debt": {"delta": -1000.0}},     # Pay down $1,000/mo debt
        {"liquid_reserves": {"delta": 10000.0}},  # Add $10K reserves
        {"requested_loan": {"set": 230000.0}},    # Borrow $230K instead
        {"income": {"delta": 15000.0}},           # Add $15K/yr income
        {"monthly_debt": {"delta": -600.0}},      # Pay down $600/mo debt
    ]
    recourse = engine.search_recourse(base_state=applicant, candidate_interventions=candidates)

    print(f"  Base decision:        {recourse.base_action}")
    for i, opt in enumerate(recourse.evaluations):
        tag = "PASS" if opt.passed else "FAIL"
        print(f"    #{i} [{tag}] cost={opt.cost:.4f}  {opt.intervention}  "
              f"DTI={dti(opt.resulting_state):.3f}")
    print(f"  Flipped to approved:  {recourse.flipped}")
    if recourse.flipped:
        for field, ch in recourse.minimal_changes.items():
            print(f"  Minimal change:       {field} {ch['from']:,.0f} -> {ch['to']:,.0f} "
                  f"({ch['delta']:+,.0f})")
        print(f"  Cost:                 {recourse.cost:.4f}")
        print(f"  Violations cleared:   {recourse.violations_cleared}")
    print(f"  Latency:              {recourse.latency_us:.1f} µs (measured)")

    # Typed changes are enforced: a bare number is not guessed as delta or absolute.
    try:
        engine.search_recourse(base_state=applicant, candidate_interventions=[{"monthly_debt": -500}])
    except InterventionError as exc:
        print(f"  Rejected malformed intervention: {exc}")

    print("\n[3] Stress testing the approved (post-recourse) application...")
    if not recourse.flipped:
        raise SystemExit("No candidate intervention flips the decision; nothing to stress test.")
    approved = next(o.resulting_state for o in recourse.evaluations
                    if o.intervention == recourse.minimal_intervention)
    stress = engine.stress_test(
        base_state=approved,
        scenarios={
            "Rate Hike +200bps": {
                "description": "Debt service rises $100/mo",
                "shocks": {"monthly_debt": {"delta": 100.0}},
            },
            "Income Contraction -20%": {
                "description": "Income falls $15,000/yr",
                "shocks": {"income": {"delta": -15000.0}},
            },
            "Asset Devaluation -30%": {
                "description": "Collateral value falls $105,000",
                "shocks": {"collateral_value": {"delta": -105000.0}},
            },
            "Refinance Relief": {
                "description": "Debt service falls $100/mo",
                "shocks": {"monthly_debt": {"delta": -100.0}},
            },
        },
        margins={
            "dti_headroom": lambda s: DTI_CAP - dti(s),
            "ltv_headroom": lambda s: LTV_CAP - ltv(s),
        },
    )

    print(f"  Base passes:       {stress.base_passed}")
    print(f"  Scenarios tested:  {stress.scenarios_evaluated}")
    print(f"  Scenarios passed:  {stress.scenarios_passed}")
    for sc in stress.scenario_results:
        tag = "PASS" if sc.passed else "FAIL"
        print(f"    [{tag}] {sc.scenario_name}: DTI headroom {sc.margins['dti_headroom']:+.3f}, "
              f"LTV headroom {sc.margins['ltv_headroom']:+.3f}"
              + ("" if sc.passed else f"  -> {sc.violations}"))
    print(f"  Latency:           {stress.latency_us:.1f} µs (measured)")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
