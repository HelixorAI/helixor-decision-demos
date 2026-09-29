#!/usr/bin/env python3
"""Integration 06 · Output guardrail using the local runtime.

Passes a language model's output through the PII Guard runtime before it
reaches the user: clean text passes, PII is redacted, or (with
block_on_fatal) the output is blocked.

`HelixorGuardrail` is a plain callable that takes a string and returns a dict.
It does not import or depend on any agent framework; to use it in one, call it
from that framework's output post-processing step.

The model outputs below are canned sample text (SAMPLE_MODEL_OUTPUTS), so no
model is called. The guardrail decisions on them are real runtime results.
"""

from helixor_runtime import HelixorEngine


# Canned sample model outputs; no model is called. In use, these come from your model.
SAMPLE_MODEL_OUTPUTS = {
    "Summarize the customer record": (
        "Customer John Doe (SSN: 234-56-7890) has an outstanding balance "
        "of $4,200 on card 4532-1234-5678-9012. Contact: john.doe@acme.com, "
        "phone (415) 555-0198."
    ),
    "Draft a follow-up email": (
        "Hi Team,\n\nPlease follow up with the client regarding their "
        "Q4 renewal. The account is in good standing with no outstanding "
        "compliance issues.\n\nBest regards"
    ),
    "Generate a patient intake summary": (
        "Patient intake: MRN-4529381, diagnosed with Type 2 diabetes. "
        "Primary care physician noted elevated A1C levels. Insurance on "
        "file with SSN 567-89-0123 for billing verification."
    ),
}


class HelixorGuardrail:
    """Output guardrail over the Helixor decision runtime: str in, decision dict out."""

    def __init__(self, block_on_fatal: bool = True):
        self.engine = HelixorEngine()
        self.block_on_fatal = block_on_fatal

    def __call__(self, llm_output: str) -> dict:
        """Evaluate LLM output through the PII Guard pack."""
        result = self.engine.evaluate(llm_output)

        if result.invariants_passed:
            return {
                "status": "CLEAN",
                "output": llm_output,
                "receipt": result.receipt_hash,
            }

        # PII detected — redact or block
        clean = result.remedy.clean_text if result.remedy else llm_output
        action = result.action
        triggers = [t.rule_id for t in result.triggers]
        severity = max(
            (t.severity for t in result.triggers),
            key=lambda s: {"INFO": 0, "WARNING": 1, "FATAL": 2}.get(s, 0),
            default="WARNING",
        )

        if self.block_on_fatal and severity == "FATAL":
            return {
                "status": "BLOCKED",
                "output": None,
                "reason": result.reason,
                "action": action,
                "triggers": triggers,
                "receipt": result.receipt_hash,
            }
        else:
            return {
                "status": "REDACTED",
                "output": clean,
                "original_length": len(llm_output),
                "redacted_categories": result.remedy.redacted_categories if result.remedy else [],
                "triggers": triggers,
                "receipt": result.receipt_hash,
            }


def main() -> None:
    print("=" * 70)
    print(" INTEGRATION: OUTPUT GUARDRAIL (sample model outputs, real runtime decisions)")
    print("=" * 70)

    guardrail = HelixorGuardrail(block_on_fatal=False)  # Redact instead of block

    for prompt, llm_response in SAMPLE_MODEL_OUTPUTS.items():
        print(f"\n{'─' * 70}")
        print(f"  [Prompt]:   \"{prompt}\"")
        print(f"  [Sample model output]: \"{llm_response[:80]}...\"")

        result = guardrail(llm_response)

        print(f"  [Status]:   {result['status']}")
        if result["status"] == "CLEAN":
            print(f"  [Output]:   (passed through unchanged)")
        elif result["status"] == "REDACTED":
            print(f"  [Output]:   \"{result['output'][:80]}...\"")
            print(f"  [Redacted]: {result.get('redacted_categories', [])}")
            print(f"  [Rules]:    {result.get('triggers', [])}")
        elif result["status"] == "BLOCKED":
            print(f"  [Blocked]:  {result.get('reason', '?')}")

        print(f"  [Receipt]:  {result['receipt'][:24]}...")

    print(f"\n{'─' * 70}")
    print("\n" + "=" * 70)
    print(" USAGE: call the guardrail on each model output before returning it:")
    print("   guardrail = HelixorGuardrail()")
    print("   decision = guardrail(model_output)")
    print("=" * 70)


if __name__ == "__main__":
    main()
