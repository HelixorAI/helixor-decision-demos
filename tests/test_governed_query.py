"""integrations/05 fails closed, and its opt-in simulation never passes for a real result."""

from __future__ import annotations

import pytest

from tests.conftest import load_script

m05 = load_script("integrations/05_governed_query.py")


def test_default_run_fails_closed(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        m05.main([])
    assert exc.value.code == m05.EXIT_UNAVAILABLE == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("UNAVAILABLE: governed data access")
    assert "nothing was queried" in captured.err


def test_governed_query_raises_instead_of_returning_rows() -> None:
    with pytest.raises(m05.GovernedDataUnavailable):
        m05.governed_query(realm="r", role_id="SupplierAnalyst_EMEA", concept="Supplier")


def test_every_simulated_line_is_labelled_and_nothing_claims_verification(
    capsys: pytest.CaptureFixture[str],
) -> None:
    m05.main(["--simulate"])
    lines = capsys.readouterr().out.splitlines()
    assert lines
    assert all(line.startswith("[SIMULATION]") for line in lines), [l for l in lines if not l.startswith("[SIMULATION]")]
    text = "\n".join(lines).lower()
    assert "verif" not in text
    assert "true" not in text


def test_simulated_results_are_marked_and_policy_differs_by_role() -> None:
    analyst = m05.simulate_governed_query("r", "SupplierAnalyst_EMEA", "Supplier")
    auditor = m05.simulate_governed_query("r", "ComplianceAuditor_Global", "Supplier")
    for result in (analyst, auditor):
        assert result["simulation"] is True
        assert "verified" not in result
    assert all("taxIdentifier" not in row for row in analyst["rows"])
    assert analyst["withheldFields"][0]["field"] == "taxIdentifier"
    assert all(row["taxIdentifier"].startswith("SIM-") for row in auditor["rows"])
    assert auditor["withheldFields"] == []


def test_receipt_digest_is_recomputed_and_catches_a_changed_row() -> None:
    result = m05.simulate_governed_query("r", "SupplierAnalyst_EMEA", "Supplier")
    assert m05.recompute_receipt_digest(result)["digestMatches"] is True
    tampered = dict(result, rows=[dict(result["rows"][0], dailyCapacityTons=1)] + result["rows"][1:])
    check = m05.recompute_receipt_digest(tampered)
    assert check["simulation"] is True
    assert check["digestMatches"] is False
