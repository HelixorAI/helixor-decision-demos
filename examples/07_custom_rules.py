#!/usr/bin/env python3
"""Example 07 · Tier 0: Where custom rules go.

Step 1 of the "Add custom rules" tutorial, which runs on the Community tier:

  - the built-in example pack does not know your internal identifiers, so
    PROJ-ZEUS-9X passes through it;
  - compile_custom_rule() was removed from HelixorEngine in 0.3.0. Calling it
    raises RemovedCapabilityError, whose message says what to do instead:
    declare the rule in a playbook and compile it with your Developer license.

The playbook for that is playbooks/internal_ids.yaml; example 11 compiles and
runs it when a Developer license is in place.

Tutorial: https://helixor.dev/tutorials/custom-rules.html
"""

from __future__ import annotations

from helixor_runtime import HelixorEngine, RemovedCapabilityError


def main() -> int:
    print("=" * 70)
    print(" HELIXOR DECISION RUNTIME — WHERE CUSTOM RULES GO ")
    print("=" * 70)

    engine = HelixorEngine()

    # The built-in pack only knows the regulated data it was written for.
    text = "Status for PROJ-ZEUS-9X is green. Contact ops@example.com."
    result = engine.evaluate(text)
    print("\n[1] The built-in example pack on an internal project code")
    print(f'  Input:    "{text}"')
    print(f"  Action:   {result.action}")
    print(f"  Rules:    {[t.rule_id for t in result.triggers]}")
    print(f'  Output:   "{result.remedy.clean_text}"')
    print("  PROJ-ZEUS-9X passes through: the built-in pack does not know it.")

    # The tutorial's step 1, as written.
    print("\n[2] compile_custom_rule() is gone (Changed in 0.3.0)")
    print("tier:", engine.tier)
    print("has compile_custom_rule:", hasattr(engine, "compile_custom_rule"))
    try:
        engine.compile_custom_rule("Block any text containing 'PROJ-ZEUS'")
    except RemovedCapabilityError as exc:
        print(f"{type(exc).__name__}: {exc}")
    else:
        # Fail closed: if a runtime brings the method back, this example is wrong.
        print("UNEXPECTED: compile_custom_rule() returned; update this example.")
        return 1

    print("\n[3] What to do instead, with your Developer license")
    print("  playbooks/internal_ids.yaml declares two regex rules. Compile and run it:")
    print("    helixor-pack compile --playbook playbooks/internal_ids.yaml \\")
    print("      --license ~/.helixor/helixor.lic --out internal_ids.hxpack")
    print("    python examples/11_compiled_pack.py")
    print("\n" + "=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
