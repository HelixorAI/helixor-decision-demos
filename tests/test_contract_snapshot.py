"""The public contract snapshot carries only the operations the integration scripts call."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

CONTRACTS = Path(__file__).resolve().parent / "contracts"
SNAPSHOT = json.loads((CONTRACTS / "reasoning-backend.openapi.json").read_text())


def _pruner():
    spec = importlib.util.spec_from_file_location("prune_openapi", CONTRACTS / "prune_openapi.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_snapshot_holds_only_allow_listed_operations() -> None:
    allowed = _pruner().OPERATIONS
    assert set(SNAPSHOT["paths"]) == set(allowed)
    for path, methods in SNAPSHOT["paths"].items():
        assert set(methods) == set(allowed[path]), path


def test_snapshot_is_its_own_pruned_form() -> None:
    """Re-pruning is a no-op: no schema is carried that the allow-listed operations don't reference."""
    assert _pruner().prune(SNAPSHOT) == SNAPSHOT
