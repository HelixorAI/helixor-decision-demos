#!/usr/bin/env python3
"""Use Case: Shift Rostering with Feasibility Checks, Suggestions and Fallbacks.

Business Problem:
    A clinic rosters a week of day and night shifts. Night shifts need a
    registered nurse. Before solving, the manager wants to know what the
    solver requires, whether the week can be staffed at all, what to change
    if it cannot, and — if nothing changes in time — the least-bad rosters,
    each saying which rule it breaks and by how much.

Features Demonstrated:
    • Required vs optional inputs, with the defaults the solver applies
    • Pre-solve checks that name the slice (week, skill, location) and the
      exact hour shortfall
    • Parameter suggestions derived from the data: add capacity, or lower
      coverage, or (for skills) a policy change — alternatives, not a fix list
    • Constraint classes: gates never break, hard rules make a roster
      infeasible, soft rules are minimized; skills and max-consecutive-days
      are tenant policy
    • The three least-bad rosters when no roster is feasible (licensed; needs
      the full solver engine installed)
    • Solving in either deployment model, chosen by ONE explicit switch:
      --mode embedded (the solver runs in this process; needs the full engine)
      or --mode hosted (the Helixor solver service). A roster that breaks a
      hard rule is never returned as the solution in either model: the answer
      is "infeasible", with the named shortfalls and ranked alternates.

What the checks prove:
    A failed capacity check certifies that no roster can meet coverage and the
    hour caps together. A passing check proves nothing on its own; the
    solver's feasibility certificate judges every roster it returns.
"""

from __future__ import annotations

import argparse
import os
from typing import Any

from helixor_runtime import HelixorSolver, LicenseError, SolverEngineUnavailableError

STAFF = [
    {"id": "ana", "max_hours": 36, "skills": ["rn"]},
    {"id": "ben", "max_hours": 36, "skills": ["rn"]},
    {"id": "caro", "max_hours": 36},
    {"id": "dev", "max_hours": 24},
    {"id": "eli"},  # no max_hours: the declared default applies
]

# Seven days x (day 08-20, night 20-08). Every night needs one registered nurse.
SHIFTS = [
    {
        "id": f"d{day}-{kind}",
        "day": day,
        "shift_type": kind,
        "start_hour": 8 if kind == "day" else 20,
        "duration": 12,
        "required_staff": 1,
        "required_skills": ["rn"] if kind == "night" else [],
    }
    for day in range(7)
    for kind in ("day", "night")
]

WEEK: dict[str, Any] = {"employees": STAFF, "shifts": SHIFTS}


def show_inputs() -> None:
    print("\n[1] What the solver needs")
    contract = HelixorSolver.describe_inputs("rostering")
    for entity in contract["entities"]:
        required = [c["name"] for c in entity["columns"] if c["required"]]
        defaults = [f"{c['name']}={c['default']}{(' ' + c['unit']) if c.get('unit') else ''}"
                    for c in entity["columns"] if not c["required"] and "default" in c]
        print(f"  {entity['entity']:<10} required: {', '.join(required) or '-'}")
        if defaults:
            print(f"  {'':<10} defaults: {', '.join(defaults)}")
    report = HelixorSolver.validate("rostering", {"employees": [{"name": "no id"}]})
    print(f"  A payload with no ids and no shifts: missing {report['missing']}")
    for default in HelixorSolver.validate("rostering", WEEK)["defaults_in_effect"]:
        print(f"  Default in effect: {default['field']} = {default['default']} on {default['rows']} row(s)")


def show_feasibility() -> None:
    print("\n[2] Pre-solve feasibility checks")
    report = HelixorSolver.check_feasibility("rostering", WEEK)
    totals = report["totals"]
    print(f"  demand {totals['demand_hours']:g}h vs capacity {totals['capacity_hours']:g}h; "
          f"structurally_infeasible={report['structurally_infeasible']}")
    for finding in report["findings"]:
        print(f"  [{finding['severity']}] {finding['check_id']}: {finding['message']}")


def show_suggestions() -> None:
    print("\n[3] Suggested changes (alternatives per shortfall, derived from the data)")
    for s in HelixorSolver.suggest_parameters("rostering", WEEK):
        print(f"  ({s['alternative_group']}) {s['rationale']}")


def show_constraint_classes() -> None:
    print("\n[4] Constraint classes (defaults; tenant policy can move the configurable ones)")
    for row in HelixorSolver.constraint_classes("rostering", WEEK):
        policy = f"  policy {row['policy_key']} (default {row['policy_default']})" if "policy_key" in row else ""
        print(f"  {row['class']:<5} {row['constraint']:<32}{policy}")


def show_options(license: Any) -> None:
    print("\n[5] Least-bad rosters (licensed; full solver engine)")
    try:
        result = HelixorSolver.best_effort_options("rostering", WEEK, license)
    except (LicenseError, SolverEngineUnavailableError) as exc:
        print(f"  Not run: {type(exc).__name__}: {exc}")
        return
    print(f"  status={result['status']}")
    for option in result["options"]:
        breaks = "; ".join(f"{r['constraint']} x{r['count']} ({r['class']})" for r in option["relaxes"]) or "nothing"
        soft = "; ".join(f"{m['constraint']} {m['count']}" for m in option["soft_misses"]) or "none"
        print(f"  #{option['rank']} breaks {breaks}")
        print(f"     soft misses: {soft}")


def configured_solver(mode: str | None, license: Any) -> HelixorSolver | None:
    """The one explicit switch between the two deployment models."""
    if mode == "embedded":
        return HelixorSolver(mode="embedded", license=license)
    if mode == "hosted":
        return HelixorSolver(
            mode="hosted",
            base_url=os.environ["HELIXOR_SOLVER_URL"],
            auth=os.environ["HELIXOR_SOLVER_TOKEN"],
        )
    return None


def show_solve(solver: HelixorSolver | None) -> None:
    print("\n[6] Solve the week")
    if solver is None:
        print("  Not run: choose --mode embedded or --mode hosted (there is no default).")
        return
    try:
        outcome = solver.solve("rostering", WEEK)
    except (LicenseError, SolverEngineUnavailableError) as exc:
        print(f"  Not run: {type(exc).__name__}: {exc}")
        return
    meta = outcome["metadata"]
    print(f"  Served by: {meta['model']}; engine: {meta['engine']}")
    print(f"  verdict={outcome['verdict']}, roster returned as the solution: {outcome['solution'] is not None}")
    for row in outcome["shortfalls"]:
        if row["kind"] == "pre_solve_check":
            print(f"    shortfall: {row['message']}")
        else:
            print(f"    hard rule broken: {row['counter']} x{row['count']}")
    for option in outcome["alternates"][:3]:
        breaks = "; ".join(f"{r['constraint']} x{r['count']} ({r['class']})" for r in option["relaxes"]) or "nothing"
        print(f"    alternate #{option['rank']}: breaks {breaks}")


def main(license: Any = None, mode: str | None = None) -> None:
    print("=" * 70)
    print(" USE CASE: SHIFT ROSTERING WITH FEASIBILITY CHECKS AND FALLBACKS ")
    print("=" * 70)
    show_inputs()
    show_feasibility()
    show_suggestions()
    show_constraint_classes()
    show_options(license)
    show_solve(configured_solver(mode, license))
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
                        help="embedded: solve in this process (full engine); hosted: the Helixor solver "
                             "service (HELIXOR_SOLVER_URL, HELIXOR_SOLVER_TOKEN)")
    args = parser.parse_args()
    main(_license_or_none(), mode=args.mode)
