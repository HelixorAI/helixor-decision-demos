#!/usr/bin/env python3
"""Integration 03 · Playbook Studio: Compile, Validate, and Admit Playbooks.

Shows the full playbook lifecycle via the Helixor Reasoning Backend:
    1. List available playbooks
    2. Validate a playbook definition
    3. Compile a playbook into executable rules
    4. Admit the compiled playbook into the active runtime
    5. Execute a decision turn against it

This is the Tier 2 (Studio) experience — what developers get when they
log into the Helixor portal and author decision playbooks.

Requirements:
    pip install httpx
    export HELIXOR_API_URL=http://127.0.0.1:8030
    export HELIXOR_API_KEY=hlx_...

Tier 2: Requires Helixor account + Studio access.
"""

import json
import os
import sys

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)


API_URL = os.environ.get("HELIXOR_API_URL", "http://127.0.0.1:8030")
API_KEY = os.environ.get("HELIXOR_API_KEY", "")


def headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if API_KEY:
        h["X-Helixor-API-Key"] = API_KEY
    return h


# A custom playbook for internal project code detection
CUSTOM_PLAYBOOK = {
    "pack_id": "custom.internal_code_guard.v1",
    "goal_id": "custom.internal_code_guard.v1",
    "version": "1.0.0",
    "name": "Internal Project Code Guard",
    "kind": "compliance",
    "description": "Detect and block internal project codes from leaking externally",
    "budget": {"max_latency_ms": 1.0, "max_tokens": 0},
    "floor": 0.90,
    "actions": ["permit_clean_payload", "block_internal_code_leak"],
    "codons": [
        {
            "code": "INTERNAL_PROJECT_CODE",
            "kind": "codon",
            "codon_type": "extract_pattern",
            "trigger": "on_input",
            "params": {"pattern": r"\bPROJ-[A-Z]+-\d+[A-Z]?\b"},
            "binds_to": "has_project_code",
            "matches_field": "project_code_matches",
            "remedy_template": "[REDACTED_PROJECT_CODE]",
        },
    ],
    "hard_rules": [
        {
            "id": "RULE-BLOCK-INTERNAL-CODE",
            "condition": "state.has_project_code == True",
            "action": "block_internal_code_leak",
            "description": "Internal project code detected — block egress",
            "severity": "fatal",
        },
    ],
    "default_action": "permit_clean_payload",
}


COMPILE_PROMPT = (
    "Detect internal project codes shaped like PROJ-ZEUS-9X in outgoing text and block the "
    "message when one is present; otherwise permit it."
)


def compile_request() -> dict:
    """PlaybookCompileRequest for POST /api/v1/reasoning/playbooks/compile."""
    return {
        "prompt": COMPILE_PROMPT,
        "name": CUSTOM_PLAYBOOK["name"],
        "pack_id": CUSTOM_PLAYBOOK["pack_id"],
    }


def admit_request(pack: dict) -> dict:
    """PlaybookAdmitRequest for POST /api/v1/reasoning/playbooks/admit (pack from compile)."""
    return {"pack": pack, "run_preflight_simulation": True}


def turn_request() -> dict:
    """PlaybookTurnRequest for POST /api/v1/reasoning/playbooks/turn."""
    return {
        "pack_id": CUSTOM_PLAYBOOK["pack_id"],
        "message": "The deliverable for PROJ-ZEUS-9X is ready for external review.",
    }


def main() -> None:
    print("=" * 70)
    print(" INTEGRATION: PLAYBOOK STUDIO — COMPILE & ADMIT")
    print("=" * 70)

    # ── 1. List available playbooks ──
    print("\n[1] Listing available playbooks...")
    try:
        r = httpx.get(f"{API_URL}/api/v1/reasoning/playbooks/list", headers=headers(), timeout=5.0)
        if r.status_code == 200:
            packs = r.json()  # a JSON array of playbook summaries
            print(f"  Available: {len(packs)} playbook(s)")
            for p in packs[:5]:
                print(f"    • {p.get('pack_id', p.get('name', '?'))}")
        else:
            print(f"  Status: {r.status_code}")
    except httpx.ConnectError:
        print(f"  ✗ Cannot reach {API_URL}")
        _show_offline_demo()
        return

    # ── 2. Validate custom playbook ──
    print("\n[2] Validating custom playbook...")
    r = httpx.post(
        f"{API_URL}/api/v1/reasoning/playbooks/validate",
        headers=headers(),
        json=CUSTOM_PLAYBOOK,
        timeout=10.0,
    )
    if r.status_code == 200:
        result = r.json()
        print(f"  Valid:    {result.get('valid', '?')}")
        errors = result.get("errors", [])
        warnings = result.get("warnings", [])
        if errors:
            print(f"  Errors:  {errors}")
        if warnings:
            print(f"  Warnings: {warnings}")
    else:
        print(f"  Status: {r.status_code}")

    # ── 3. Compile playbook ──
    print("\n[3] Compiling playbook into executable rules...")
    r = httpx.post(
        f"{API_URL}/api/v1/reasoning/playbooks/compile",
        headers=headers(),
        json=compile_request(),
        timeout=15.0,
    )
    if r.status_code != 200:
        print(f"  Status: {r.status_code} — {r.text[:200]}")
        return
    compiled = r.json()
    print(f"  Compiler:   {compiled['compiler_mode']}")
    print(f"  Executable: {compiled['is_executable']}")
    print(f"  Hard rules: {len(compiled['pack'].get('hard_rules', []))}")

    # ── 4. Admit to runtime ──
    print("\n[4] Admitting playbook into active runtime...")
    r = httpx.post(
        f"{API_URL}/api/v1/reasoning/playbooks/admit",
        headers=headers(),
        json=admit_request(compiled["pack"]),
        timeout=10.0,
    )
    if r.status_code == 200:
        print(f"  Admission: {json.dumps(r.json())[:200]}")
    else:
        print(f"  Status: {r.status_code} — {r.text[:200]}")
        return

    # ── 5. Execute turn ──
    print("\n[5] Executing decision turn against compiled playbook...")
    r = httpx.post(
        f"{API_URL}/api/v1/reasoning/playbooks/turn",
        headers=headers(),
        json=turn_request(),
        timeout=10.0,
    )
    if r.status_code == 200:
        result = r.json()
        print(f"  Verdict: {result['verdict']}")
        print(f"  Move:    {result.get('chosen_move')}")
    else:
        print(f"  Status: {r.status_code} — {r.text[:200]}")

    print("\n" + "=" * 70)
    print(" This is the Studio workflow: author → validate → compile → admit.")
    print(" Custom playbooks extend the runtime without touching source code.")
    print("=" * 70)


def _show_offline_demo():
    print("\n" + "-" * 70)
    print(" PLAYBOOK STUDIO (offline — showing the workflow)")
    print("-" * 70)
    print(f"""
  The Playbook Studio lifecycle:

  1. AUTHOR:   Write a YAML playbook with codons + hard rules
  2. VALIDATE: POST /api/v1/reasoning/playbooks/validate
  3. COMPILE:  POST /api/v1/reasoning/playbooks/compile
  4. ADMIT:    POST /api/v1/reasoning/playbooks/admit
  5. EXECUTE:  POST /api/v1/reasoning/playbooks/turn

  Custom playbook definition:
{json.dumps(CUSTOM_PLAYBOOK, indent=2)[:500]}...

  To run live: start backend + set HELIXOR_API_URL
""")


if __name__ == "__main__":
    main()
