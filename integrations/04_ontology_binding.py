#!/usr/bin/env python3
"""Integration 04 · Ontology with source bindings (source binding is Planned).

Submits an ontology whose concepts declare the data sources they would bind
to (a relational ERP database, a cloud data warehouse, a REST feed, a Kafka
topic) and the field and row policies that would apply per role, then reads
the admitted configuration back.

What runs today: the server admits and returns the ontology configuration.
What is Planned: binding those sources, applying the policies at query time
and returning access receipts (Lattice, the governed data plane). This script
does not query any source; see 05_governed_query.py, which fails closed.

Requirements:
    pip install httpx
    export HELIXOR_API_URL=<your Helixor server URL>
    export HELIXOR_API_KEY=<your API key>

If the server is unreachable or rejects the ontology, the script says so and
exits with status 1; it has no offline mode.
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
    print(" INTEGRATION: ONTOLOGY WITH SOURCE BINDINGS (BINDING IS PLANNED)")
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
      - id: SRC-REST-SUPPLIER-FEED
        type: rest
        url: ${HELIXOR_SUPPLIER_FEED_URL}
        path: "$.suppliers"

  Customer:
    attributes:
      name: { type: string }
      email: { type: string, pii: true }
      segment: { type: string, enum: [enterprise, mid_market, smb] }
      ltv: { type: float, description: "Lifetime value USD" }
    sources:
      - id: SRC-WAREHOUSE-CDW
        type: postgresql
        connection: ${HELIXOR_WAREHOUSE_DSN}
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
            print(f"  ✗ Ontology not admitted: HTTP {r.status_code} — {r.text[:200]}")
            sys.exit(1)
    except httpx.ConnectError:
        print(f"  ✗ Cannot reach {API_URL}; nothing was submitted.")
        sys.exit(1)

    # ── Step 2: Read back the admitted ontology configuration ──
    print("\n[2] Reading back the admitted ontology configuration...")
    r = httpx.get(f"{API_URL}/api/v1/reasoning/ontology/config", headers=headers(), timeout=10.0)
    r.raise_for_status()
    print(f"  Config keys: {sorted(r.json())}")

    # ── Step 3: Governed queries (Planned) ──
    # The server admits the ontology above, but it does not bind the declared
    # sources or answer governed queries: that is Lattice, which is Planned.
    print("\n[3] Source binding and governed queries are Planned; nothing was queried.")
    print("    integrations/05_governed_query.py fails closed for the same reason.")


if __name__ == "__main__":
    main()
