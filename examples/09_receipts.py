#!/usr/bin/env python3
"""Example 09 · Tier 0: Receipts — recompute one, then chain your audit log.

Every result carries a receipt_hash. This example recomputes it from what you
log (never the payload, only its SHA-256) with the published recipe,
helixor.decision_receipt.v1, and shows the three properties the guide states:

  - the same input and pack version always give the same receipt;
  - two different inputs blocked by the same rule get different receipts;
  - a receipt is a fingerprint you can recompute, not a signature.

Receipts are not signed, keyed or chained. The last part adds a hash chain
to the log you write, so an edited or deleted line is detectable.

Guide: https://helixor.dev/guide/receipts.html
"""

from __future__ import annotations

import hashlib
import io
import json

from helixor_runtime import HelixorEngine


def decision_receipt(pack_id, pack_version, action, invariants_passed, rule_ids, payload_sha256):
    """Recompute a helixor.decision_receipt.v1 receipt."""
    body = json.dumps({
        "schema": "helixor.decision_receipt.v1",
        "pack_id": pack_id,
        "pack_version": pack_version,
        "action": action,
        "invariants_passed": invariants_passed,
        "rule_ids": rule_ids,
        "sha256_payload": payload_sha256,
    }, sort_keys=True, separators=(",", ":"))
    return "hx_proof_" + hashlib.sha256(body.encode("utf-8")).hexdigest()[:24]


class ChainedAuditLog:
    """Each line carries the hash of the previous one, so edits and deletions show."""

    def __init__(self, sink):
        self.sink, self.prev = sink, "0" * 64

    def append(self, entry: dict) -> str:
        record = dict(entry, prev=self.prev)
        line = json.dumps(record, sort_keys=True)
        self.prev = hashlib.sha256(line.encode()).hexdigest()
        self.sink.write(line + "\n")
        return self.prev


def verify_chain(lines: list[str]) -> int | None:
    """Return the index of the first line whose chain link is broken, or None."""
    prev = "0" * 64
    for i, line in enumerate(lines):
        if json.loads(line)["prev"] != prev:
            return i
        prev = hashlib.sha256(line.encode()).hexdigest()
    return None


def log_entry(engine: HelixorEngine, text: str) -> dict:
    """What you log for each decision: no payload, only its hash."""
    result = engine.evaluate(text)
    return {
        "pack": result.pack_id,
        "pack_version": engine.version,
        "action": result.action,
        "passed": result.invariants_passed,
        "rules": [t.rule_id for t in result.triggers],
        "payload_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "receipt": result.receipt_hash,
    }


def recompute(entry: dict) -> str:
    return decision_receipt(entry["pack"], entry["pack_version"], entry["action"],
                            entry["passed"], entry["rules"], entry["payload_sha256"])


def main() -> int:
    print("=" * 70)
    print(" HELIXOR DECISION RUNTIME — RECEIPTS ")
    print("=" * 70)

    engine = HelixorEngine()
    print(f"\n  Pack: {engine.pack_id} (version {engine.version})")

    # [1] The guide's example: recompute the receipt from the log entry.
    print("\n[1] Recompute a logged receipt")
    entry = log_entry(engine, "Employee note: SSN is 123-45-6789.")
    print(f"  {entry['receipt']} {recompute(entry) == entry['receipt']}")

    # [2] Deterministic, and specific to the input.
    print("\n[2] Same input, same receipt; different input, different receipt")
    again = log_entry(engine, "Employee note: SSN is 123-45-6789.")
    other = log_entry(engine, "Applicant SSN 123-45-6780 on file.")
    print(f"  same input twice:          {again['receipt'] == entry['receipt']}")
    print(f"  other input, same rule:    {other['rules'] == entry['rules']}  ({other['rules'][0]})")
    print(f"  other input, same receipt: {other['receipt'] == entry['receipt']}")

    # [3] A receipt is not a signature: anyone holding the fields can make one.
    print("\n[3] What a receipt does not prove")
    forged = dict(entry, action="permit_clean_payload", passed=True, rules=[])
    print(f"  anyone can compute a receipt for an altered entry: {recompute(forged).startswith('hx_proof_')}")
    print("  so integrity has to come from where you store the log.")

    # [4] Chain the log so an edit or a deletion is detectable.
    print("\n[4] A hash-chained audit log")
    sink = io.StringIO()
    log = ChainedAuditLog(sink)
    for text in ["Move the design review to Thursday.",
                 "Send the deck to dana.reyes@example.com.",
                 "Employee note: SSN is 123-45-6789."]:
        e = log_entry(engine, text)
        log.append(e)
        print(f"  {e['action']:32} {e['receipt']}")
    lines = sink.getvalue().splitlines()
    print(f"  chain intact:                   {verify_chain(lines) is None}")
    tampered = [lines[0], lines[2]]                       # line 2 deleted
    print(f"  after deleting line 2, broken at index: {verify_chain(tampered)}")

    print("\n" + "=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
