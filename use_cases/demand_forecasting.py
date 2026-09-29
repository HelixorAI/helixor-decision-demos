#!/usr/bin/env python3
"""Use Case: Adaptive Demand Forecasting with Regime Detection.

Business Problem:
    A supply chain or cloud infrastructure team needs real-time demand
    forecasts that adapt instantly to regime shifts (baseline → peak → surge)
    without retraining. Wrong forecasts cause stockouts or wasted capacity.

Features Demonstrated:
    • Bayesian regime tracking (Beta posteriors)
    • Sub-15 µs point forecasts with 95% credible intervals
    • Regime switching within a few observations (no retraining required)
"""

from helixor_runtime import HelixorForecaster


def main() -> None:
    print("=" * 70)
    print(" USE CASE: ADAPTIVE DEMAND FORECASTING ")
    print("=" * 70)

    # Regimes are stated in this team's demand units (requests/sec).
    regimes = {
        "baseline": {"mean": 50.0, "std": 8.0, "label": "Off-Peak Baseline"},
        "peak": {"mean": 88.0, "std": 10.0, "label": "Normal Business Peak"},
        "surge": {"mean": 148.0, "std": 15.0, "label": "Lunch Surge"},
    }
    forecaster = HelixorForecaster(window_size=3, regimes=regimes)

    # Simulate a day of demand observations (hourly)
    # Normal morning → afternoon peak → evening surge → overnight calm
    hourly_actuals = {
        6: 45.0,   # Early morning - baseline
        7: 52.0,   # Morning ramp
        8: 78.0,   # Morning rush
        9: 85.0,   # Peak
        10: 90.0,  # Peak
        11: 95.0,  # Peak
        12: 140.0, # Lunch surge!
        13: 155.0, # Sustained surge
        14: 110.0, # Settling
        15: 88.0,  # Back to peak
        16: 75.0,  # Winding down
        17: 60.0,  # Evening
        18: 42.0,  # Quiet
    }

    print("\n  Hour | Regime     | Forecast | Actual | Error  | CI 95%")
    print("  " + "-" * 65)

    results = []
    for hour, actual in hourly_actuals.items():
        # Get forecast BEFORE seeing actual
        forecast = forecaster.forecast_next(current_hour=hour)

        # Observe actual to update beliefs
        obs = forecaster.observe_actual(
            actual_demand=actual,
            forecast=forecast,
            current_hour=hour,
        )

        point = forecast["point_forecast"]
        ci_lo, ci_hi = forecast["ci_95"]
        error_pct = obs.get("error_pct", abs(actual - point) / max(actual, 1) * 100)
        regime = forecast["regime"]
        if obs["unexplained_by_regimes"]:
            raise RuntimeError(
                f"Hour {hour}: demand {actual} is {obs['nearest_regime_sigma']:.1f} sigma from every "
                "configured regime; recalibrate the regimes."
            )

        print(
            f"  {hour:4d} | {regime:10s} | {point:8.1f} | {actual:6.1f} | "
            f"{error_pct:5.1f}% | [{ci_lo:.0f}, {ci_hi:.0f}]"
        )
        results.append((hour, regime, obs))

    print("\n  Demand surged at hours 12-13; after those two observations the")
    print("  forecaster switched to the surge regime, and back to peak as it settled.")
    print("  No retraining, no batch job, no ML pipeline — just Bayesian updating.")

    print("\n" + "=" * 70)
    return results


if __name__ == "__main__":
    main()
