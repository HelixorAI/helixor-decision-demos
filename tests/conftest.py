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
