#!/usr/bin/env python3
"""Integration 02 · Decision-as-a-Function with SSE Streaming.

Connect to the hosted Helixor reasoning backend and execute decisions
with real-time Server-Sent Events streaming. Demonstrates the full
server-side decision pipeline: a typed decide call, streaming reasoning
chat over SSE (requires platform auth on the server), and a playbook turn.

Requirements:
    pip install httpx
    export HELIXOR_API_URL=http://127.0.0.1:8030
    export HELIXOR_API_KEY=hlx_...

Tier 2: Requires a Helixor account and running backend.
"""

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


def decide_request() -> dict:
    """DecideRequest for POST /api/v1/decide.

    ``goal`` must be a goal admitted on the server (here the bundled
    security alert triage goal); each question is typed and cites evidence.
    """
    return {
        "goal": "sec.alert_triage.v1",
        "evidence": [
            {
                "id": "alert-1",
                "text": "Login to the payroll admin console from an unrecognised host at 03:12 "
                        "using a service account with no change ticket.",
                "source": "siem",
            },
            {
                "id": "change-1",
                "text": "No maintenance window or approved change covers the payroll console this week.",
                "source": "change_calendar",
            },
        ],
        "questions": [
            {
                "question_id": "unauthorized",
                "family_id": "sec.unauthorized",
                "kind": "boolean",
                "prompt": "Is this access unauthorized?",
                "options": [{"option_id": "true"}, {"option_id": "false"}],
                "context_refs": ["alert-1", "change-1"],
            }
        ],
    }


def chat_stream_request() -> dict:
    """ReasoningChatRequest for POST /api/v1/reasoning/chat/stream."""
    return {
        "message": "Analyze the risk profile of a fleet of 50 delivery vehicles operating in urban zones during peak hours.",
        "mode": "general",
    }


def playbook_turn_request() -> dict:
    """PlaybookTurnRequest for POST /api/v1/reasoning/playbooks/turn."""
    return {
        "pack_id": "compliance.regulatory_pii_guard.v1",
        "message": "Customer John Doe, SSN 456-78-9012, requests balance inquiry.",
    }


def print_verdicts(result: dict) -> None:
    """Print a DecisionResponse: one verdict per question plus the proof id."""
    for question_id, v in result["verdicts"].items():
        print(f"  {question_id}: {v['verdict']} -> {v.get('value')} (p_correct={v.get('p_correct')})")
    print(f"  Proof:    {result.get('proof_id')}")


def main() -> None:
    print("=" * 70)
    print(" INTEGRATION: DECISION-AS-A-FUNCTION WITH SSE STREAMING")
    print("=" * 70)

    # ── 1. REST decision ──
    print("\n[1] REST Decision-as-a-Function...")
    try:
        r = httpx.post(
            f"{API_URL}/api/v1/decide",
            headers=headers(),
            json=decide_request(),
            timeout=15.0,
        )
        if r.status_code == 200:
            result = r.json()
            print_verdicts(result)
            print(f"  Composed: {result['composed']}")
        else:
            print(f"  Status: {r.status_code} — {r.text[:200]}")
    except httpx.ConnectError:
        print(f"  ✗ Cannot reach {API_URL}")
        _show_offline_demo()
        return

    # ── 2. SSE streaming reasoning chat ──
    print("\n[2] SSE Streaming Reasoning Chat...")
    try:
        with httpx.stream(
            "POST",
            f"{API_URL}/api/v1/reasoning/chat/stream",
            headers=headers(),
            json=chat_stream_request(),
            timeout=30.0,
        ) as stream:
            if stream.status_code != 200:
                stream.read()
                print(f"  Status: {stream.status_code} — {stream.text[:200]}")
            else:
                event_count = 0
                for line in stream.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    event_count += 1
                    data = line[5:].strip()
                    if event_count <= 3:
                        preview = data[:80] + "..." if len(data) > 80 else data
                        print(f"  SSE #{event_count}: {preview}")
                    elif event_count == 4:
                        print(f"  ... ({event_count}+ events)")

                print(f"  Total SSE events: {event_count}")
    except httpx.ConnectError:
        print(f"  ✗ Server not reachable for SSE streaming")

    # ── 3. Playbook turn execution ──
    print("\n[3] Interactive Playbook Turn...")
    try:
        r = httpx.post(
            f"{API_URL}/api/v1/reasoning/playbooks/turn",
            headers=headers(),
            json=playbook_turn_request(),
            timeout=10.0,
        )
        if r.status_code == 200:
            result = r.json()
            print(f"  Verdict:  {result['verdict']}")
            print(f"  Move:     {result.get('chosen_move')}")
            print(f"  Reply:    {result.get('reply')}")
        else:
            print(f"  Status: {r.status_code} — {r.text[:200]}")
    except httpx.ConnectError:
        print(f"  ✗ Server not reachable")

    print("\n" + "=" * 70)


def _show_offline_demo():
    """Show what server integration looks like without a live server."""
    print("\n" + "-" * 70)
    print(" SERVER DEMO (offline — showing the API contract)")
    print("-" * 70)
    print("""
  The Helixor Reasoning Backend exposes:

  Decision Endpoints:
    POST /api/v1/decide              — Decision-as-a-Function (REST)
    POST /api/v1/reasoning/chat      — Governed reasoning chat
    POST /api/v1/reasoning/chat/stream — SSE streaming reasoning
    POST /api/v1/reasoning/solve     — Direct reasoning solve

  Playbook Endpoints:
    POST /api/v1/reasoning/playbooks/turn      — Interactive turn
    GET  /api/v1/reasoning/playbooks/list       — List playbooks
    POST /api/v1/reasoning/playbooks/compile    — Compile playbook
    POST /api/v1/reasoning/playbooks/admit      — Admit to runtime

  Developer Endpoints:
    POST /api/v1/developer/signup    — Self-serve signup
    GET  /api/v1/developer/account   — Profile + remaining tokens

  To run this live:
    1. Start the backend: helixor serve
    2. Set HELIXOR_API_URL and HELIXOR_API_KEY
    3. Re-run this example
""")


if __name__ == "__main__":
    main()
