#!/usr/bin/env python3
"""Integration 04 · Ontology-Bound Data Sources via Lattice.

This is the advanced integration pattern. Instead of passing raw data
to the decision runtime, you bind data sources to ontology concepts.
The Lattice governed data plane handles:

    1. Source binding (PostgreSQL, Snowflake, APIs → ontology concepts)
    2. Policy application (row/field-level filtering by role)
    3. Governed query resolution (rows never leave their stores)
    4. Cryptographic access receipts (SHA-256 digest, replayable)

The decision runtime then evaluates against the governed data — it never
sees the raw source, only the policy-filtered view.

Requirements:
    export HELIXOR_API_URL=http://127.0.0.1:8030
    export HELIXOR_API_KEY=hlx_...

Tier 3: Requires Helixor account + Lattice pack.
"""

import json
import os
import sys

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)


API_URL = os.environ.get("HELIXOR_API_URL", "http://127.0.0.1:8030")
API_KEY = os.environ.get("HELIXOR_API_KEY", "")


def headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if API_KEY:
        h["X-Helixor-API-Key"] = API_KEY
    return h


def ontology_config_request(yaml_text: str) -> dict:
    """Body for PUT /api/v1/reasoning/ontology/config."""
    return {"yaml": yaml_text}


def main() -> None:
    print("=" * 70)
    print(" INTEGRATION: ONTOLOGY-BOUND DATA SOURCES VIA LATTICE")
    print("=" * 70)

    # ── Step 1: Define ontology concepts ──
    print("\n[1] Defining ontology with source bindings...")
    ontology_config = ontology_config_request("""
schema_version: helixor.ontology.v1

concepts:
  Supplier:
    attributes:
      legalName: { type: string, description: "Legal entity name" }
      country: { type: string, description: "ISO 3166-1 country code" }
      dailyCapacityTons: { type: float, description: "Daily manufacturing capacity" }
      taxIdentifier: { type: string, pii: true, description: "Tax registration number" }
    sources:
      - id: SRC-POSTGRES-ERP
        type: postgresql
        connection: ${HELIXOR_ERP_DSN}
        table: suppliers
        mapping:
          legalName: legal_name
          country: country_code
          dailyCapacityTons: daily_capacity_tons
          taxIdentifier: tax_id
      - id: SRC-SHEET-SUPPLIER-FEED
        type: google_sheets
        spreadsheet_id: ${HELIXOR_SUPPLIER_SHEET_ID}
        range: "Suppliers!A:F"

  Customer:
    attributes:
      name: { type: string }
      email: { type: string, pii: true }
      segment: { type: string, enum: [enterprise, mid_market, smb] }
      ltv: { type: float, description: "Lifetime value USD" }
    sources:
      - id: SRC-SNOWFLAKE-CDW
        type: snowflake
        connection: ${HELIXOR_SNOWFLAKE_DSN}
        table: dim_customers

  Transaction:
    attributes:
      amount: { type: float }
      currency: { type: string }
      timestamp: { type: datetime }
      status: { type: string, enum: [pending, settled, reversed] }
    sources:
      - id: SRC-KAFKA-TXN-STREAM
        type: kafka
        topic: transactions.settled
        schema_registry: ${HELIXOR_SR_URL}

policies:
  - id: RULE-SHIELD-RESTRICTED-TAXID-01
    concept: Supplier
    field: taxIdentifier
    action: redact
    unless_role: [auditor, compliance_officer]
    reason: "PII field restricted to audit and compliance roles"

  - id: RULE-SHIELD-REGIONAL-ISOLATION
    concept: Supplier
    row_filter: "country IN (caller.authorized_regions)"
    reason: "Regional data isolation per GDPR Art. 44"

  - id: RULE-SHIELD-PII-EMAIL-REDACT
    concept: Customer
    field: email
    action: redact
    unless_role: [support, admin]
    reason: "Email PII redacted for non-support roles"
""")

    try:
        r = httpx.put(
            f"{API_URL}/api/v1/reasoning/ontology/config",
            headers=headers(),
            json=ontology_config,
            timeout=10.0,
        )
        if r.status_code == 200:
            result = r.json()
            print(f"  Ontology admitted: {sorted(result)}")
        else:
            print(f"  Status: {r.status_code} — {r.text[:200]}")
            _show_local_demo()
            return
    except httpx.ConnectError:
        print(f"  ✗ Cannot reach {API_URL}")
        _show_local_demo()
        return

    # ── Step 2: Read back the admitted ontology configuration ──
    print("\n[2] Reading back the admitted ontology configuration...")
    r = httpx.get(f"{API_URL}/api/v1/reasoning/ontology/config", headers=headers(), timeout=10.0)
    r.raise_for_status()
    print(f"  Config keys: {sorted(r.json())}")

    # ── Step 3: Governed queries ──
    # The reasoning backend has no governed-query endpoint; /api/v1/decide
    # answers typed questions over evidence and does not resolve ontology
    # queries. Governed queries go through the Lattice MCP tools
    # (lattice_query / lattice_receipt_verify) — see 05_governed_query.py.
    print("\n[3] Governed queries run through the Lattice MCP tools:")
    print("    python integrations/05_governed_query.py")

    print("\n" + "=" * 70)
    print(" The ontology binds concepts to sources in place; Lattice applies")
    print(" policy at query lowering and returns access receipts (see 05).")
    print("=" * 70)


def _show_local_demo():
    """Show what Lattice does without a live server."""
    print("\n" + "-" * 70)
    print(" LATTICE DEMO (offline — showing the concept)")
    print("-" * 70)

    print("""
  The Lattice governed data plane works like this:

  1. BIND: Data sources connect to ontology concepts
     PostgreSQL → Supplier concept
     Snowflake  → Customer concept
     Kafka      → Transaction concept

  2. POLICY: Rules apply at query lowering (before resolution)
     SupplierAnalyst_EMEA:
       ✓ Can see: legalName, country, dailyCapacityTons
       ✗ Cannot see: taxIdentifier (RULE-SHIELD-RESTRICTED-TAXID-01)
       ✗ Cannot see: non-EMEA rows (RULE-SHIELD-REGIONAL-ISOLATION)

     ComplianceAuditor_Global:
       ✓ Can see: ALL fields including taxIdentifier
       ✓ Can see: ALL regions (no isolation)

  3. RECEIPT: Every answer carries a cryptographic access receipt
     receiptId:       RCPT-928374
     packageDigest:   sha256:7f3b89e9d1a2c4e0...
     ontologyTboxHash: sha256:9f86d081884c7d65...
     policyRevision:  pol-rev-2026.09-r4
     replayable:      true

  4. AGENT GATEWAY: External agents query via MCP
     lattice_query    → governed data retrieval
     lattice_simulate → preview access for a persona
     lattice_receipt_verify → audit receipt integrity

  To run this live:
    1. Start the Helixor backend: helixor serve
    2. Set HELIXOR_API_URL and HELIXOR_API_KEY
    3. Re-run this example
""")


if __name__ == "__main__":
    main()
