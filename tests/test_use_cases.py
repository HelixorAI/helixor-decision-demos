"""Use cases compute what they claim."""

from __future__ import annotations

import pytest

from helixor_runtime import HelixorCounterfactualEngine, HelixorForecaster
from tests.conftest import load_script


def test_loan_recourse_denies_then_finds_minimal_debt_paydown(capsys: pytest.CaptureFixture[str]) -> None:
    load_script("use_cases/loan_recourse.py").main()
    out = capsys.readouterr().out
    assert "Approved:    False" in out
    assert "Base decision:        denied" in out
    assert "Flipped to approved:  True" in out
    assert "Minimal change:       monthly_debt 3,200 -> 2,600 (-600)" in out
    assert "Rejected malformed intervention" in out
    assert "Base passes:       True" in out
    assert "Scenarios passed:  1" in out


def test_counterfactual_engine_requires_constraints() -> None:
    with pytest.raises(TypeError):
        HelixorCounterfactualEngine()  # type: ignore[call-arg]


def test_stress_scenarios_must_use_shocks() -> None:
    from helixor_runtime import CounterfactualConfigurationError

    engine = HelixorCounterfactualEngine(constraints=lambda s: [])
    with pytest.raises(CounterfactualConfigurationError, match="shocks"):
        engine.stress_test(base_state={"income": 1.0}, scenarios={"bad": {"income": 0.5}})


def test_demand_forecasting_observations_fit_configured_regimes() -> None:
    results = load_script("use_cases/demand_forecasting.py").main()
    assert all(not obs["unexplained_by_regimes"] for _, _, obs in results)
    assert "surge" in {regime for _, regime, _ in results}


def test_forecaster_reports_observations_outside_every_regime() -> None:
    forecaster = HelixorForecaster()
    forecast = forecaster.forecast_next(current_hour=10)
    obs = forecaster.observe_actual(actual_demand=5.0, forecast=forecast, current_hour=10)
    assert obs["unexplained_by_regimes"] is True


def test_fleet_routing_names_shortfalls_and_suggests_bounds(capsys: pytest.CaptureFixture[str]) -> None:
    load_script("use_cases/fleet_routing.py").main()
    out = capsys.readouterr().out
    assert "vehicles   required: id, capacity" in out
    assert "none is assumed" in out
    assert "shortfall 34 units" in out
    assert "ferry-kiosk: the earliest possible arrival is 8.79h" in out
    assert "n_vehicles: 1 -> at least 2" in out
    assert "vehicle_capacity             hard  enforced by route_admission" in out
    assert "time_windows                 hard  enforced by pre_solve_check" in out
    # Planning needs a licence; without one the step says so, typed.
    assert "Not run: SolverLicenseRequiredError" in out
    # Solving needs the deployment model chosen explicitly; there is no default.
    assert "Not run: choose --mode embedded or --mode hosted (there is no default)." in out


def test_fleet_routing_embedded_solve_needs_a_licence(capsys: pytest.CaptureFixture[str]) -> None:
    load_script("use_cases/fleet_routing.py").main(mode="embedded")
    out = capsys.readouterr().out
    assert out.count("Not run: SolverLicenseRequiredError") == 2


def test_shift_rostering_names_the_skill_shortfall(capsys: pytest.CaptureFixture[str]) -> None:
    load_script("use_cases/shift_rostering.py").main()
    out = capsys.readouterr().out
    assert "employees[].max_hours = 40 on 1 row(s)" in out
    assert "Skill 'rn': demanded coverage is 84h but skill-capable employee capacity is 72h (deficit 12h)" in out
    assert "add at least 12h of capacity from staff holding skill 'rn'" in out
    assert "treat required skills as soft" in out
    assert "gate  no_overlapping_shifts" in out
    assert "Not run: SolverLicenseRequiredError" in out
    assert "Not run: choose --mode embedded or --mode hosted (there is no default)." in out
