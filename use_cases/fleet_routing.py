#!/usr/bin/env python3
"""Use Case: Fleet Routing with Feasibility Checks, Suggestions and Fallbacks.

Business Problem:
    A dispatcher has today's deliveries and a small fleet. Before planning,
    they need to know what the planner requires, whether today's load can be
    served at all, what to change if it cannot, and which least-bad plan to
    run if nothing changes in time.

Features Demonstrated:
    • Required vs optional inputs, with the defaults the solver applies
    • Pre-solve feasibility checks that name the stop and the exact shortfall
    • Parameter suggestions derived from the data (necessary lower bounds)
    • Constraint classes, and which constraints the route builder checks
    • Ranked best-effort plans, each saying what it relaxes (licensed)
    • Solving in either deployment model, chosen by ONE explicit switch:
      --mode embedded (the solver runs in this process) or --mode hosted (the
      Helixor solver service). Same answer, same errors; no default, no
      fallback between them.

What the plans are:
    Step 6 optimises the routes: with time windows declared, a local search
    (feasible insertion, then simulated annealing with ruin-and-recreate)
    sequences stops against their windows; the answer names the engine that
    ran and its seed and final distance. The plan is returned only when it is
    feasible; otherwise the answer names the shortfalls and ranks relaxed
    alternates. The ranked best-effort plans in step 5 relax the problem with
    the capacity-aware sweep as their admission probe, so a relaxation there
    is sufficient, not minimal.
"""

from __future__ import annotations

import argparse
import os
from typing import Any

from helixor_runtime import HelixorSolver, LicenseError, SolverEngineUnavailableError

DEPOT = [33.749, -84.388]

# Today's deliveries: [lat, lon], demand in crates, delivery window in hours.
TODAY: dict[str, Any] = {
    "depot": DEPOT,
    "depot_time_window": [7, 19],
    "speed_kmh": 40,
    "customers": [
        {"id": "bakery", "location": [33.771, -84.391], "demand": 12, "time_window": [8, 11]},
        {"id": "clinic", "location": [33.762, -84.357], "demand": 8, "time_window": [9, 12]},
        {"id": "school", "location": [33.731, -84.402], "demand": 15, "time_window": [7, 9]},
        {"id": "market", "location": [33.742, -84.349], "demand": 10, "time_window": [10, 16]},
        {"id": "hotel", "location": [33.781, -84.371], "demand": 9, "time_window": [8, 18]},
        {"id": "cafe", "location": [33.718, -84.366], "demand": 14, "time_window": [7, 10]},
        {"id": "ferry-kiosk", "location": [34.25, -83.9], "demand": 6, "time_window": [7, 7.5]},
    ],
    "vehicles": [{"id": "van-1", "capacity": 40}],
}


def show_inputs() -> None:
    print("\n[1] What the planner needs")
    contract = HelixorSolver.describe_inputs("vrp")
    for entity in contract["entities"]:
        required = [c["name"] for c in entity["columns"] if c["required"]]
        defaults = [f"{c['name']}={c['default']}{(' ' + c['unit']) if c.get('unit') else ''}"
                    for c in entity["columns"] if not c["required"] and "default" in c]
        print(f"  {entity['entity']:<10} required: {', '.join(required) or '-'}")
        if defaults:
            print(f"  {'':<10} defaults: {', '.join(defaults)}")

    missing_capacity = {k: v for k, v in TODAY.items() if k != "vehicles"}
    report = HelixorSolver.validate("vrp", missing_capacity)
    print(f"  Without vehicles: ok={report['ok']} -> {report['errors'][0]['detail']}")
    report = HelixorSolver.validate("vrp", TODAY)
    for default in report["defaults_in_effect"]:
        print(f"  Default in effect: {default['field']} = {default['default']} on {default['rows']} row(s)")


def show_feasibility() -> dict[str, Any]:
    print("\n[2] Pre-solve feasibility checks")
    report = HelixorSolver.check_feasibility("vrp", TODAY)
    print(f"  ok={report['ok']}  structurally_infeasible={report['structurally_infeasible']}")
    for finding in report["findings"]:
        print(f"  [{finding['severity']}] {finding['check_id']}: {finding['message']}")
    for skipped in report["skipped"]:
        print(f"  [skipped] {skipped['check_id']}: {skipped['reason']}")
    return report


def show_suggestions() -> None:
    print("\n[3] Suggested parameters (necessary, derived from the data)")
    for s in HelixorSolver.suggest_parameters("vrp", TODAY):
        print(f"  {s['parameter']}: {s['current']} -> at least {s['suggested']}  ({s['rationale']})")


def show_constraint_classes() -> None:
    print("\n[4] Constraint classes")
    for row in HelixorSolver.constraint_classes("vrp"):
        if row["default_enabled"] or row["enforced_by"] != "declared_only":
            print(f"  {row['constraint']:<28} {row['class']:<5} enforced by {row['enforced_by']}")


def show_options(license: Any) -> None:
    print("\n[5] Ranked best-effort plans (licensed)")
    try:
        result = HelixorSolver.best_effort_options("vrp", TODAY, license)
    except (LicenseError, SolverEngineUnavailableError) as exc:
        print(f"  Not run: {type(exc).__name__}: {exc}")
        return
    print(f"  status={result['status']}  not checked by the route builder: {result['not_checked']}")
    for option in result["options"]:
        relaxes = "; ".join(f"{r['parameter']} {r['from']} -> {r['to']}" for r in option["relaxes"]) or "nothing"
        held = [s["stop"] for s in option["unserved_stops"]]
        print(f"  #{option['rank']} {option['kind']:<18} relaxes {relaxes}"
              f"{'; holds back ' + ', '.join(held) if held else ''}; {option['total_distance_km']:.1f} km")
    for miss in result["not_found"]:
        print(f"  (no {miss['kind']} option: {miss['reason']})")


# The same deliveries once the dispatcher has acted on step 3: a second van,
# and the ferry kiosk (unreachable in its window) moved to tomorrow.
PLANNABLE: dict[str, Any] = {
    **TODAY,
    "customers": [c for c in TODAY["customers"] if c["id"] != "ferry-kiosk"],
    "vehicles": [{"id": "van-1", "capacity": 40}, {"id": "van-2", "capacity": 40}],
}


def configured_solver(mode: str | None, license: Any) -> HelixorSolver | None:
    """The one explicit switch between the two deployment models."""
    if mode == "embedded":
        return HelixorSolver(mode="embedded", license=license)
    if mode == "hosted":
        # The service address and token are named explicitly; nothing is assumed.
        return HelixorSolver(
            mode="hosted",
            base_url=os.environ["HELIXOR_SOLVER_URL"],
            auth=os.environ["HELIXOR_SOLVER_TOKEN"],
        )
    return None


def show_plan(solver: HelixorSolver | None) -> None:
    print("\n[6] Plan the routes")
    if solver is None:
        print("  Not run: choose --mode embedded or --mode hosted (there is no default).")
        return
    try:
        stated = solver.solve("vrp", TODAY, options={"time_limit_seconds": 2})
        plan = solver.solve("vrp", PLANNABLE, options={"time_limit_seconds": 2})
    except (LicenseError, SolverEngineUnavailableError) as exc:
        print(f"  Not run: {type(exc).__name__}: {exc}")
        return
    meta = stated["metadata"]
    print(f"  Served by: {meta['model']}")
    print(f"  Today as stated: verdict={stated['verdict']}, plan returned: {stated['solution'] is not None}")
    for row in stated["shortfalls"]:
        print(f"    shortfall: {row.get('message') or row['kind']}")
    for option in stated["alternates"]:
        relaxes = "; ".join(f"{r['parameter']} {r['from']} -> {r['to']}" for r in option["relaxes"])
        print(f"    alternate #{option['rank']}: relaxes {relaxes}")
    meta = plan["metadata"]
    print(f"  With a second van and the kiosk moved: verdict={plan['verdict']}")
    print(f"    engine: {meta['engine']} ({meta['engine_reason']})")
    print(f"    seed {meta['seed_cost']:.1f} km -> optimised {meta['final_cost']:.1f} km "
          f"in a {meta['budget_seconds']:g} s budget")
    for row in plan["solution"]["route_rows"]:
        stops = [PLANNABLE["customers"][i - 1]["id"] for i in row["stops"] if i]
        print(f"    vehicle {row['vehicle']}: {' -> '.join(stops)}  load {row['load']:g}, {row['distance']:.1f} km")
    print(f"    late stops: {len(plan['certificate']['late_stops'])}; not enforced by the search: {plan['not_enforced']}")


def main(license: Any = None, mode: str | None = None) -> None:
    print("=" * 70)
    print(" USE CASE: FLEET ROUTING WITH FEASIBILITY CHECKS AND FALLBACKS ")
    print("=" * 70)
    show_inputs()
    show_feasibility()
    show_suggestions()
    show_constraint_classes()
    show_options(license)
    show_plan(configured_solver(mode, license))
    print("\n" + "=" * 70)


def _license_or_none() -> Any:
    try:
        return HelixorSolver.load_license()
    except FileNotFoundError as exc:
        print(f"(no licence: {exc})")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mode", choices=["embedded", "hosted"],
                        help="embedded: solve in this process; hosted: the Helixor solver service "
                             "(HELIXOR_SOLVER_URL, HELIXOR_SOLVER_TOKEN)")
    args = parser.parse_args()
    main(_license_or_none(), mode=args.mode)
