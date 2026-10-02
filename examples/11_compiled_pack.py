#!/usr/bin/env python3
"""Example 11 · Tier 1: Compile your own pack with a Developer license.

The compile-and-run steps of two tutorials, on the playbooks in playbooks/:

  - internal_ids.yaml ("Add custom rules"): block internal project codes,
    redact ticket numbers, next to the built-in checks;
  - order_notes.yaml ("Write your own decision pack"): your own closed action
    set, with a caller that fails closed on any action it does not expect.

Each playbook is compiled with `helixor-pack compile` into a temporary
directory (a .hxpack is sealed to your license; never commit one), loaded
with HelixorEngine.load_pack(), and evaluated on the tutorials' inputs. The
script checks every action against the tutorial and exits 1 on a mismatch.

Needs your Developer license, in HELIXOR_LICENSE_FILE or at
~/.helixor/helixor.lic. Without one it compiles nothing, prints a line
starting NEEDS_LICENSE and exits 4; run_all.sh reports that as SKIP.

Tutorials: https://helixor.dev/tutorials/custom-rules.html
           https://helixor.dev/tutorials/own-pack.html
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from helixor_runtime import HelixorEngine

ROOT = Path(__file__).resolve().parent.parent
NEEDS_LICENSE_EXIT = 4

INTERNAL_IDS = [  # (input, expected action) from "Add custom rules"
    ("Status for PROJ-ZEUS-9X is green.", "block_internal_project_code"),
    ("See TCK-004211 for the fix.", "redact_ticket_id"),
    ("Email ops@example.com about PROJ-ZEUS-9X.", "block_internal_project_code"),
    ("Lunch is at noon.", "permit_clean_payload"),
]

ORDER_NOTES_ACTIONS = {"permit_clean_payload", "block_internal_cost_code", "block_supplier_reference"}
ORDER_NOTES = [  # (note, expected send) from "Write your own decision pack"
    ("Order ORD-20931 ships Tuesday.", True),
    ("Restock from SUP-QRV-042 next week.", False),
    ("Order ORD-20931 for ops@example.com ships Tuesday.", False),
]


def find_license() -> Path | None:
    """HELIXOR_LICENSE_FILE, then ~/.helixor/helixor.lic (the Python loader's order)."""
    env = os.environ.get("HELIXOR_LICENSE_FILE")
    if env:
        path = Path(env).expanduser()
        if not path.is_file():
            raise SystemExit(f"HELIXOR_LICENSE_FILE points at {path}, which does not exist.")
        return path
    default = Path.home() / ".helixor" / "helixor.lic"
    return default if default.is_file() else None


def helixor_pack() -> str:
    """The helixor-pack command installed next to this interpreter."""
    beside = Path(sys.executable).parent / "helixor-pack"
    found = str(beside) if beside.exists() else shutil.which("helixor-pack")
    if not found:
        raise SystemExit("helixor-pack is not installed; install the runtime wheel (README step 3).")
    return found


def compile_pack(playbook: Path, license_file: Path, out: Path) -> HelixorEngine:
    cmd = [helixor_pack(), "compile", "--playbook", str(playbook),
           "--license", str(license_file), "--out", str(out)]
    print("  $ helixor-pack compile --playbook", playbook.relative_to(ROOT), "--license <your license> --out", out.name)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"compile failed (exit {proc.returncode}):\n{proc.stdout}{proc.stderr}")
    return HelixorEngine.load_pack(out, license_file=license_file)


def run_internal_ids(engine: HelixorEngine) -> int:
    failures = 0
    for text, expected in INTERNAL_IDS:
        d = engine.evaluate(text)
        mark = "ok" if d.action == expected else f"EXPECTED {expected}"
        failures += d.action != expected
        print(f"  {text}")
        print(f"    {d.action}  {[t.rule_id for t in d.triggers]}  {d.remedy.clean_text!r}  [{mark}]")
    return failures


def decide_note(engine: HelixorEngine, note: str) -> dict:
    """The tutorial's send_note.py decision, in process: fail closed on the unexpected."""
    d = engine.evaluate(note)
    if d.action not in ORDER_NOTES_ACTIONS:
        return {"send": False, "why": f"unexpected action {d.action}", "receipt": d.receipt_hash}
    if d.action.startswith("block_"):
        return {"send": False, "why": d.reason, "receipt": d.receipt_hash}
    return {"send": True, "why": "clean", "receipt": d.receipt_hash}


def run_order_notes(engine: HelixorEngine) -> int:
    failures = 0
    for note, expected_send in ORDER_NOTES:
        decision = decide_note(engine, note)
        failures += decision["send"] != expected_send
        print(f"  {note}")
        print(f"     {decision}")
    return failures


def main() -> int:
    print("=" * 70)
    print(" HELIXOR DECISION RUNTIME — YOUR OWN COMPILED PACK (Tier 1) ")
    print("=" * 70)

    license_file = find_license()
    if license_file is None:
        print("NEEDS_LICENSE: compiling a playbook needs your Developer license in "
              "HELIXOR_LICENSE_FILE or at ~/.helixor/helixor.lic. "
              "Request one: https://helixor.dev/guide/account.html#request-access")
        return NEEDS_LICENSE_EXIT

    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        print("\n[1] Add custom rules: playbooks/internal_ids.yaml")
        engine = compile_pack(ROOT / "playbooks" / "internal_ids.yaml", license_file, Path(tmp) / "internal_ids.hxpack")
        if engine.pack_id != "custom.internal_ids.v1":
            raise SystemExit(f"wrong pack loaded: {engine.pack_id}")
        print(f"  Loaded {engine.pack_id} ({engine.tier})")
        failures += run_internal_ids(engine)

        print("\n[2] Your own decision pack: playbooks/order_notes.yaml")
        engine = compile_pack(ROOT / "playbooks" / "order_notes.yaml", license_file, Path(tmp) / "order_notes.hxpack")
        if engine.pack_id != "custom.order_notes.v1":
            raise SystemExit(f"wrong pack loaded: {engine.pack_id}")
        print(f"  Loaded {engine.pack_id} ({engine.tier})")
        failures += run_order_notes(engine)

    print("\n" + "=" * 70)
    if failures:
        print(f" {failures} result(s) differ from the tutorials.")
        return 1
    print(" Every action matches the tutorials.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
