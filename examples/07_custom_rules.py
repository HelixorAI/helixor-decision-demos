#!/usr/bin/env python3
"""Example 07 · Tier 1: Registered License — Custom Rule Compilation.

This example shows what UNLOCKS when you register for a free developer
license. The bundled Community enclave runs static regulatory invariants.
A registered license lets you compile custom detection rules.

    # Step 1: Register free at https://helixor.ai/register to receive helixor.lic
    # Step 2: Save it as ~/.helixor/helixor.lic (or set HELIXOR_LICENSE_FILE)
    # Step 3: Add your rule to a playbook and compile it into a sealed pack
    helixor-pack compile --playbook my_rules.yaml --out my_rules.hxpack
    # Step 4: Load it: HelixorEngine.load_pack("my_rules.hxpack")

Without a registered license, compile_custom_rule() raises an error
with clear upgrade instructions. This is intentional — it shows you
exactly what the next tier unlocks.
"""

from helixor_runtime import HelixorEngine


def main() -> None:
    print("=" * 70)
    print(" HELIXOR DECISION RUNTIME — CUSTOM RULE COMPILATION ")
    print(" Tier 1: Requires a registered Developer license")
    print("=" * 70)

    engine = HelixorEngine()

    print(f"\n  Current Tier: {engine.tier}")
    print(f"  Licensed to:  {engine.licensed_to}")

    # ── First, show that the bundled PII Guard works fine ──
    print("\n── Built-in regulatory invariants (always available) ──")

    test_text = "Internal project code: PROJ-ZEUS-9X. Contact ops@acme.com."
    result = engine.evaluate(test_text)
    print(f'  Input:    "{test_text}"')
    print(f"  Action:   {result.action}")
    print(f"  Triggers: {[t.rule_id for t in result.triggers]}")
    print(f'  Output:   "{result.remedy.clean_text}"')
    print()
    print("  Note: PROJ-ZEUS-9X passed through — the bundled enclave doesn't know")
    print("  it's an internal project code. Only the built-in PII rules fire.")

    # ── Now try to add a custom rule ──
    print("\n── Attempting custom rule compilation ──")
    print('  Instruction: "Block any text containing PROJ-ZEUS"')

    try:
        engine.compile_custom_rule("Block any text containing 'PROJ-ZEUS'")
        print("  ✓ Custom rule compiled successfully!")

        # Re-evaluate — the custom rule should now fire
        result2 = engine.evaluate(test_text)
        print(f'\n  Re-evaluate: "{test_text}"')
        print(f"  Action:      {result2.action}")
        print(f"  Triggers:    {[t.rule_id for t in result2.triggers]}")
        print(f"  Compliant:   {result2.invariants_passed}")
        print(f'  Output:      "{result2.remedy.clean_text}"')

        print("\n  ✓ The enclave now detects PROJ-ZEUS as a policy violation!")
        print("  This is the power of Tier 1: extend the decision logic at runtime.")

    except Exception as e:
        print(f"\n  ✗ {e}")
        print()
        print("  ─────────────────────────────────────────────────────────")
        print("  This is expected on the bundled Community license.")
        print("  To unlock custom rule compilation:")
        print()
        print("    1. Register free:  https://helixor.ai/register")
        print("    2. Save license:   ~/.helixor/helixor.lic (or set HELIXOR_LICENSE_FILE)")
        print("    3. Compile rules:  helixor-pack compile --playbook my_rules.yaml --out my_rules.hxpack")
        print("    4. Load the pack:  HelixorEngine.load_pack(\"my_rules.hxpack\")")
        print("  ─────────────────────────────────────────────────────────")

    print("\n" + "=" * 70)
    print(" ADOPTION LADDER")
    print("  Tier 0: Clone & Run      → Examples 01-06 (you are here)")
    print("  Tier 1: Registered       → Custom rules, playbook editing")
    print("  Tier 2: Studio (Portal)  → Ontology viewer, data source binding")
    print("  Tier 3: Expert           → Custom domains, codons, and symbols")
    print("=" * 70)


if __name__ == "__main__":
    main()
