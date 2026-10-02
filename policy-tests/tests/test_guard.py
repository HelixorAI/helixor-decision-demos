"""Golden, property, latency and streaming tests for the built-in example pack.

From the "Testing policies" tutorial: https://helixor.dev/tutorials/testing-policies.html
Run from this directory: `python -m pytest -v` (33 tests).
"""

import statistics
import time

import pytest

from helixor_runtime import HelixorEngine

from golden import GOLDEN


@pytest.fixture(scope="module")
def engine():
    return HelixorEngine()


@pytest.mark.parametrize("text,action,rule_ids", GOLDEN)
def test_golden(engine, text, action, rule_ids):
    d = engine.evaluate(text)
    assert d.action == action
    assert [t.rule_id for t in d.triggers] == rule_ids
    assert d.invariants_passed == (action == "permit_clean_payload")


@pytest.mark.parametrize("text,action,rule_ids", GOLDEN)
def test_clean_text_never_contains_a_match(engine, text, action, rule_ids):
    d = engine.evaluate(text)
    for trigger in d.triggers:
        for item in trigger.matched_items:
            assert item not in d.remedy.clean_text


def test_permit_returns_input_unchanged(engine):
    text = "Move the design review to Thursday."
    assert engine.evaluate(text).remedy.clean_text == text


def test_dict_input_matches_string_input(engine):
    text = "Send the deck to dana.reyes@example.com."
    assert engine.evaluate({"message": text}).action == engine.evaluate(text).action


def test_receipts_are_deterministic(engine):
    text = "Applicant SSN 123-45-6789 verified."
    assert engine.evaluate(text).receipt_hash == engine.evaluate(text).receipt_hash


def test_embedded_evaluation_has_no_egress(engine):
    d = engine.evaluate("Send the deck to dana.reyes@example.com.")
    assert d.tokens_spent == 0 and d.egress_bytes == 0


def test_latency_budget(engine):
    texts = [g.values[0] for g in GOLDEN]
    engine.evaluate(texts[0])  # warm up
    samples = []
    for _ in range(50):
        for text in texts:
            t0 = time.perf_counter()
            engine.evaluate(text)
            samples.append((time.perf_counter() - t0) * 1e6)
    p50 = statistics.median(samples)
    # Loose, wall-clock budget: catches order-of-magnitude regressions,
    # not noise on shared CI runners.
    assert p50 < 2_000, f"p50 {p50:.0f} µs"


STREAMED = "Reach support at support@example.com or call (415) 555-0100."


def chunks(text, size):
    return [text[i : i + size] for i in range(0, len(text), size)]


@pytest.mark.parametrize("size", [1, 2, 3, 5, 8, 64])
def test_streaming_matches_block_redaction(engine, size):
    streamed = "".join(engine.stream_filter(chunks(STREAMED, size)))
    assert streamed == engine.evaluate(STREAMED).remedy.clean_text
