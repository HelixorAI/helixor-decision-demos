# Helixor Decision Demos — Developer Examples

> **Module**: `helixor-decision-demos`
> **Purpose**: Consumer-facing examples showing how to use the Helixor
> Decision Runtime (`helixor-runtime`) in-process decision engine.

## What This Repository Contains

This repository contains **only developer-facing example code**. It does NOT
contain engine source code, cryptographic implementations, decision logic,
extractors, or remedy algorithms. All of that lives in the `helixor-runtime`
package (a pure-Python reference implementation in 0.2.x; not a native
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
| `examples/01_quickstart.py` | Load the engine, evaluate payloads |
| `examples/02_batch_benchmark.py` | 5,000-payload throughput benchmark |
| `examples/03_stream_interceptor.py` | LLM prompt privacy gateway |
| `examples/04_streaming_token_interceptor.py` | Real-time sliding-window streaming |
| `examples/05_http_evaluation_service.py` | In-VPC HTTP/SSE microservice |
| `examples/06_decision_as_a_function.py` | REST + SSE + WebSocket protocols |
| `playbooks/regulatory_pii_guard.yaml` | Sample YAML playbook for cloud compilation |
| `docs/ARCHITECTURE.md` | Architecture overview |

## Conventions

- All examples import from `helixor_runtime`, never from internal modules.
- No engine source code, extractors, remedy logic, or cryptographic
  implementations belong in this repository. It is public and Apache-2.0;
  the runtime is proprietary (see `NOTICE`). `tests/test_repo_hygiene.py`
  fails if runtime source is vendored or internal modules are imported.
- `tests/contracts/` carries only the pruned OpenAPI operations the
  integrations call (`prune_openapi.py`), never the backend's full API.
- The `playbooks/` directory contains declarative YAML input files that are
  submitted to the Helixor Cloud Compiler to produce `.hxpack` binaries.
