# Phase 3: Integration Examples

Real-world integration patterns showing the Helixor Decision Runtime
connected to the hosted server, external data sources, and ontology
bindings via Helixor Lattice.

## Architecture

```
                                    ┌──────────────────────────┐
                                    │   Helixor Reasoning      │
                                    │   Backend (hosted)       │
                                    │                          │
┌───────────┐   REST/SSE/WS        │  /api/v1/decide          │
│ Your App  │──────────────────────▶│  /api/v1/reasoning/chat  │
│           │                       │  /api/v1/reasoning/solve │
│           │   Generated SDK       │                          │
│           │   (helixor-sdk-gen)   │  Ontology + Extensions   │
└───────────┘                       │  Playbook Compiler       │
      │                             │  Decision Ledger         │
      │                             └────────────┬─────────────┘
      │                                          │
      │                                          │ Lattice
      │                                          │ (governed data plane)
      │                                          │
      ▼                                          ▼
┌───────────┐                       ┌──────────────────────────┐
│ Local     │                       │   Data Sources           │
│ Runtime   │                       │   (bound via ontology)   │
│ (Python)  │                       │                          │
│           │                       │   PostgreSQL / Snowflake │
│ .hxpack   │                       │   S3 / GCS data lake     │
│ .hxlic    │                       │   REST APIs              │
└───────────┘                       │   Kafka streams          │
                                    └──────────────────────────┘
```

## Integration Examples

| # | File | What It Shows | Tier |
|---|------|--------------|------|
| 01 | `01_server_evaluate.py` | Connect to hosted Helixor API, evaluate text with the regulatory PII playbook | 2: Server |
| 02 | `02_server_decision.py` | Decision-as-a-Function against the real server (SSE streaming) | 2: Server |
| 03 | `03_playbook_studio.py` | List, validate, compile, and admit playbooks via Studio API | 2: Studio |
| 04 | `04_ontology_binding.py` | Admit an ontology that binds concepts to external data sources | 3: Lattice |
| 05 | `05_governed_query.py` | Run governed queries through Lattice with access receipts | 3: Lattice |
| 06 | `06_langchain_guardrail.py` | LangChain guardrail using the local runtime | 2: Server |
| 07 | `07_batch_csv_pipeline.py` | Process CSV files through the runtime, write results | 0: Local |

## Lattice: The Governed Data Plane

Lattice is how external data sources connect to the decision runtime:

1. **Ontology binding** — Your ontology declares concepts (Supplier, Customer,
   Transaction). Sources (PostgreSQL, Snowflake, APIs) bind to those concepts
   in-place — rows never leave their stores.

2. **Policy at query lowering** — Access policies are expressed in the ontology
   vocabulary. Before any query resolves, Lattice applies row-level and
   field-level filtering based on the caller's role and clearance.

3. **Access receipts** — Every answer carries a cryptographic access receipt
   (SHA-256 digest of the admitted data, ontology TBox hash, and policy
   revision). Receipts are replayable for audit.

4. **MCP gateway** — External agents (agent frameworks, coding assistants) access
   governed data via the Lattice MCP surface: `lattice_query`,
   `lattice_simulate`, `lattice_receipt_verify`.

Lattice ships as a compiled pack evaluated by the runtime. The developer
configures ontology concepts and source connections; the governed resolution
is handled by the runtime. (As with every 0.2.x pack, the decrypted pack is
held in the host process's memory — see `docs/ARCHITECTURE.md`.)
