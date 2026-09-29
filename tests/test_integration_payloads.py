"""Every request body the integration scripts send matches the reasoning backend OpenAPI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tests.conftest import load_script

SPEC = json.loads((Path(__file__).parent / "contracts" / "reasoning-backend.openapi.json").read_text())


def _request_validator(path: str, method: str = "post") -> Draft202012Validator:
    schema = SPEC["paths"][path][method]["requestBody"]["content"]["application/json"]["schema"]
    return Draft202012Validator({**schema, "components": SPEC["components"]})


def _assert_valid(path: str, body: dict, method: str = "post") -> None:
    errors = sorted(_request_validator(path, method).iter_errors(body), key=str)
    assert not errors, f"{method.upper()} {path}: " + "; ".join(e.message for e in errors)


MINIMAL_PACK = {
    "pack_id": "custom.internal_code_guard.v1",
    "goal_id": "custom.internal_code_guard.v1",
    "actions": ["permit_clean_payload", "block_internal_code_leak"],
}

m01 = load_script("integrations/01_server_evaluate.py")
m02 = load_script("integrations/02_server_decision.py")
m03 = load_script("integrations/03_playbook_studio.py")
m04 = load_script("integrations/04_ontology_binding.py")

CASES = [
    ("/api/v1/reasoning/playbooks/turn", m01.pii_turn_request(), "post"),
    ("/api/v1/decide", m02.decide_request(), "post"),
    ("/api/v1/reasoning/chat/stream", m02.chat_stream_request(), "post"),
    ("/api/v1/reasoning/playbooks/turn", m02.playbook_turn_request(), "post"),
    ("/api/v1/reasoning/playbooks/validate", m03.CUSTOM_PLAYBOOK, "post"),
    ("/api/v1/reasoning/playbooks/compile", m03.compile_request(), "post"),
    ("/api/v1/reasoning/playbooks/admit", m03.admit_request(MINIMAL_PACK), "post"),
    ("/api/v1/reasoning/playbooks/turn", m03.turn_request(), "post"),
    ("/api/v1/reasoning/ontology/config", m04.ontology_config_request("schema_version: x"), "put"),
]


@pytest.mark.parametrize("path, body, method", CASES, ids=[f"{m}:{p}" for p, _, m in CASES])
def test_request_body_matches_openapi(path: str, body: dict, method: str) -> None:
    _assert_valid(path, body, method)


def test_old_payload_shapes_are_rejected() -> None:
    """The shapes the scripts used to send fail the contract."""
    with pytest.raises(AssertionError):
        _assert_valid("/api/v1/decide", {"prompt": "x", "domain": "compliance"})
    with pytest.raises(AssertionError):
        _assert_valid("/api/v1/reasoning/playbooks/turn", {"pack_id": "p", "turn_input": {"text": "x"}})
    with pytest.raises(AssertionError):
        _assert_valid("/api/v1/reasoning/playbooks/admit", {"pack_id": "p"})


def test_decide_goal_is_an_admitted_goal_id() -> None:
    assert m02.decide_request()["goal"] == "sec.alert_triage.v1"
