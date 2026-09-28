#!/usr/bin/env python3
"""Example 01 · Tier 0: Clone & Run — Quickstart.

No API key. Zero configuration. Needs the licensed helixor-runtime installed.

    git clone https://github.com/HelixorAI/helixor-decision-demos
    cd helixor-decision-demos
    pip install helixor-runtime
    python examples/01_quickstart.py

The bundled Community enclave ships with the PII Guard regulatory
invariants (GLBA, PCI-DSS, HIPAA, GDPR, TCPA) ready to evaluate.
"""

from helixor_runtime import HelixorEngine


def main() -> None:
    print("=" * 70)
    print(" HELIXOR DECISION RUNTIME — QUICKSTART ")
    print(" Bundled Community Enclave · No API Key · Zero Config")
    print("=" * 70)

    # One line. No pack file, no license file, no API key.
    engine = HelixorEngine()

    print(f"\n  Enclave:      {engine.pack_id} (v{engine.version})")
    print(f"  Licensed to:  {engine.licensed_to}")
    print(f"  Tier:         {engine.tier}")

    # ── PII Guard Tutorial: Evaluate 4 payload types ──

    samples = [
        # Clean — no PII
        "Please schedule the product demo with team lead on Thursday at 2pm.",
        # SSN — GLBA fatal block
        "Employee onboarding: SSN is 123-45-6789, department operations.",
        # Credit Card — PCI-DSS fatal block + email redaction
        "Customer renewal card: 4111-1111-1111-1111, contact billing@acme.corp.",
        # Health ID — HIPAA fatal block
        "Patient medical chart: RX-8839201 diagnosed with acute hypertension.",
    ]

    for sample in samples:
        print(f'\n[Input]: "{sample}"')
        result = engine.evaluate(sample)

        print(f"  Action:         {result.action}")
        print(f"  Compliant:      {result.invariants_passed}")
        print(f"  Latency:        {result.latency_us:.1f} µs")
        print(f"  Tokens Spent:   {result.tokens_spent}")
        print(f"  Network Egress: {result.egress_bytes} bytes")
        print(f"  Audit Receipt:  {result.receipt_hash}")

        if not result.invariants_passed:
            print(f'  Clean Output:   "{result.remedy.clean_text}"')

    print("\n" + "=" * 70)
    print(" WHAT'S NEXT?")
    print("  → Run examples 02-06 to see benchmarks, streaming, and HTTP service")
    print("  → Run example 07 to see what unlocks with a registered license")
    print("  → Sign up free: https://helixor.ai/register")
    print("=" * 70)


if __name__ == "__main__":
    main()
