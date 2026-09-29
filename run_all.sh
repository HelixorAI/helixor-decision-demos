#!/bin/bash
# Run all locally-executable examples, use cases, and integrations.
# Examples that require a live server are skipped with a note.

set -e

echo "============================================================"
echo " HELIXOR DECISION DEMOS — FULL SWEEP"
echo "============================================================"

echo ""
echo "── Phase 1: Tutorial ──"
for f in examples/01_quickstart.py \
         examples/02_batch_benchmark.py \
         examples/03_prompt_interceptor.py \
         examples/04_streaming_interceptor.py \
         examples/07_custom_rules.py \
         examples/08_generated_sdk_client.py; do
    echo "  Running $f..."
    python3 "$f" > /dev/null 2>&1 && echo "    ✓ PASS" || echo "    ✗ FAIL"
done

echo ""
echo "── Phase 2: Use Cases ──"
for f in use_cases/fleet_routing.py \
         use_cases/shift_rostering.py \
         use_cases/loan_recourse.py \
         use_cases/demand_forecasting.py \
         use_cases/sales_arbitration.py \
         use_cases/belief_tracking.py; do
    echo "  Running $f..."
    python3 "$f" > /dev/null 2>&1 && echo "    ✓ PASS" || echo "    ✗ FAIL"
done

echo ""
echo "── Phase 3: Integrations (local only) ──"
for f in integrations/05_governed_query.py \
         integrations/06_langchain_guardrail.py \
         integrations/07_batch_csv_pipeline.py; do
    echo "  Running $f..."
    python3 "$f" > /dev/null 2>&1 && echo "    ✓ PASS" || echo "    ✗ FAIL"
done

echo ""
echo "── Skipped (require live server) ──"
echo "  integrations/01_server_evaluate.py     (needs HELIXOR_API_URL)"
echo "  integrations/02_server_decision.py     (needs HELIXOR_API_URL)"
echo "  integrations/03_playbook_studio.py     (needs HELIXOR_API_URL)"
echo "  integrations/04_ontology_binding.py    (needs HELIXOR_API_URL + Lattice)"
echo "  examples/05_http_service.py            (starts a server)"
echo "  examples/06_decision_protocols.py      (starts a server)"

echo ""
echo "============================================================"
echo " SWEEP COMPLETE"
echo "============================================================"
