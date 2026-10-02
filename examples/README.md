# Tutorial Examples

A progressive walkthrough on the runtime's built-in example pack (data
protection, `compliance.regulatory_pii_guard.v1`). Each example adds one
capability. Install the runtime first (steps 1 to 3 of the
[README](../README.md#get-started)); every example below then runs from the
repository root, and all but 11 run with no license file.

## Community tier (no license file)

| # | File | What you learn |
|---|------|----------------|
| 01 | `01_quickstart.py` | `HelixorEngine()` with no arguments, `evaluate()`, and the result: action, clean output, receipt. Getting-started step 4. |
| 02 | `02_batch_benchmark.py` | Throughput and p50/p90/p99 latency of 5,000 evaluations, measured on your machine. `latency_us` covers evaluation only. |
| 03 | `03_prompt_interceptor.py` | Deciding on a prompt before it goes to a language model: send, send redacted, or stop. Getting-started step 5. |
| 04 | `04_streaming_interceptor.py` | Redacting a token stream in flight, halting it on a fatal match, and the sync and async stream filters. Getting-started step 5. |
| 05 | `05_http_service.py` | Serving the engine over HTTP and SSE. Starts its own server on a free loopback port and stops it. |
| 06 | `06_decision_protocols.py` | REST, SSE and WebSocket against the same engine. Starts and stops its own server. |
| 07 | `07_custom_rules.py` | Where custom rules go: the built-in pack does not know your identifiers, and `compile_custom_rule()` was removed in 0.3.0 (it raises `RemovedCapabilityError`, which says to use a playbook). Step 1 of [Add custom rules](https://helixor.dev/tutorials/custom-rules.html). |
| 09 | `09_receipts.py` | Recompute a receipt from what you log (never the payload) with the published `helixor.decision_receipt.v1` recipe; same input, same receipt; and a hash-chained audit log that shows a deleted line. [Receipts](https://helixor.dev/guide/receipts.html). |
| 10 | `10_outcome_memory.py` | `HelixorBeliefLedger`: how belief moves, routing a rule per segment by confidence, and snapshot/restore. Both scripts of [Track outcomes and confidence](https://helixor.dev/tutorials/outcome-memory.html), with the same output. |

The [Testing policies](https://helixor.dev/tutorials/testing-policies.html)
suite is in [`policy-tests/`](../policy-tests): `cd policy-tests && python -m pytest -q` (33 passed).

## Developer license

| # | File | What you learn |
|---|------|----------------|
| 11 | `11_compiled_pack.py` | Compile `playbooks/internal_ids.yaml` and `playbooks/order_notes.yaml` with `helixor-pack compile` and your license, load them with `HelixorEngine.load_pack()`, and check every action against [Add custom rules](https://helixor.dev/tutorials/custom-rules.html) and [Write your own decision pack](https://helixor.dev/tutorials/own-pack.html). Without a license it prints `NEEDS_LICENSE` and exits 4 (`run_all.sh`: `SKIP`). |

## Generated SDK

| # | File | What you learn |
|---|------|----------------|
| 08 | `08_generated_sdk_client.py` | The typed Python client generated from the pack manifest (`sdks/python`): typed state, `decide()`, `decide_batch()`. With no native library (Planned) it runs the generated Python evaluator, which it has to request explicitly (`allow_python_fallback=True`). The audit report needs the native library, so the example says so instead of printing one. |

## Running

```bash
python examples/01_quickstart.py        # one example
./run_all.sh                            # every example, one PASS/FAIL/SKIP line each
python scripts/check_docs.py            # outputs still match tests/expected/ and the README
```

On the author's machine (Python 3.12, runtime 0.3.0), `02_batch_benchmark.py`
reported p50 18.3 µs and p99 21.1 µs. Measure on yours; the numbers depend on
the host and the payload.

## What's next

- [`use_cases/`](../use_cases/README.md): the runtime's other engines on business problems.
- [`integrations/`](../integrations/README.md): batch files, an agent-framework guardrail, and server scripts.
- [`sdks/`](../sdks/README.md): the generated SDKs.
