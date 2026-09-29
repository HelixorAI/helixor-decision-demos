"""Shared helpers for the demo tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent.parent


def load_script(relative: str) -> ModuleType:
    """Import a numbered demo script (e.g. integrations/01_server_evaluate.py) as a module."""
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# The routing and rostering use cases run on the helixor-solvers package, which
# the runtime wheel does not include. Without it those tests are skipped with
# that reason (never passed); with it they run.
SOLVER_USE_CASES = ("fleet_routing", "shift_rostering")


def _solvers_installed() -> bool:
    return importlib.util.find_spec("helixor_solvers") is not None


def pytest_collection_modifyitems(config, items) -> None:
    import pytest

    if _solvers_installed():
        return
    skip = pytest.mark.skip(reason="needs the helixor-solvers package, which the runtime wheel does not include")
    for item in items:
        if any(name in item.name for name in SOLVER_USE_CASES):
            item.add_marker(skip)
