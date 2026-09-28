#!/usr/bin/env python3
"""Example 04 · Tier 0: Clone & Run — Streaming Token Interceptor.

The enclave's streaming API solves the Token Chunk Boundary Problem:
sensitive entities split across LLM token fragments ("123" + "-45" + "-6789")
are detected and handled in-flight without stalling the stream.

This is the feature that makes Helixor unique for real-time LLM guardrails.
"""

import asyncio
import sys
import time

from helixor_runtime import HelixorEngine


def simulate_llm_stream_with_contact_pii():
    """Simulates token stream with contact PII split across boundaries."""
    tokens = [
        "Thank you for contacting customer support. ",
        "You can reach your account representative at ",
        "sarah", ".connor", "@cyberdyne-defense", ".com",
        " or directly dial our hotline at (415) 555-", "0199",
        " during normal business hours. ",
        "Have a great day!",
    ]
    for token in tokens:
        time.sleep(0.02)
        yield token


def simulate_llm_stream_with_fatal_ssn():
    """Simulates token stream with SSN split across boundaries."""
    tokens = [
        "Patient Intake Summary: ",
        "Patient John Doe presented with elevated blood pressure. ",
        "Identified SSN is ", "123", "-45", "-6789",
        ". Patient assigned to room 402.",
    ]
    for token in tokens:
        time.sleep(0.02)
        yield token


async def simulate_async_llm_stream():
    """Simulates an async token stream with IP and email PII."""
    tokens = [
        "System diagnostics: Primary gateway host ",
        "192.168.1.105 ",
        "is online. Contact security officer at admin@internal-net.org ",
        "for credential refresh.",
    ]
    for token in tokens:
        await asyncio.sleep(0.02)
        yield token


def demo_contact_redaction(engine: HelixorEngine):
    print("\n" + "=" * 75)
    print(" DEMO 1: In-Flight Contact Redaction via Streaming Enclave")
    print("=" * 75)

    session = engine.create_streaming_session(lookahead_chars=28)

    print("\n[Streaming Output]:")
    print("-" * 50)
    for raw_chunk in simulate_llm_stream_with_contact_pii():
        print(f"  [RAW TOKEN]: {raw_chunk!r}")
        for chunk in session.push(raw_chunk):
            badge = " [REDACTED]" if chunk.redacted else ""
            print(f"    --> [EMIT #{chunk.chunk_index}]: {chunk.text!r}{badge}")

    for chunk in session.flush():
        badge = " [REDACTED]" if chunk.redacted else ""
        print(f"    --> [FLUSH #{chunk.chunk_index}]: {chunk.text!r}{badge}")
    print("-" * 50)


def demo_fatal_halting(engine: HelixorEngine):
    print("\n" + "=" * 75)
    print(" DEMO 2: Fatal Statutory Halting (SSN Exfiltration Prevention)")
    print("=" * 75)

    session = engine.create_streaming_session(lookahead_chars=28, block_on_fatal=True)

    print("\n[Streaming Output]:")
    print("-" * 50)
    for raw_chunk in simulate_llm_stream_with_fatal_ssn():
        print(f"  [RAW TOKEN]: {raw_chunk!r}")
        for chunk in session.push(raw_chunk):
            if chunk.blocked:
                print(f"\n  [!!! STREAM HALTED BY ENCLAVE !!!]")
                print(f"  Action:   {chunk.action}")
                print(f"  Reason:   {chunk.reason}")
                print(f"  Rules:    {[t.rule_id for t in chunk.triggers]}")
                break
            else:
                print(f"    --> [EMIT #{chunk.chunk_index}]: {chunk.text!r}")
        if session.is_blocked:
            break
    print("-" * 50)


def demo_sync_generator(engine: HelixorEngine):
    print("\n" + "=" * 75)
    print(" DEMO 3: Drop-In Stream Generator (engine.stream_filter)")
    print("=" * 75)

    sanitized = engine.stream_filter(simulate_llm_stream_with_contact_pii())
    print("Consuming sanitized stream:")
    for token in sanitized:
        sys.stdout.write(token)
        sys.stdout.flush()
    print("\n")


async def demo_async_generator(engine: HelixorEngine):
    print("\n" + "=" * 75)
    print(" DEMO 4: Async Stream Generator (engine.astream_filter)")
    print("=" * 75)

    sanitized = engine.astream_filter(simulate_async_llm_stream())
    print("Consuming sanitized async stream:")
    async for token in sanitized:
        sys.stdout.write(token)
        sys.stdout.flush()
    print("\n")


def main():
    print("=" * 75)
    print(" HELIXOR DECISION RUNTIME — STREAMING TOKEN INTERCEPTOR ")
    print("=" * 75)

    engine = HelixorEngine()

    demo_contact_redaction(engine)
    demo_fatal_halting(engine)
    demo_sync_generator(engine)
    asyncio.run(demo_async_generator(engine))

    print("=" * 75)
    print(" All streaming demonstrations completed successfully.")
    print("=" * 75)


if __name__ == "__main__":
    main()
