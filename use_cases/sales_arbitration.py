#!/usr/bin/env python3
"""Use Case: Enterprise Sales Dialogue Arbitration.

Business Problem:
    A B2B sales team needs every customer interaction to follow
    compliance rules: no premature pricing, no unauthorized contact
    harvesting, mandatory battle card citations, and PII redaction
    in the conversation transcript — all enforced deterministically.

Features Demonstrated:
    • Intent classification (inquiry, pricing, objection, contact)
    • Dialogue legality invariants (cold-open rules)
    • Battle card citation enforcement
    • Zero-egress PII redaction in conversation flow
    • Sub-50 µs per-turn evaluation
"""

from helixor_runtime import HelixorSalesEngine


def main() -> None:
    print("=" * 70)
    print(" USE CASE: ENTERPRISE SALES DIALOGUE ARBITRATION ")
    print("=" * 70)

    engine = HelixorSalesEngine()
    print(f"\n  Pack: {engine.pack_id}")

    # Simulate a multi-turn sales conversation
    conversation = [
        "Hi, I'm interested in learning about your compliance platform.",
        "What regulations does it cover? We're in financial services.",
        "How much does the enterprise plan cost?",
        "Can you send the proposal to sarah.cfo@example.com?",
        "Another vendor quoted us $0.042 per million tokens. Can you match that?",
    ]

    slots: dict[str, str] = {}

    for turn_idx, message in enumerate(conversation, start=1):
        print(f"\n{'─' * 70}")
        print(f"  [Turn {turn_idx}] Customer: \"{message}\"")

        result = engine.evaluate_turn(
            message=message,
            session_slots=slots,
            turn_index=turn_idx,
        )

        print(f"  Intent:      {result.intent} ({result.intent_confidence:.0%})")
        print(f"  Sentiment:   {result.sentiment}")
        print(f"  Action:      {result.action}")
        print(f"  Rule:        {result.rule_id}")
        print(f"  Latency:     {result.latency_us:.1f} µs")

        if result.citations:
            print(f"  Citations:   {result.citations}")

        if result.reply:
            reply_preview = result.reply[:120] + "..." if len(result.reply) > 120 else result.reply
            print(f"  Reply:       \"{reply_preview}\"")

        if result.contact_state:
            print(f"  Contact:     {result.contact_state}")

        # Update session slots for next turn
        if result.slots:
            slots.update(result.slots)

    print(f"\n{'─' * 70}")
    print("\n  Key insight: pricing and contact requests were gate-checked")
    print("  against dialogue legality invariants — no premature disclosure,")
    print("  no unauthorized contact harvesting. All in microseconds.")
    print("=" * 70)


if __name__ == "__main__":
    main()
