"""The README's commands and the examples' outputs match a fresh run.

This is scripts/check_docs.py as a test; see its docstring and the README's
"Keeping docs and outputs honest". It needs the runtime wheels installed.
"""

from __future__ import annotations

import pytest

pytest.importorskip("helixor_runtime", reason="needs the licensed runtime wheels (README step 3)")

from scripts import check_docs  # noqa: E402


def test_example_outputs_match_tests_expected() -> None:
    problems = check_docs.check_examples(update=False)
    assert not problems, "\n".join(problems)


def test_readme_verify_blocks_match_a_fresh_run() -> None:
    problems = check_docs.check_readme()
    assert not problems, "\n".join(problems)


def test_every_pinned_example_has_an_expected_output() -> None:
    missing = [p for p in check_docs.PINNED if not check_docs.expected_path(p).exists()]
    assert not missing, missing


def test_trimmed_output_matching() -> None:
    actual = ["a", "Latency: 12.5 µs", "b", "c"]
    assert check_docs.contains_in_order(["a", "...", "Latency: 99.0 µs", "c"], actual) is None
    assert check_docs.contains_in_order(["c", "a"], actual) == "a"
