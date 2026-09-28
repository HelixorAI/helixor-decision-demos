"""Playbooks parse, docs reference only real commands, no third-party company names."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TEXT_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".json", ".hxlic", ".sh"}
SKIPPED = {".git", "__pycache__", ".pytest_cache", "contracts", "sdks"}
# Third-party company names that must never appear. Stored as truncated SHA-256
# digests of the lower-cased name (spaces removed) so this public file does not
# itself name them. Add one with:
#   python -c "import hashlib,sys; print(hashlib.sha256(sys.argv[1].lower().replace(' ', '').encode()).hexdigest()[:16])" NAME
BANNED_NAME_DIGESTS = frozenset({
    "41a24366212bb5c1",
    "45cd2fb5a1701292",
    "4ef9bfe6a5402861",
    "57090017a8df3027",
    "77c8810846d2773f",
    "84316121a26ffa3e",
    "9e66a118b9a0fb8c",
    "bc74d4c225d5b7d9",
    "cb5c36fe59056a6a",
})
_WORD = re.compile(r"[a-z0-9]+")


def _banned_name_in(line: str) -> bool:
    words = _WORD.findall(line.lower())
    candidates = set(words) | {a + b for a, b in zip(words, words[1:])}
    return any(hashlib.sha256(c.encode()).hexdigest()[:16] in BANNED_NAME_DIGESTS for c in candidates)


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


def test_no_third_party_company_names() -> None:
    hits = []
    for path in _text_files():
        for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
            if _banned_name_in(line):
                hits.append(f"{path.relative_to(ROOT)}:{lineno}")
    assert not hits, hits


# Claims the 0.2.x pure-Python runtime does not meet (defect_0bedaefc). A doc may only
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
    assert "https://helixor.dev/legal/license-agreement.html" in notice
