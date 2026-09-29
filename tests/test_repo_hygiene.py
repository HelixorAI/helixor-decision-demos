"""Playbooks parse, docs reference only real commands, nothing internal leaks."""

from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
TEXT_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".json", ".hxlic", ".sh"}
# Local virtual environments (the README creates .venv inside the clone) hold
# third-party and runtime code that is not part of this repository.
SKIPPED = {".git", "__pycache__", ".pytest_cache", "contracts", "sdks", ".venv", "venv", "env"}
# Third-party names are checked by a private pre-publish scanner, not here: a
# list in a public file (even hashed) names what it bans. Point this test at a
# names file (one name per line) to run the same check locally.
NAMES_FILE_ENV = "HELIXOR_PREPUBLISH_NAMES_FILE"
_WORD = re.compile(r"[a-z0-9]+")


def _text_files():
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix in TEXT_SUFFIXES and not SKIPPED & set(path.parts):
            if path != Path(__file__).resolve():
                yield path


def test_playbooks_are_valid_yaml() -> None:
    for playbook in (ROOT / "playbooks").glob("*.yaml"):
        assert isinstance(yaml.safe_load(playbook.read_text()), dict), playbook


def test_no_reference_to_nonexistent_license_activate_command() -> None:
    hits = [str(p.relative_to(ROOT)) for p in _text_files() if "license activate" in p.read_text()]
    assert not hits, hits


def test_no_names_from_the_prepublish_list() -> None:
    names_file = os.environ.get(NAMES_FILE_ENV)
    if not names_file:
        pytest.skip(f"set {NAMES_FILE_ENV} to a names file to run this check; the pre-publish scan always runs it")
    names = {
        line.strip().lower().replace(" ", "")
        for line in Path(names_file).read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }
    assert names, f"{names_file} lists no names"
    hits = []
    for path in _text_files():
        for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
            words = _WORD.findall(line.lower())
            if names & (set(words) | {a + b for a, b in zip(words, words[1:])}):
                hits.append(f"{path.relative_to(ROOT)}:{lineno}")
    assert not hits, hits


INTERNAL_REFERENCE = re.compile(r"\bdefect_[0-9a-f]{8}|github\.com/HelixorAI/(?!helixor-decision-demos\b)[\w.-]+")


def test_no_internal_references() -> None:
    """No internal defect ids, and no links to other (private) repositories."""
    hits = []
    for path in _text_files():
        for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
            if INTERNAL_REFERENCE.search(line):
                hits.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()[:100]}")
    assert not hits, hits


def test_runtime_is_not_an_install_requirement() -> None:
    """helixor-runtime is not on a public index; declaring it invites dependency confusion."""
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    deps = pyproject["project"]["dependencies"] + [
        d for extra in pyproject["project"].get("optional-dependencies", {}).values() for d in extra
    ]
    assert not [d for d in deps if re.match(r"helixor[-_]runtime\b", d, re.IGNORECASE)], deps
    requirements = ROOT / "requirements.txt"
    assert not requirements.exists() or "helixor-runtime" not in requirements.read_text()


def test_license_is_the_full_apache_text() -> None:
    text = (ROOT / "LICENSE").read_text()
    assert "TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION" in text
    assert "END OF TERMS AND CONDITIONS" in text


# Claims the 0.3.x pure-Python runtime does not meet. A doc may only
# mention them to say they are *not* met or are planned, never as a current property.
OVERCLAIMS = re.compile(
    r"opaque (in-memory )?(decision )?enclave|compiled (native )?(runtime )?binary|zero visibility|"
    r"never sees the internals|executes opaquely",
    re.IGNORECASE,
)
DISCLAIMER = re.compile(r"\b(not|planned|no opacity)\b", re.IGNORECASE)


def test_docs_do_not_overclaim_the_runtime() -> None:
    hits = []
    for path in _text_files():
        if path.suffix != ".md":
            continue
        for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
            if OVERCLAIMS.search(line) and not DISCLAIMER.search(line):
                hits.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")
    assert not hits, hits


def test_architecture_doc_states_the_shipped_security_model() -> None:
    doc = (ROOT / "docs" / "ARCHITECTURE.md").read_text()
    assert "pure-Python reference" in doc
    assert "content key is carried inside the `.hxlic`" in doc


# This repository is public; the Helixor runtime is proprietary and licensed separately.
RUNTIME_SOURCE_DIRS = ("pii_guard", "helixor_runtime", "native", "codon_runtime")
INTERNAL_IMPORT = re.compile(r"^\s*(from|import)\s+pii_guard\b", re.MULTILINE)


def test_no_runtime_source_is_vendored() -> None:
    present = [d for d in RUNTIME_SOURCE_DIRS if (ROOT / d).exists()]
    assert not present, f"runtime source must not be vendored into the public demos: {present}"
    for path in ROOT.rglob("*.py"):
        if SKIPPED & set(path.parts):
            continue
        assert not INTERNAL_IMPORT.search(path.read_text()), f"{path.relative_to(ROOT)} imports runtime internals"


def test_notice_states_the_runtime_is_proprietary() -> None:
    notice = (ROOT / "NOTICE").read_text()
    assert "Apache License, Version 2.0" in notice
    assert "helixor-software-license-agreement-v1" in notice
    assert "helixor.dev/legal" not in notice  # no published agreement page exists yet
