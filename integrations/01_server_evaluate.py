#!/usr/bin/env python3
"""Integration 01 · Connect to the Hosted Helixor Reasoning API.

Instead of running the runtime locally, connect to the hosted service
at your Helixor backend. The same decision semantics — statutory PII
evaluation, solver dispatch, playbook execution — but over REST/SSE.

Requirements:
    pip install httpx
    export HELIXOR_API_URL=http://127.0.0.1:8030  # or your hosted endpoint
    export HELIXOR_API_KEY=hlx_...                 # your API key

Tier 2: Requires a Helixor account and API key.
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


def pii_turn_request() -> dict:
    """PlaybookTurnRequest for POST /api/v1/reasoning/playbooks/turn."""
    return {
        "pack_id": "compliance.regulatory_pii_guard.v1",
        "message": "Please process the refund for SSN 123-45-6789 on card 4111-1111-1111-1111.",
    }


def main() -> None:
    print("=" * 70)
    print(" INTEGRATION: HOSTED HELIXOR REASONING API")
    print("=" * 70)

    # ── Health Check ──
    print("\n[1] Health check...")
    try:
        r = httpx.get(f"{API_URL}/api/v1/health", headers=headers(), timeout=5.0)
        r.raise_for_status()
        health = r.json()
        print(f"  Status:       {health['status']}")
        print(f"  Version:      {health['version']}")
        print(f"  Capabilities: {health['capabilities_loaded']}/{health['capabilities_total']} loaded")
    except httpx.ConnectError:
        print(f"  ✗ Cannot reach {API_URL}")
        print(f"    Start the server or set HELIXOR_API_URL")
        print(f"    For local testing: python -m helixor_runtime.server")
        return
    except Exception as e:
        print(f"  ✗ {e}")
        return

    # ── PII evaluation through the regulatory PII playbook ──
    print("\n[2] PII evaluation (compliance.regulatory_pii_guard.v1)...")
    r = httpx.post(
        f"{API_URL}/api/v1/reasoning/playbooks/turn",
        headers=headers(),
        json=pii_turn_request(),
        timeout=10.0,
    )
    if r.status_code == 200:
        result = r.json()
        print(f"  Verdict:  {result['verdict']}")
        print(f"  Move:     {result.get('chosen_move')}")
        print(f"  Rules:    {result.get('rule_ids')}")
    else:
        print(f"  Status: {r.status_code} — {r.text[:200]}")

    # ── Playbook listing ──
    print("\n[3] Available playbooks...")
    r = httpx.get(f"{API_URL}/api/v1/reasoning/playbooks/list", headers=headers(), timeout=5.0)
    if r.status_code == 200:
        packs = r.json()  # a JSON array of playbook summaries
        for p in packs[:5]:
            name = p.get("pack_id", p.get("name", "?"))
            print(f"  • {name}")
        if len(packs) > 5:
            print(f"  ... and {len(packs) - 5} more")
    else:
        print(f"  Status: {r.status_code}")

    # ── Ontology config ──
    print("\n[4] Ontology configuration...")
    r = httpx.get(f"{API_URL}/api/v1/reasoning/ontology/config", headers=headers(), timeout=5.0)
    if r.status_code == 200:
        config = r.json()
        print(f"  Ontology config keys: {sorted(config)}")
    else:
        print(f"  Status: {r.status_code}")

    print("\n" + "=" * 70)
    print(" This example connects to the real Helixor backend.")
    print(" The same decision semantics as the local runtime,")
    print(" but with playbook studio, ontology bindings, and audit ledger.")
    print("=" * 70)


if __name__ == "__main__":
    main()
