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
