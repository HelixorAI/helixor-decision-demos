#!/usr/bin/env python3
"""Integration 07 · Batch CSV Pipeline through the Decision Enclave.

Real-world pattern: process a CSV file of customer records through
the PII Guard enclave, writing a clean version with all PII redacted
and a compliance report with audit receipts.

Works with the local enclave (Tier 0) — no server required.
"""

import csv
import io
import time

from helixor_runtime import HelixorEngine


# Simulated input CSV (in production, read from file/S3/GCS)
INPUT_CSV = """customer_id,name,email,phone,notes
CUST-001,Alice Johnson,alice@acme.com,(415) 555-0101,Enterprise renewal Q4
CUST-002,Bob Smith,bob.smith@globex.io,(212) 555-0199,SSN on file: 123-45-6789
CUST-003,Carol Davis,carol@startup.co,(650) 555-0142,Card ending 4111-1111-1111-1111
CUST-004,Dave Wilson,dave@example.com,(312) 555-0177,Standard account
CUST-005,Eve Torres,eve.torres@health.org,(617) 555-0133,Patient MRN-1234567 referral
"""


def main() -> None:
    print("=" * 70)
    print(" INTEGRATION: BATCH CSV PIPELINE")
    print("=" * 70)

    engine = HelixorEngine()

    reader = csv.DictReader(io.StringIO(INPUT_CSV.strip()))
    clean_rows = []
    report_rows = []

    t0 = time.perf_counter()
    for row in reader:
        # Evaluate each field that might contain PII
        for field in ["name", "email", "phone", "notes"]:
            value = row.get(field, "")
            if not value:
                continue

            result = engine.evaluate(value)

            if not result.invariants_passed:
                # Replace with redacted version
                row[field] = result.remedy.clean_text if result.remedy else value
                report_rows.append({
                    "customer_id": row["customer_id"],
                    "field": field,
                    "action": result.action,
                    "triggers": [t.rule_id for t in result.triggers],
                    "receipt": result.receipt_hash,
                })

        clean_rows.append(row)

    elapsed_ms = (time.perf_counter() - t0) * 1000

    # ── Clean CSV output ──
    print("\n── Clean CSV (PII redacted) ──")
    if clean_rows:
        fieldnames = list(clean_rows[0].keys())
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(clean_rows)
        print(output.getvalue())

    # ── Compliance report ──
    print("── Compliance Report ──")
    print(f"  Records processed: {len(clean_rows)}")
    print(f"  PII violations:    {len(report_rows)}")
    print(f"  Processing time:   {elapsed_ms:.1f} ms")
    print()
    for r in report_rows:
        print(f"  {r['customer_id']}.{r['field']}: {r['action']}")
        if r["triggers"]:
            print(f"    Rules: {r['triggers']}")
        print(f"    Receipt: {r['receipt'][:24]}...")

    print("\n" + "=" * 70)
    print(" In production: read from S3/GCS, write clean CSV + report back,")
    print(" attach receipts to audit trail. Zero tokens, zero network egress.")
    print("=" * 70)


if __name__ == "__main__":
    main()
