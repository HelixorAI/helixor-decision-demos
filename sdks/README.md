# Generated SDKs

When you install a Helixor decision pack, you get **two things**:

1. **The runtime** (`helixor-runtime`) — the in-process decision engine (pure Python in 0.2.x; a native `.dylib`/`.so` build is planned, not shipped)
2. **A typed SDK for your language** — generated automatically by [`helixor-sdk-gen`](https://github.com/HelixorAI/helixor-sdk-gen)

The SDK is generated from the pack's manifest (its state schema, hard rules,
actions, and codons) so every field, type, and constraint is correct by
construction. No hand-written wrappers, no guessing field names.

## What's Included

```
sdks/
├── embedded-pack-manifest.json           # Pack IR used for generation
├── python/regulatorypiiguard/            # Python SDK
│   ├── __init__.py
│   ├── models.py                         # Pydantic models (typed state, results, causes)
│   ├── client.py                         # RegulatoryPiiGuardClient with .decide()
│   └── runtime_bridge.py                 # Native C FFI → GraalVM → Python fallback
└── java/                                 # Java SDK
    ├── pom.xml
    └── src/main/java/ai/helixor/runtime/regulatorypiiguard/
        ├── model/                        # Java records (state, result, counterfactual)
        ├── client/                       # Typed client
        └── playbook/                     # Compiled playbook with invariant rules
```

## Python Usage

```python
from regulatorypiiguard import RegulatoryPiiGuardClient, RegulatoryPiiGuardState

client = RegulatoryPiiGuardClient(
    pack_path="regulatory_pii_guard.hxpack",       # compiled pack binary
    native_lib_path="libhelixor_regulatory.dylib",  # native runtime
)

state = RegulatoryPiiGuardState(
    has_ssn=True,
    has_credit_card=False,
    has_health_record=False,
    has_email=True,
    has_phone=False,
    has_ip=False,
)

result = client.decide(state)
print(result.verdict)          # DecisionVerdict.REFUSE
print(result.proof_sha256)     # e705e2d2...
print(result.latency_us)       # 1.96
print(result.is_approved)      # False
print(result.necessary_causes) # [NecessaryCause(factor='has_ssn', ...)]
```

## Java Usage

```java
import ai.helixor.runtime.regulatorypiiguard.client.RegulatoryPiiGuardClient;
import ai.helixor.runtime.regulatorypiiguard.model.RegulatoryPiiGuardState;
import ai.helixor.runtime.regulatorypiiguard.model.DecisionResult;

var client = RegulatoryPiiGuardClient.builder()
    .nativeLibPath("libhelixor_regulatory.dylib")
    .build();

var state = RegulatoryPiiGuardState.builder()
    .hasSsn(true)
    .hasCreditCard(false)
    .hasHealthRecord(false)
    .hasEmail(true)
    .hasPhone(false)
    .hasIp(false)
    .build();

DecisionResult result = client.decide(state);
System.out.println(result.verdict());   // REFUSE
System.out.println(result.latencyUs()); // 1.96
```

## How Generation Works

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│  Pack YAML   │────▶│  helixor-sdk-gen │────▶│  Typed SDK   │
│  (playbook)  │     │  (cloud or CLI)  │     │  (py/java/ts)│
└──────────────┘     └─────────────────┘     └──────────────┘
       │                                            │
       ▼                                            ▼
┌──────────────┐                             ┌──────────────┐
│ Pack Manifest│                             │ Runtime      │
│   IR (.json) │                             │ (pure Python)│
└──────────────┘                             └──────────────┘
```

1. You author a pack playbook (YAML) defining state schema, rules, and actions
2. `helixor-sdk-gen` lowers it to a `PackManifestIR`
3. Language emitters generate typed models, clients, and runtime bridges
4. (Planned, not shipped in 0.2.x) GraalVM Native Image compiles the playbook into a C-ABI shared library
5. You ship the runtime + the generated SDK — developers get both on install

## Regenerating Locally

```bash
# From the internal demos repo (requires helixor-sdk-gen installed)
python scripts/generate_runtime_sdk.py

# Or via CLI
helix-sdk-gen generate helix-sdk.yml openapi.yaml --out ./sdks --local
```
