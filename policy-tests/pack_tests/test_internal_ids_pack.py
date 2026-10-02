"""Tests for the pack compiled from playbooks/internal_ids.yaml (Developer license).

From the "Testing policies" tutorial: https://helixor.dev/tutorials/testing-policies.html

    POLICY_PACK=internal_ids.hxpack POLICY_LICENSE="$HOME/.helixor/helixor.hxlic" \
        python -m pytest -v pack_tests

It fails with a KeyError if either variable is unset, and with
FileNotFoundError if either file is missing. That is deliberate: a pack test
that silently skips is not a test. The default `python -m pytest` in this
directory does not collect it (testpaths = tests).
"""

import os

import pytest

from helixor_runtime import HelixorEngine

PACK = os.environ["POLICY_PACK"]          # e.g. internal_ids.hxpack
LICENSE = os.environ["POLICY_LICENSE"]    # e.g. ~/.helixor/helixor.hxlic


@pytest.fixture(scope="module")
def engine():
    engine = HelixorEngine.load_pack(PACK, license_file=LICENSE)
    assert engine.pack_id == "custom.internal_ids.v1"
    return engine


@pytest.mark.parametrize("text,action", [
    pytest.param("Status for PROJ-ZEUS-9X is green.", "block_internal_project_code", id="project-code"),
    pytest.param("Kickoff PROJ-APOLLO-12 tomorrow.", "block_internal_project_code", id="other-project"),
    pytest.param("Email ops@example.com about PROJ-ZEUS-9X.", "block_internal_project_code", id="code+email"),
    pytest.param("See TCK-004211 for the fix.", "redact_ticket_id", id="ticket"),
    pytest.param("The PROJ-ZEUS team meets today.", "permit_clean_payload", id="no-number"),
    pytest.param("Lunch is at noon.", "permit_clean_payload", id="clean"),
])
def test_pack_actions(engine, text, action):
    assert engine.evaluate(text).action == action


def test_redact_rule_removes_the_ticket(engine):
    assert "TCK-004211" not in engine.evaluate("See TCK-004211 for the fix.").remedy.clean_text
