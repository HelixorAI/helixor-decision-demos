#!/usr/bin/env python3
"""Integration 06 · LangChain Guardrail using the Local Enclave.

Shows how to use the Helixor Decision Runtime as a LangChain-compatible
guardrail. Every LLM call's output is evaluated through the PII Guard
enclave before being returned to the user.

Pattern:
    User prompt → LLM → Helixor PII Guard → Clean response or Block

Works with any LangChain-compatible LLM. Falls back to a simulated
LLM if langchain is not installed.

Tier 0: Works locally with the bundled Community enclave.
"""

from helixor_runtime import HelixorEngine


# Simulated LLM responses (in production, these come from your LLM)
SIMULATED_LLM_RESPONSES = {
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
    """LangChain-compatible output guardrail using Helixor Decision Runtime.

    Drop this into any LangChain chain as an output parser / post-processor.
    """

    def __init__(self, block_on_fatal: bool = True):
        self.engine = HelixorEngine()
        self.block_on_fatal = block_on_fatal

    def __call__(self, llm_output: str) -> dict:
        """Evaluate LLM output through the PII Guard enclave."""
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
    print(" INTEGRATION: LANGCHAIN GUARDRAIL")
    print("=" * 70)

    guardrail = HelixorGuardrail(block_on_fatal=False)  # Redact instead of block

    for prompt, llm_response in SIMULATED_LLM_RESPONSES.items():
        print(f"\n{'─' * 70}")
        print(f"  [Prompt]:   \"{prompt}\"")
        print(f"  [LLM Raw]:  \"{llm_response[:80]}...\"")

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
    print(" USAGE IN LANGCHAIN:")
    print("   guardrail = HelixorGuardrail()")
    print("   chain = llm | guardrail  # pipe LLM output through guardrail")
    print("   result = chain.invoke({'input': 'Summarize the customer record'})")
    print("=" * 70)


if __name__ == "__main__":
    main()
