#!/usr/bin/env python3
"""Integration 05 · Governed queries (Planned): fails closed by default.

Governed data access (Lattice: sources bound to ontology concepts, access
policy applied before a query resolves, an access receipt per answer) is
Planned. It is not part of the runtime wheel, and no Helixor service offers it
today. So by default this script queries nothing: it prints why and exits with
status 3.

    python integrations/05_governed_query.py              # fails closed (exit 3)
    python integrations/05_governed_query.py --simulate   # local simulation

`--simulate` shows the SHAPE of the planned contract with rows this script
makes up. Every printed line starts with "[SIMULATION]" and every returned
dict carries "simulation": True. Nothing in simulation mode is checked against
a data source, a policy engine or a signing key, so it never reports anything
as verified. The one real computation is the receipt digest: a SHA-256 over
the admitted rows, which `recompute_receipt_digest` recomputes to show that
changing an admitted row changes the digest. It is an unsigned digest, so it
says nothing about who produced the rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys

EXIT_UNAVAILABLE = 3
SIMULATION = "SIMULATION"


class GovernedDataUnavailable(RuntimeError):
    """Governed data access is Planned; there is no service to query."""

    missing_capability = "governed data access (Lattice query, access policy, access receipts)"

    def __init__(self) -> None:
        super().__init__(
            f"UNAVAILABLE: {self.missing_capability} is Planned and not shipped. "
            "Neither the runtime wheel nor any Helixor service offers it, so nothing "
            "was queried and no receipt was produced. Run with --simulate to see the "
            "shape of the planned contract with made-up rows."
        )


def governed_query(realm: str, role_id: str, concept: str, query: str = "") -> dict:
    """The real governed query. It has no service to call, so it fails closed."""
    raise GovernedDataUnavailable()


# ── Local simulation (off by default) ────────────────────────────────────────

# Made-up rows for the simulation. They are not read from any source.
_SIMULATED_ROWS = (
    {"id": "SUPP-001", "legalName": "Example Precision Parts (simulated)", "country": "DE", "dailyCapacityTons": 120},
    {"id": "SUPP-002", "legalName": "Example Metalworks (simulated)", "country": "FR", "dailyCapacityTons": 85},
)
_SIMULATED_TAX_IDS = {"SUPP-001": "SIM-TAX-0001", "SUPP-002": "SIM-TAX-0002"}
# The simulated policy: which roles may see the restricted field.
_ROLES_WITH_TAX_ACCESS = frozenset({"ComplianceAuditor_Global"})


def _receipt_digest(realm: str, concept: str, role_id: str, rows: list[dict]) -> str:
    canonical = json.dumps({"realm": realm, "concept": concept, "roleId": role_id, "rows": rows}, sort_keys=True)
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


def simulate_governed_query(realm: str, role_id: str, concept: str) -> dict:
    """Simulated rows, a simulated field policy and a digest of what was admitted."""
    may_see_tax = role_id in _ROLES_WITH_TAX_ACCESS
    rows = []
    for row in _SIMULATED_ROWS:
        admitted = dict(row)
        if may_see_tax:
            admitted["taxIdentifier"] = _SIMULATED_TAX_IDS[row["id"]]
        rows.append(admitted)
    withheld = [] if may_see_tax else [{"field": "taxIdentifier", "reason": "simulated policy: role lacks audit access"}]
    return {
        "simulation": True,
        "realm": realm,
        "concept": concept,
        "roleId": role_id,
        "rows": rows,
        "withheldFields": withheld,
        "receiptDigest": _receipt_digest(realm, concept, role_id, rows),
    }


def recompute_receipt_digest(result: dict) -> dict:
    """Recompute the digest from the rows in `result` and compare.

    This is a real recomputation over the simulated rows, not a verification of
    anything: the digest is unsigned and the rows are made up.
    """
    recomputed = _receipt_digest(result["realm"], result["concept"], result["roleId"], result["rows"])
    return {"simulation": True, "digestMatches": recomputed == result["receiptDigest"], "recomputed": recomputed}


def _say(line: str = "") -> None:
    print(f"[{SIMULATION}] {line}".rstrip())


def run_simulation() -> None:
    realm = "example-realm"
    _say("Governed query contract, LOCAL SIMULATION: made-up rows, no data source, no signing key.")

    for role in ("SupplierAnalyst_EMEA", "ComplianceAuditor_Global"):
        result = simulate_governed_query(realm=realm, role_id=role, concept="Supplier")
        _say()
        _say(f"Query as {role}: {len(result['rows'])} simulated rows")
        for row in result["rows"]:
            tax = row.get("taxIdentifier", "(withheld)")
            _say(f"  {row['id']}: {row['legalName']} ({row['country']}, {row['dailyCapacityTons']}t/day), tax id {tax}")
        for withheld in result["withheldFields"]:
            _say(f"  withheld {withheld['field']}: {withheld['reason']}")
        _say(f"  receipt digest (unsigned): {result['receiptDigest'][:23]}...")

        check = recompute_receipt_digest(result)
        _say(f"  digest recomputed from the rows above: {'matches' if check['digestMatches'] else 'DIFFERS'}")

        tampered = dict(result, rows=[dict(result["rows"][0], dailyCapacityTons=999)] + result["rows"][1:])
        after = recompute_receipt_digest(tampered)
        _say(f"  after changing one row: {'matches' if after['digestMatches'] else 'differs'}")

    _say()
    _say("Nothing above came from a governed data plane; governed data access is Planned.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--simulate", action="store_true", help="run the labelled local simulation")
    args = parser.parse_args(argv)

    if args.simulate:
        run_simulation()
        return
    try:
        governed_query(realm="example-realm", role_id="SupplierAnalyst_EMEA", concept="Supplier")
    except GovernedDataUnavailable as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(EXIT_UNAVAILABLE) from None


if __name__ == "__main__":
    main()
