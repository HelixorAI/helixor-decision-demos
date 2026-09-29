# Integration Examples

Patterns that connect the runtime to other systems. Two run locally with the
runtime wheel alone, four are clients for a Helixor server and need one, and
one (05) is for a Planned capability and fails closed.

## Run locally

| # | File | What it shows |
|---|------|---------------|
| 06 | `06_output_guardrail.py` | A guardrail that passes model output through the runtime before it reaches the user: clean text passes, PII is redacted or blocked. It is a plain callable with no framework dependency. The model outputs are canned sample text, so no model is needed; the decisions on them are real runtime results. |
| 07 | `07_batch_csv_pipeline.py` | A CSV of customer records through the runtime, field by field: a clean CSV plus a per-field report with rules and receipts. |

```bash
python integrations/07_batch_csv_pipeline.py
```

## Need a Helixor server

These scripts call a Helixor reasoning server over HTTP. Access to a server
and an API key is not part of the Developer license request; ask for it
separately if you need it. `run_all.sh` reports them as `SKIP`.

| # | File | What it shows |
|---|------|---------------|
| 01 | `01_server_evaluate.py` | Evaluate text with the regulatory playbook through the server. |
| 02 | `02_server_decision.py` | A typed decide call, a streamed reasoning chat over SSE, and a playbook turn. |
| 03 | `03_playbook_studio.py` | List, validate, compile and admit a playbook through the server. |
| 04 | `04_ontology_binding.py` | Submit an ontology that binds concepts to data sources. Source binding is Planned. |

```bash
pip install httpx
export HELIXOR_API_URL=<your Helixor server URL>
export HELIXOR_API_KEY=<your API key>
python integrations/01_server_evaluate.py
```

The request bodies these scripts send are checked against a pruned copy of the
server's API contract in `tests/contracts/` (see its README).

## Governed data (Planned)

Lattice is the planned governed data plane: data sources bind to ontology
concepts, access policy applies before a query resolves, and each answer
carries an access receipt. It is not shipped, in the runtime wheel or in any
Helixor service.

| # | File | What it does |
|---|------|--------------|
| 04 | `04_ontology_binding.py` | Submits an ontology that declares source bindings and policies, and reads it back. The server admits the ontology; it does not bind the sources. |
| 05 | `05_governed_query.py` | Fails closed: prints `UNAVAILABLE: ...` and exits with status 3, because there is no governed data plane to query. `run_all.sh` reports it as `SKIP`. |

```bash
python integrations/05_governed_query.py              # UNAVAILABLE, exit 3
python integrations/05_governed_query.py --simulate   # labelled local simulation
```

`--simulate` shows the shape of the planned contract with rows the script makes
up: the same query admits different fields for different roles, and each
answer carries a SHA-256 digest of what was admitted. Every line it prints
starts with `[SIMULATION]`. No data source, policy engine or signing key is
involved, so it reports nothing as verified. It does recompute the digest from
the rows, to show that changing a row changes the digest; the digest is
unsigned, so it shows the rows match, not who produced them.
