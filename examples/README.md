# Tutorial Examples

A progressive walkthrough on the runtime's built-in example pack (data
protection, `compliance.regulatory_pii_guard.v1`). Each example adds one
capability. Install the runtime first (steps 1 to 3 of the
[README](../README.md#get-started)); every example below then runs from the
repository root with no license file.

## Community tier (no license file)

| # | File | What you learn |
|---|------|----------------|
| 01 | `01_quickstart.py` | `HelixorEngine()` with no arguments, `evaluate()`, and the result: action, clean output, receipt. Getting-started step 4. |
| 02 | `02_batch_benchmark.py` | Throughput and p50/p90/p99 latency of 5,000 evaluations, measured on your machine. `latency_us` covers evaluation only. |
| 03 | `03_prompt_interceptor.py` | Deciding on a prompt before it goes to a language model: send, send redacted, or stop. Getting-started step 5. |
| 04 | `04_streaming_interceptor.py` | Redacting a token stream in flight, halting it on a fatal match, and the sync and async stream filters. Getting-started step 5. |
| 05 | `05_http_service.py` | Serving the engine over HTTP and SSE. Starts its own server on a free loopback port and stops it. |
| 06 | `06_decision_protocols.py` | REST, SSE and WebSocket against the same engine. Starts and stops its own server. |

## Developer license

| # | File | What you learn |
|---|------|----------------|
| 07 | `07_custom_rules.py` | Where custom rules go. The built-in pack cannot be extended at run time; the example prints the steps to put a rule in a playbook and compile it with `helixor-pack compile` and your Developer license. It runs, and exits 0, on the Community tier. |

## Generated SDK

| # | File | What you learn |
|---|------|----------------|
| 08 | `08_generated_sdk_client.py` | The typed Python client generated from the pack manifest (`sdks/python`): typed state, `decide()`, `decide_batch()`. With no native library (Planned) it runs the generated Python evaluator, which it has to request explicitly (`allow_python_fallback=True`). The audit report needs the native library, so the example says so instead of printing one. |

## Running

```bash
python examples/01_quickstart.py        # one example
./run_all.sh                            # every example, one PASS/FAIL/SKIP line each
```

On the author's machine (Python 3.12, runtime 0.3.0), `02_batch_benchmark.py`
reported p50 18.3 µs and p99 21.1 µs. Measure on yours; the numbers depend on
the host and the payload.

## What's next

- [`use_cases/`](../use_cases/README.md): the runtime's other engines on business problems.
- [`integrations/`](../integrations/README.md): batch files, an agent-framework guardrail, and server scripts.
- [`sdks/`](../sdks/README.md): the generated SDKs.
