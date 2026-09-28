#!/usr/bin/env python3
"""Use Case: Fleet Vehicle Routing Optimization (VRP).

Business Problem:
    A logistics company dispatches delivery vehicles across stops.
    The solver finds optimal routes respecting vehicle capacity
    constraints — all computed in microseconds on local CPU.

Features Demonstrated:
    • Combinatorial optimization (Vehicle Routing Problem)
    • Capacity constraint enforcement
    • Bin packing / resource allocation
    • Solution verification via TensorConstraintNetwork
"""

from helixor_runtime import HelixorSolver


def main() -> None:
    print("=" * 70)
    print(" USE CASE: FLEET VEHICLE ROUTING OPTIMIZATION ")
    print("=" * 70)

    # ── VRP: Dispatch 12 stops across 3 vehicles ──
    print("\n[1] Solving VRP: 12 stops, 3 vehicles, 80kg capacity...")
    result = HelixorSolver.solve_vrp(
        stops=12,
        fleet_size=3,
        vehicle_capacity=80.0,
    )

    print(f"\n  Solver ID:       {result.solver_id}")
    print(f"  Status:          {result.status}")
    print(f"  Feasible:        {result.feasible}")
    print(f"  Solve Time:      {result.solve_time_us:.1f} µs")
    print(f"  Total Cost:      {result.solution['total_cost']:.1f}")
    print(f"  Stops Dispatched:{result.solution['stops_dispatched']}")

    for route in result.solution.get("routes", []):
        print(f"    {route['vehicle_id']}: {route['stops']} (load={route['load']:.0f}kg, dist={route['distance']:.1f}km)")

    # ── Bin Packing ──
    print("\n" + "-" * 70)
    print("[2] Bin Packing: 8 items into containers (capacity 100)...")
    bp_result = HelixorSolver.solve_bin_packing(
        items=8,
        bin_capacity=100.0,
    )
    print(f"  Bins Used:    {bp_result.solution['bins_required']}")
    print(f"  Feasible:     {bp_result.feasible}")
    print(f"  Utilization:  {bp_result.solution['capacity_utilization']:.0%}")
    print(f"  Solve Time:   {bp_result.solve_time_us:.1f} µs")

    for b in bp_result.solution.get("bins", []):
        print(f"    {b['bin_id']}: {b['items_count']} items, {b['used_capacity']:.0f}/{bp_result.solution['bin_capacity']:.0f} used")

    # ── Constraint Network ──
    print("\n" + "-" * 70)
    print("[3] Custom Constraint Network: operational bounds check...")
    net = HelixorSolver.create_constraint_network()
    net.add_variable("income", lower=0, value=85000)
    net.add_variable("monthly_debt", lower=0, value=2100)
    net.add_variable("loan_amount", lower=0, value=320000)

    consistent = net.propagate()
    summary = net.summary()
    print(f"  Variables:   {summary['variable_count']}")
    print(f"  Constraints: {summary['constraint_count']}")
    print(f"  Consistent:  {consistent}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
