#!/usr/bin/env python3
"""Example 03 · Tier 0: Clone & Run — LLM Prompt Privacy Gateway.

Demonstrates the runtime as an inline decision point for outbound LLM
requests: inspect every prompt before it reaches a hosted LLM.
Fatal violations (SSN, credit cards) are blocked. Contact PII is redacted.
"""

from typing import Any

from helixor_runtime import HelixorEngine


class SecureLLMGateway:
    """In-memory security boundary for outbound LLM requests."""

    def __init__(self) -> None:
        self.engine = HelixorEngine()

    def sanitize_and_dispatch(self, user_prompt: str) -> dict[str, Any]:
        """Inspect prompt through the runtime before allowing network dispatch."""
        verdict = self.engine.evaluate(user_prompt)

        if verdict.action.startswith("block"):
            return {
                "status": "BLOCKED_BY_POLICY",
                "reason": verdict.reason,
                "triggers": [t.rule_id for t in verdict.triggers],
                "receipt_hash": verdict.receipt_hash,
                "dispatched_to_network": False,
            }

        return {
            "status": "DISPATCHED_CLEAN",
            "original_prompt": user_prompt,
            "sanitized_outgoing_prompt": verdict.remedy.clean_text,
            "receipt_hash": verdict.receipt_hash,
            "dispatched_to_network": True,
            "latency_us": verdict.latency_us,
        }


def main() -> None:
    print("=" * 70)
    print(" HELIXOR DECISION RUNTIME — LLM PROMPT PRIVACY INTERCEPTOR ")
    print("=" * 70)

    gateway = SecureLLMGateway()

    prompts = [
        "Summarize this meeting: We agreed on a 15% discount for Acme Corp.",
        "Please extract balance sheet data for applicant with SSN 123-45-6789.",
        "Draft a follow-up email to client at david@client.com or call (415) 555-0182.",
    ]

    for p in prompts:
        print(f'\n[Incoming Prompt]: "{p}"')
        res = gateway.sanitize_and_dispatch(p)

        print(f"  Status:     {res['status']}")
        print(f"  Dispatched: {res['dispatched_to_network']}")
        print(f"  Receipt:    {res['receipt_hash']}")

        if res["status"] == "BLOCKED_BY_POLICY":
            print(f"  >> BLOCKED: {res['reason']}")
        else:
            print(f'  >> SANITIZED: "{res["sanitized_outgoing_prompt"]}"')


if __name__ == "__main__":
    main()
