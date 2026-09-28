#!/usr/bin/env python3
"""Integration 05 · Governed Queries with Lattice Access Receipts.

Demonstrates the Lattice MCP gateway pattern: an external agent
(an agent framework or coding assistant) queries governed data through the
Lattice surface. Every answer carries a cryptographic access receipt.

This example simulates the Lattice MCP tools locally to show the
contract. When connected to a live server, these same calls go
through the real governed data plane.

Tier 3: Full Lattice integration.
"""

import hashlib
import json
import time


def lattice_query(
    realm: str,
    role_id: str,
    concept: str,
    query: str = "",
) -> dict:
    """Simulate the lattice_query MCP tool.

    In production, this resolves through the Lattice governed data plane:
    1. Parse the query intent against the ontology
    2. Apply row-level and field-level policies for the caller's role
    3. Resolve data from bound sources (without rows leaving stores)
    4. Generate a cryptographic access receipt
    5. Return admitted rows + receipt
    """
    is_auditor = "auditor" in role_id.lower()
    is_emea = "emea" in role_id.lower()

    # Policy-filtered data (simulated)
    rows = [
        {"id": "SUPP-001", "legalName": "Berlin Precision Machining GmbH", "country": "DE", "dailyCapacityTons": 120},
        {"id": "SUPP-002", "legalName": "Rhone-Alpes Metalworks SAS", "country": "FR", "dailyCapacityTons": 85},
    ]

    withheld_fields = []
    if not is_auditor:
        withheld_fields.append({
            "field": "taxIdentifier",
            "ruleId": "RULE-SHIELD-RESTRICTED-TAXID-01",
            "reason": "PII redacted — caller lacks audit clearance",
        })
    else:
        for r in rows:
            r["taxIdentifier"] = "DE-994829104" if r["country"] == "DE" else "FR-44829103928"

    # Cryptographic access receipt
    canonical = json.dumps({"realm": realm, "concept": concept, "roleId": role_id, "rows": rows}, sort_keys=True)
    digest = "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()

    return {
        "queryId": f"QRY-{int(time.time()) % 1000000}",
        "realm": realm,
        "concept": concept,
        "outcome": "ANSWERED",
        "rowsCount": len(rows),
        "rows": rows,
        "withheldFields": withheld_fields,
        "receipt": {
            "receiptId": f"RCPT-{int(time.time()) % 1000000}",
            "packageDigest": digest,
            "ontologyTboxHash": "sha256:7f3b89e9d1a2c4e09f5643a7891234bc567890def1234567890abcdef1234567",
            "policySetRevision": "pol-rev-2026.09-r4",
            "replayable": True,
        },
    }


def lattice_simulate(role_id: str, concept: str) -> dict:
    """Simulate the lattice_simulate MCP tool.

    Preview what a given agent persona can access without running
    the actual query. Used by Studio to show access boundaries.
    """
    is_auditor = "auditor" in role_id.lower()
    return {
        "roleId": role_id,
        "concept": concept,
        "accessLevel": "FULL" if is_auditor else "PARTIAL",
        "withheldFields": [] if is_auditor else ["taxIdentifier", "internalCreditRating"],
        "sourcesInScope": ["SRC-POSTGRES-ERP", "SRC-SHEET-SUPPLIER-FEED"],
        "governedRulesApplied": (
            ["RULE-SHIELD-AUDITOR-FULL-DISCLOSURE"]
            if is_auditor
            else ["RULE-SHIELD-RESTRICTED-TAXID-01", "RULE-SHIELD-REGIONAL-ISOLATION"]
        ),
    }


def lattice_receipt_verify(receipt_id: str, package_digest: str) -> dict:
    """Simulate the lattice_receipt_verify MCP tool.

    Cryptographically verify that an access receipt is valid and
    the admitted data hasn't been tampered with since query time.
    """
    if not package_digest.startswith("sha256:"):
        return {"verified": False, "error": "Invalid digest format"}

    return {
        "verified": True,
        "receiptId": receipt_id,
        "integrityStatus": "VALID_BITWISE_MATCH",
        "verifiedAtUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def main() -> None:
    print("=" * 70)
    print(" INTEGRATION: GOVERNED QUERIES WITH LATTICE ACCESS RECEIPTS")
    print("=" * 70)

    realm = "helixor-di-P1"

    # ── Query as Analyst (restricted) ──
    print("\n[1] Query as SupplierAnalyst_EMEA...")
    result = lattice_query(
        realm=realm,
        role_id="SupplierAnalyst_EMEA",
        concept="Supplier",
        query="EMEA suppliers with capacity > 80 tons/day",
    )
    print(f"  Outcome:  {result['outcome']}")
    print(f"  Rows:     {result['rowsCount']}")
    for row in result["rows"]:
        print(f"    {row['id']}: {row['legalName']} ({row['country']}, {row['dailyCapacityTons']}t/day)")
    if result["withheldFields"]:
        for w in result["withheldFields"]:
            print(f"  ✗ Withheld: {w['field']} — {w['reason']}")
    receipt = result["receipt"]
    print(f"  Receipt:  {receipt['receiptId']}")
    print(f"  Digest:   {receipt['packageDigest'][:50]}...")

    # ── Same query as Auditor (sees everything) ──
    print(f"\n[2] Same query as ComplianceAuditor_Global...")
    result2 = lattice_query(
        realm=realm,
        role_id="ComplianceAuditor_Global",
        concept="Supplier",
    )
    print(f"  Outcome:  {result2['outcome']}")
    for row in result2["rows"]:
        tax = row.get("taxIdentifier", "—")
        print(f"    {row['id']}: {row['legalName']} — Tax ID: {tax}")
    print(f"  Withheld: {len(result2['withheldFields'])} fields (auditor sees all)")

    # ── Simulate access for a persona ──
    print(f"\n[3] Access simulation for SupplierAnalyst_EMEA...")
    sim = lattice_simulate("SupplierAnalyst_EMEA", "Supplier")
    print(f"  Access:   {sim['accessLevel']}")
    print(f"  Withheld: {sim['withheldFields']}")
    print(f"  Rules:    {sim['governedRulesApplied']}")

    # ── Verify receipt ──
    print(f"\n[4] Verify access receipt from query 1...")
    verify = lattice_receipt_verify(receipt["receiptId"], receipt["packageDigest"])
    print(f"  Verified: {verify['verified']}")
    print(f"  Status:   {verify['integrityStatus']}")

    print("\n" + "=" * 70)
    print(" LATTICE PRINCIPLES DEMONSTRATED:")
    print("   1. Same query, different roles → different data admitted")
    print("   2. Policy applied ONCE at query lowering (before resolution)")
    print("   3. Rows never left their source stores")
    print("   4. Receipt is pinned — rendering never re-resolves")
    print("   5. These MCP tools are what external agents and assistants call")
    print("=" * 70)


if __name__ == "__main__":
    main()
