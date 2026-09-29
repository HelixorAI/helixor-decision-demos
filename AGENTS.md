# Helixor Decision Demos — Developer Examples

> **Module**: `helixor-decision-demos`
> **Purpose**: Consumer-facing examples showing how to use the Helixor
> Decision Runtime (`helixor-runtime`) in-process decision engine.

## What This Repository Contains

This repository contains **only developer-facing example code**. It does NOT
contain engine source code, cryptographic implementations, decision logic,
extractors, or remedy algorithms. All of that lives in the `helixor-runtime`
package (a pure-Python reference implementation in 0.3.x; not a native
binary and not an opaque enclave — see `docs/ARCHITECTURE.md`).

## Developer API Surface

```python
from helixor_runtime import HelixorEngine

# Load a compiled pack and license into the in-process engine
engine = HelixorEngine.load_pack("guard.hxpack", license_file="helixor.lic")

# Evaluate — the runtime handles everything internally
result = engine.evaluate("Customer SSN is 123-45-6789.")

# Stream — wrap any token generator with the runtime's filter
for token in engine.stream_filter(llm_token_stream):
    print(token, end="")
```

## Files

| Path | Description |
| :--- | :--- |
| `examples/01_quickstart.py` | Evaluate payloads on the built-in example pack |
| `examples/02_batch_benchmark.py` | 5,000-payload throughput and latency measurement |
| `examples/03_prompt_interceptor.py` | Decide on a model prompt before dispatch |
| `examples/04_streaming_interceptor.py` | Redact or halt a token stream in flight |
| `examples/05_http_service.py` | HTTP/SSE service on a loopback port |
| `examples/06_decision_protocols.py` | REST + SSE + WebSocket |
| `examples/07_custom_rules.py` | Where custom rules go (Developer license) |
| `examples/08_generated_sdk_client.py` | The generated typed Python client |
| `use_cases/`, `integrations/` | See each directory's README |
| `playbooks/regulatory_pii_guard.yaml` | The built-in example pack's playbook |
| `run_all.sh` | Runs every example; PASS / FAIL / SKIP / KNOWN per line |
| `docs/ARCHITECTURE.md` | What the 0.3.x runtime does and does not protect |

The README's "Get started" section and https://helixor.dev/guide/quickstart.html
are the same seven steps with the same names. Change them together, and only
with output from a run on a clean checkout.

## Conventions

- All examples import from `helixor_runtime`, never from internal modules.
- No engine source code, extractors, remedy logic, or cryptographic
  implementations belong in this repository. It is public and Apache-2.0;
  the runtime is proprietary (see `NOTICE`). `tests/test_repo_hygiene.py`
  fails if runtime source is vendored or internal modules are imported.
- `tests/contracts/` carries only the pruned OpenAPI operations the
  integrations call (`prune_openapi.py`), never the backend's full API.
- The `playbooks/` directory contains declarative YAML playbooks; a Developer
  license compiles a playbook into a `.hxpack` with `helixor-pack compile`.
