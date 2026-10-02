"""The shipped generated SDK fails fast without a native runtime and checks every contact factor."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


from regulatorypiiguard import RegulatoryPiiGuardClient  # noqa: E402
from regulatorypiiguard.runtime_bridge import NativeRuntimeUnavailableError  # noqa: E402

CLEAN = dict(has_ssn=False, has_credit_card=False, has_health_record=False,
             has_email=False, has_phone=False, has_ip=False)


def test_client_requires_native_runtime_or_explicit_python_evaluator(monkeypatch) -> None:
    monkeypatch.delenv("HELIXOR_RUNTIME_LIB", raising=False)
    with pytest.raises(NativeRuntimeUnavailableError):
        RegulatoryPiiGuardClient()


@pytest.mark.parametrize("factor", ["has_email", "has_phone", "has_ip"])
def test_python_evaluator_refuses_each_contact_identifier(monkeypatch, factor: str) -> None:
    monkeypatch.delenv("HELIXOR_RUNTIME_LIB", raising=False)
    client = RegulatoryPiiGuardClient(allow_python_fallback=True)
    assert client.decide(CLEAN).is_approved
    assert not client.decide({**CLEAN, factor: True}).is_approved
