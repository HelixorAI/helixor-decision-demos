# Helixor Decision Runtime: Architecture Guide

## In-Process Decision Evaluation

---

## 1. Overview

The Helixor Decision Runtime is an **in-process decision engine**. You load it
with a compiled `.hxpack` policy pack and a signed `.hxlic` license file; it
then evaluates payloads inside your process, with no network calls on the
evaluation path and no LLM tokens. `HelixorEngine()` with no arguments loads
the built-in example pack on the Community tier, with no pack or license file;
that is what the examples in this repository use.

**Developer API surface:**

```python
from helixor_runtime import HelixorEngine

engine = HelixorEngine.load_pack("guard.hxpack", license_file="helixor.hxlic")
result = engine.evaluate(text)
```

`load_pack` verifies the license, decrypts the pack, and checks its
declarations. `evaluate` runs state extraction, invariant evaluation, remedy
synthesis, and audit-receipt generation, and returns a typed result.

### What ships today (0.3.x)

The current `helixor-runtime` build is a **pure-Python reference
implementation**. It is not a native binary and it is not an opaque enclave:

| Property | 0.3.x behaviour |
| :--- | :--- |
| Execution | Python, in the host process. No network calls while evaluating; zero LLM tokens. |
| Latency | Tens of microseconds per evaluation of the built-in pack: `examples/02_batch_benchmark.py` reported p50 18.3 µs on the author's machine (Python 3.12, runtime 0.3.0). `latency_us` covers evaluation only. Measure on your hardware. |
| License | Ed25519 signature verified against the pinned Helixor Authority public key. The validity window is checked at load and on every decision; an expired license fails closed. |
| Pack at rest | AES-256-GCM encrypted, bound to the pack id and license id, integrity-checked on load. |
| Pack key | The pack's content key is carried inside the `.hxlic` license. Anyone holding **both** the license and the pack can decrypt it. |
| Pack in memory | After loading, the decrypted rules are ordinary Python objects in the host process and can be inspected by code running in that process. |
| Audit receipts | A SHA-256-derived fingerprint per decision that you can recompute. Not signed, not keyed and not chained. |

Pack encryption keeps rules confidential from parties who hold the pack but
not the license (for example in transit or in shared storage). It is **not**
an intellectual-property or anti-inspection boundary against the licensee.
Treat pack contents as visible to anyone who can run the engine.

### Planned (not shipped)

A native runtime build and license-independent key wrapping (so the content key
is not recoverable from the license file) are planned. Until they ship, no
opacity or anti-reverse-engineering guarantee applies.

---

## 2. Deployment Boundary

```
+---------------------------------------------------------------------------------+
| CUSTOMER ENVIRONMENT (cloud VPC / on-prem)                                      |
|                                                                                 |
|   [ Application Code ]                                                          |
|          |                                                                      |
|          v                                                                      |
|   +---------------------------------------------+                              |
|   | HELIXOR RUNTIME (Python library, in-process) |                              |
|   |                                              |                              |
|   | • Verifies .hxlic, decrypts .hxpack at load  |                              |
|   | • Evaluates payloads in process              |                              |
|   | • Emits SHA-256 receipt fingerprints         |                              |
|   | • No network calls on the evaluate path      |                              |
|   +---------------------------------------------+                              |
|          |                                                                      |
|          v                                                                      |
|   [ DecisionResult: action, remedy, receipt_hash, latency_us ]                  |
+---------------------------------------------------------------------------------+
```

The runtime shares the host process's trust boundary: code in the same
process can read its memory, including the decrypted pack.

---

## 3. Statutory Invariants

The runtime evaluates inputs against the pack's statutory compliance invariants:

| Framework | Protected Invariant | Severity | Action |
| :--- | :--- | :--- | :--- |
| **GLBA & FCRA** | Social Security Numbers | **FATAL** | `block_glba_ssn_leakage` |
| **PCI-DSS (Req. 3)** | Primary Account Numbers (Luhn validated) | **FATAL** | `block_pci_dss_pan_leakage` |
| **HIPAA (45 CFR §164)** | Protected Health Identifiers | **FATAL** | `block_hipaa_phi_leakage` |
| **GDPR & CCPA** | Email addresses | **WARNING** | `redact_and_permit_contact_pii` |
| **TCPA & CCPA** | Telephone numbers | **WARNING** | `redact_and_permit_contact_pii` |
| **GDPR** | IPv4 addresses | **WARNING** | `redact_and_permit_contact_pii` |

---

## 4. Streaming Token Interception

The runtime provides a sliding-window streaming API that solves the
**Token Chunk Boundary Problem** — where sensitive entities are split
across multiple LLM token fragments:

```python
# Wrap any token generator with a real-time filter
for clean_token in engine.stream_filter(llm_token_stream):
    print(clean_token, end="")
```

Tokens like `"123"` + `"-45"` + `"-6789"` are buffered in a
lookahead window inside the runtime, detected as an SSN, and the
stream is halted before the sensitive data is emitted.

---

## 5. Transport Wrappers

The runtime can be exposed over HTTP, SSE, or WebSocket for polyglot
consumers (Go, Java, Node.js, C#). The transport layer is a thin wrapper;
all decision logic runs in the runtime process:

- `GET /v1/health` — Service health check
- `POST /v1/evaluate` — Synchronous evaluation
- `POST /v1/evaluate/stream` — SSE real-time token streaming
- `WS /v1/ws/decision` — Bi-directional WebSocket
