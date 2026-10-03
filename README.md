# Helixor Decision Runtime: Demos and Tutorials

Runnable examples for the Helixor Decision Runtime, an in-process decision
engine. You pass it a payload; it returns an action from a closed set, the
rules that fired, a repaired payload and a receipt hash. Evaluation runs in
your Python process with no network or model calls.

The runtime in 0.3.x is a pure-Python reference implementation. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for exactly what it does and does
not protect.

## Start with a business problem

For shipping and purchasing, start with [domain_packs/](domain_packs/README.md).
It contains the policy drafts, 11 input cases and recorded runtime results from
the [domain-pack tutorials](https://helixor.dev/domain-packs/index.html).

- **Protect the stock reserve:** see why a 100-unit shipment is held when only
  120 units are available and 30 must remain in stock.
- **Send purchases to the right reviewer:** see how supplier status, amount and
  existing approval determine the review route.
- **Understand a policy change before release:** compare the same $3,000 request
  before and after lowering the manager-review threshold.

Clone this repository, then inspect the evidence with Python 3.11 or 3.12 alone:

<!-- verify -->
```bash
python3 domain_packs/review.py --check
```

```text
RECORDED EVIDENCE ONLY - no new policy execution or model inference
Verified 5 artifact hashes; 11/11 recorded outcomes match the example expectations.
```

Run without `--check` for the walkthrough, or add
`--case shipment-reserve-shortfall` to see the input and cited policy. This
inspection needs no runtime wheel or license. To evaluate new inputs, follow
the [Studio source-integration setup](domain_packs/README.md#2-run-new-inputs-in-studio-source-integration-preview);
the public 0.3.1 wheel does not expose that policy runner.

The embedded-runtime guide below is the same seven steps as the
[helixor.dev quickstart](https://helixor.dev/guide/quickstart.html). Once you
have access, steps 2 to 6 take under ten minutes.

## Get started

### 1. Get access

This repository is public; you can clone it now. The runtime is not on a
public package index. It comes with a Developer license, which you request by
email today:

- **To:** hello@helixor.ai
- **Subject:** Developer license request
- **Include:** your name, a work email, your organization, one sentence on what
  you want to decide.

A person at Helixor reviews each request. Once it is approved you receive:

- your Developer license file (`.hxlic`),
- the runtime wheel (`helixor_runtime-0.3.1-py3-none-any.whl`) and the
  constraint-network wheel it depends on
  (`helixor_constraint_network-1.0.1-py3-none-any.whl`), each with its
  SHA-256 checksum.

A web sign-up form is Planned; see
[Create an account](https://helixor.dev/guide/account.html#request-access).
Until you have access, the [hosted playground](https://helixor.dev/try/index.html)
shows decisions in your browser with no install.

### 2. Clone the demos

```bash
git clone https://github.com/HelixorAI/helixor-decision-demos
cd helixor-decision-demos
```

### 3. Install the runtime

Use Python 3.11 or 3.12. Check both wheels against the SHA-256 checksums you
were sent, then install them together, in one command, into a virtual
environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
shasum -a 256 ~/Downloads/helixor_runtime-0.3.1-py3-none-any.whl \
              ~/Downloads/helixor_constraint_network-1.0.1-py3-none-any.whl   # or sha256sum; compare with the emailed checksums
pip install ~/Downloads/helixor_constraint_network-1.0.1-py3-none-any.whl \
            ~/Downloads/helixor_runtime-0.3.1-py3-none-any.whl
```

Check that it loads:

<!-- verify -->
```bash
python -c "import helixor_runtime as h; e = h.HelixorEngine(); print(h.__version__, e.pack_id, e.tier)"
```

```text
0.3.1 compliance.regulatory_pii_guard.v1 COMMUNITY
```

Install the runtime only from the wheels you were sent, and install both in
the same `pip install`. Neither is on any public package index, so
`pip install helixor-runtime`, or installing the runtime wheel without the
constraint-network wheel beside it, would make pip look for a package of that
name on the index and install whatever someone else publishes under it. This
repository does not declare either as a dependency for the same reason.

**Place your license.** Steps 4 to 6 run on the Community tier and need no
license file. Put your Developer license in place now so it is ready for your
own rules (example 11):

```bash
mkdir -p ~/.helixor
mv ~/Downloads/<your-license-id>.hxlic ~/.helixor/helixor.hxlic
chmod 600 ~/.helixor/helixor.hxlic
helixor-pack inspect-license
```

Use the file name your license arrived with in place of
`<your-license-id>.hxlic`; the destination must be `~/.helixor/helixor.hxlic`.
The runtime looks for a license in this order: the path you pass
(`--license` or `license_file=`), `$HELIXOR_LICENSE_FILE`, `./helixor.hxlic`,
then `~/.helixor/helixor.hxlic` (a license saved under the older name
`helixor.lic` is still found). With none of them in place, commands that need
a license stop with `LICENSE_NOT_FOUND`, list the locations they checked and
say how to request one.
`inspect-license` prints your license ID, tier, expiry and whether the
signature verified. It needs the license you were issued, so it is the one
step here that was not part of the verified Community-tier run below.

### 4. Run your first decision

Evaluate four payloads against the runtime's built-in example pack (data
protection, `compliance.regulatory_pii_guard.v1`).

<!-- verify -->
```bash
python examples/01_quickstart.py
```

```text
  Pack:         compliance.regulatory_pii_guard.v1 (v1.0.0)
  Tier:         COMMUNITY

[Input]: "Employee onboarding: SSN is 123-45-6789, department operations."
  Action:         block_glba_ssn_leakage
  Compliant:      False
  Latency:        29.8 µs
  Tokens Spent:   0
  Network Egress: 0 bytes
  Audit Receipt:  hx_proof_9ee15305cfeef5e465f99c54
  Clean Output:   "Employee onboarding: SSN is [REDACTED_SSN], department operations."

[Input]: "Customer renewal card: 4111-1111-1111-1111, contact billing@acme.corp."
  Action:         block_pci_dss_pan_leakage
...
  Clean Output:   "Customer renewal card: [REDACTED_CARD_PAN], contact [REDACTED_EMAIL]."
```

Each result names the action, and the clean output has every match
redacted. The first fatal rule decides the action. `Tokens Spent` and
`Network Egress` are fixed at 0 by the runtime: they state that evaluation
calls no model and no network, they are not measured. The receipt is a SHA-256
fingerprint of the decision that you can recompute (example 09). It is not
signed. Latency is engine time on your machine and covers evaluation only.

### 5. Run three more examples

Each one shows a different use of the runtime.

**Guard a model prompt.** Decide on each prompt before it goes to a language
model: send it, send a redacted copy, or stop it.

<!-- verify -->
```bash
python examples/03_prompt_interceptor.py
```

```text
[Incoming Prompt]: "Please extract balance sheet data for applicant with SSN 123-45-6789."
  Status:     BLOCKED_BY_POLICY
  Dispatched: False
  Receipt:    hx_proof_cdda07f1432ca120935b65f2
  >> BLOCKED: Statutory violation: Social Security Number (GLBA / FCRA) detected

[Incoming Prompt]: "Draft a follow-up email to client at david@client.com or call (415) 555-0182."
  Status:     DISPATCHED_CLEAN
  Dispatched: True
  Receipt:    hx_proof_8d30ff02378ebfec840da53d
  >> SANITIZED: "Draft a follow-up email to client at [REDACTED_EMAIL] or call [REDACTED_PHONE]."
```

**Redact a stream in flight.** A value can be split across tokens. The
streaming filter holds back text until it can decide, so no fragment of an
email, phone number or SSN is emitted, and a fatal match halts the stream.

<!-- verify -->
```bash
python examples/04_streaming_interceptor.py
```

```text
  [RAW TOKEN]: 'sarah'
    --> [EMIT #3]: 'your '
  [RAW TOKEN]: '.connor'
...
    --> [EMIT #6]: '[REDACTED_EMAIL] or directly ' [REDACTED]
...
  [RAW TOKEN]: '123'
  [RAW TOKEN]: '-45'
  [RAW TOKEN]: '-6789'

  [!!! STREAM HALTED BY RUNTIME !!!]
  Action:   block_glba_ssn_leakage
```

**Find the smallest change that flips a decision.** A loan is denied on its
debt-to-income ratio. The counterfactual engine tries candidate changes, keeps
the ones that pass every rule, and returns the cheapest one.

<!-- verify -->
```bash
python use_cases/loan_recourse.py
```

```text
[1] Evaluating loan application...
  Approved:    False
  DTI:         0.512 (cap 0.43)
...
  Violations:  ['DTI_ABOVE_CAP']
...
    #5 [PASS] cost=0.1875  {'monthly_debt': {'delta': -600.0}}  DTI=0.416
  Flipped to approved:  True
  Minimal change:       monthly_debt 3,200 -> 2,600 (-600)
  Cost:                 0.1875
```

### 6. Make one change

The lending rules are the three constants at the top of
`use_cases/loan_recourse.py`. Tighten the debt-to-income cap and run it again:

<!-- verify -->
```bash
sed -i.bak 's/^DTI_CAP = 0.43/DTI_CAP = 0.40/' use_cases/loan_recourse.py
python use_cases/loan_recourse.py
```

```text
  DTI:         0.512 (cap 0.40)
...
    #5 [FAIL] cost=0.1875  {'monthly_debt': {'delta': -600.0}}  DTI=0.416
  Flipped to approved:  True
  Minimal change:       monthly_debt 3,200 -> 2,200 (-1,000)
  Cost:                 0.3125
```

The $600 paydown no longer passes, so the engine returns the $1,000 one. Put
the file back with `mv use_cases/loan_recourse.py.bak use_cases/loan_recourse.py`.

### 7. Where to go next

Run everything that works with the wheels alone. The policy tests in it use
pytest, so install that first:

<!-- verify -->
```bash
pip install pytest
./run_all.sh
```

```text
...
Result: 16 passed, 0 failed, 8 skipped, 0 known issues
```

`run_all.sh` prints one line per example: `PASS`, `FAIL` (exit status), or
`SKIP` with what the example needs that the wheels do not provide. It exits
non-zero on any `FAIL`; add `-v` to see the last lines of a failure. Without
pytest the policy tests are a `SKIP` too. The full run is under
[Run everything](#run-everything).

Then:

- Walk the documented concepts, one example each: [below](#one-example-per-concept).
- Write your own rules in a playbook and compile them with your Developer
  license: [Add custom rules](https://helixor.dev/tutorials/custom-rules.html), then example 11.
- Tour the repository: [the demo repository tour](https://helixor.dev/tutorials/demo-repo.html).

### How these steps were verified

Steps 2 to 7 were run as written, on a fresh clone of this repository, in a
new Python 3.12 virtual environment with only the runtime wheels
`helixor_runtime-0.3.1-py3-none-any.whl` and
`helixor_constraint_network-1.0.1-py3-none-any.whl` installed (both checked
against the release's `SHA256SUMS`), and no license file, on 2026-10-02. The
outputs above are copied from that run and trimmed; `...` marks trimmed lines,
and latencies vary by machine. `scripts/check_docs.py` re-runs every block
marked `<!-- verify -->` in this file and fails if its output no longer
contains the lines shown (see [Keeping docs and outputs honest](#keeping-docs-and-outputs-honest)).

## One example per concept

Each concept on helixor.dev that the embedded runtime supports in 0.3.1 has
one script here. The status is the portal's: **Available** runs in your
process today.

| Concept | Example | Portal page | Status | Tier |
|---------|---------|-------------|--------|------|
| Evaluate with the built-in example pack | `examples/01_quickstart.py` | [Make your first decision](https://helixor.dev/tutorials/first-guard.html) | Available | 0 |
| Guard a model call | `examples/03_prompt_interceptor.py`, `integrations/06_output_guardrail.py` | [Guard a model call](https://helixor.dev/tutorials/llm-gateway.html) | Available | 0 |
| Streaming redaction | `examples/04_streaming_interceptor.py` | [Decide on a stream](https://helixor.dev/tutorials/streaming-redaction.html) | Available | 0 |
| Batch, with an audit trail | `integrations/07_batch_csv_pipeline.py`; throughput: `examples/02_batch_benchmark.py` | [Batch processing](https://helixor.dev/guide/batch.html), [Audit pipeline](https://helixor.dev/tutorials/audit-pipeline.html) | Available | 0 |
| The decision service (HTTP, SSE, WebSocket) | `examples/05_http_service.py`, `examples/06_decision_protocols.py` | [Serve decisions to other languages](https://helixor.dev/tutorials/decision-service.html) | Available | 0 |
| Receipts: recompute, and chain your log | `examples/09_receipts.py` | [Receipts](https://helixor.dev/guide/receipts.html) | Available | 0 |
| Outcome memory | `examples/10_outcome_memory.py` | [Track outcomes and confidence](https://helixor.dev/tutorials/outcome-memory.html) | Available | 0 |
| Testing policies (golden set, properties, latency, streaming) | `policy-tests/` | [Testing policies](https://helixor.dev/tutorials/testing-policies.html) | Available | 0 (pack tests: 1) |
| Counterfactual recourse | `use_cases/loan_recourse.py` | [Quickstart](https://helixor.dev/guide/quickstart.html) steps 5 and 6 | Available | 0 |
| Where custom rules go | `examples/07_custom_rules.py`, `playbooks/internal_ids.yaml` | [Add custom rules](https://helixor.dev/tutorials/custom-rules.html) | Available | 0 |
| Compile and run your own pack | `examples/11_compiled_pack.py`, `playbooks/internal_ids.yaml`, `playbooks/order_notes.yaml` | [Add custom rules](https://helixor.dev/tutorials/custom-rules.html), [Write your own decision pack](https://helixor.dev/tutorials/own-pack.html) | Available | 1 (Developer license) |
| The generated typed client | `examples/08_generated_sdk_client.py` | [Python reference](https://helixor.dev/reference/python.html) | Available (native library Planned) | 0 |

`use_cases/demand_forecasting.py` and `use_cases/belief_tracking.py` show two
more engines in the wheel; see [use_cases/](use_cases/README.md).

**The policy tests.** `policy-tests/` is the tutorial's suite as written:

```bash
cd policy-tests
python -m pytest -q                       # 33 passed
POLICY_PACK=internal_ids.hxpack POLICY_LICENSE="$HOME/.helixor/helixor.hxlic" \
    python -m pytest -v pack_tests        # your compiled pack; needs your license
```

The pack tests fail (not skip) when either variable is unset or a file is
missing: a pack test that silently skips is not a test.

**Your own pack (Tier 1).** With your Developer license at
`~/.helixor/helixor.hxlic` (or in `HELIXOR_LICENSE_FILE`):

```bash
python examples/11_compiled_pack.py
```

It compiles `playbooks/internal_ids.yaml` and `playbooks/order_notes.yaml`
with `helixor-pack compile` into a temporary directory, loads each pack with
`HelixorEngine.load_pack()`, runs the tutorials' inputs and exits 1 if any
action differs from the tutorials. A compiled `.hxpack` is sealed to your
license: never commit one (`.gitignore` excludes them, and license files). In
0.3.1 a compiled pack runs your `regex` and `luhn_checksum` rules plus the
example pack's built-in checks; your own codons and `hard_rules` are rejected
by the compiler (Planned). Without a license the script prints `NEEDS_LICENSE`
with the runtime's `LICENSE_NOT_FOUND` guidance (the locations it checked and
how to request a license) and exits 4, and `run_all.sh` reports it as `SKIP`.

## Concepts that need the hosted service

These are on helixor.dev with their own runnable examples, against the
Helixor reasoning service or a digital worker. The embedded runtime in this
repository does not run them, so there is no code for them here.

| Concept | Portal page | Status | Where it runs |
|---------|-------------|--------|---------------|
| Probabilistic decisions: decision heads, calibrated probabilities, abstain / queue / refuse | [Probabilistic decisions](https://helixor.dev/guide/probabilistic-decisions.html) | Preview | Reasoning service |
| The rule language (`rules.dsl`) over typed facts, bound to an ontology | [Rule language](https://helixor.dev/guide/rule-language.html) | Preview | Digital workers |
| Asking the reasoning service, and handling abstentions | [Reasoning service](https://helixor.dev/tutorials/reasoning-service.html) | Preview | Reasoning service |
| Closing the learning loop, and rule proposals from outcomes | [Learning loop](https://helixor.dev/tutorials/learning-loop.html), [Rule proposals](https://helixor.dev/tutorials/rule-proposals.html) | Preview | Reasoning service |
| The sales assistant | [How the sales assistant was built](https://helixor.dev/tutorials/sales-assistant.html) | Preview | Reasoning service |
| Correctness forecast on reasoner answers | [Probabilistic decisions](https://helixor.dev/guide/probabilistic-decisions.html) | Planned | Reasoning service |

Access to the hosted service is not part of the Developer license request.
`integrations/01` to `04` are clients for a Helixor server; they need
`HELIXOR_API_URL` and are reported as `SKIP` without one.

## Run everything

On a fresh clone, in a Python 3.12 virtual environment with only the two
runtime wheels and pytest installed, and no license file (2026-10-02):

<!-- verify -->
```bash
./run_all.sh        # add -v to see the last lines of any failure
```

```text
Helixor decision demos: helixor_runtime 0.3.1, Python 3.12.13

Examples (PII Guard tutorial)
  PASS   examples/01_quickstart.py                  0.2s
  PASS   examples/02_batch_benchmark.py             0.3s
  PASS   examples/03_prompt_interceptor.py          0.2s
  PASS   examples/04_streaming_interceptor.py       0.9s
  PASS   examples/05_http_service.py                0.5s
  PASS   examples/06_decision_protocols.py          0.5s
  PASS   examples/07_custom_rules.py                0.2s
  PASS   examples/08_generated_sdk_client.py        0.1s
  PASS   examples/09_receipts.py                    0.2s
  PASS   examples/10_outcome_memory.py              0.2s
  SKIP   examples/11_compiled_pack.py             needs your Developer license (HELIXOR_LICENSE_FILE or ~/.helixor/helixor.hxlic)

Use cases
  PASS   use_cases/loan_recourse.py                 0.2s
  PASS   use_cases/demand_forecasting.py            0.2s
  PASS   use_cases/belief_tracking.py               0.2s
  SKIP   use_cases/fleet_routing.py               needs the helixor-solvers package (not in the runtime wheel)
  SKIP   use_cases/shift_rostering.py             needs the helixor-solvers package (not in the runtime wheel)

Integrations
  PASS   integrations/06_output_guardrail.py        0.2s
  PASS   integrations/07_batch_csv_pipeline.py      0.2s
  SKIP   integrations/05_governed_query.py        governed data access is Planned (fails closed)
  SKIP   integrations/01_server_evaluate.py       needs a Helixor server (HELIXOR_API_URL)
  SKIP   integrations/02_server_decision.py       needs a Helixor server (HELIXOR_API_URL)
  SKIP   integrations/03_playbook_studio.py       needs a Helixor server (HELIXOR_API_URL)
  SKIP   integrations/04_ontology_binding.py      needs a Helixor server (HELIXOR_API_URL)

Policy tests (golden set, properties, latency budget, streaming)
  PASS   policy-tests/ (33 passed)                  0.4s

Result: 16 passed, 0 failed, 8 skipped, 0 known issues
```

A `SKIP` names what the example needs and is never counted as a pass.
`integrations/05_governed_query.py` must fail closed (`UNAVAILABLE`, exit 3)
to be a `SKIP`: governed data access is Planned. Its `--simulate` flag runs a
local simulation of the planned contract in which every line is marked
`[SIMULATION]`. With your Developer license in place, example 11 runs as well.

To run the repository's own tests: `pip install -e ".[dev]"` then
`python -m pytest`.

## Keeping docs and outputs honest

```bash
python scripts/check_docs.py            # exit 1 on any difference
python scripts/check_docs.py --update   # after a deliberate change: rewrite tests/expected/, then review the diff
```

It makes two checks, with no license file in reach (an empty `HOME`) so the
results are the Community tier's:

- **Example outputs.** Every example that runs with the wheels alone is run
  and its output compared line for line with `tests/expected/`. Timings, ports
  and clock values are replaced by placeholders; every action, rule ID,
  receipt, redaction and count must match.
- **README commands.** Every command block in this README marked
  `<!-- verify -->` is run, in order, in a scratch copy of the repository,
  and the output block after it must appear in what it prints.

`python -m pytest` runs the same check (`tests/test_docs_outputs.py`).

**No hosted CI.** This repository has no GitHub Actions workflow. The domain-pack
evidence checks and repository-hygiene tests run without the runtime. The other
checks need the licensed runtime
wheels, which are never committed here, so the checks are run locally against
the released wheels before each change is published: `run_all.sh`,
`scripts/check_docs.py` and `python -m pytest`. Run the same commands after
installing the wheels you were sent to check your own copy.

## What is in this repository

| Directory | What it is for |
|-----------|----------------|
| [`domain_packs/`](domain_packs/README.md) | Shipping and purchasing policy bundles, 11 cases, a recorded-evidence walkthrough, and Studio setup for new decisions. Run `python3 domain_packs/review.py` separately from the runtime examples in `run_all.sh`. |
| [`examples/`](examples/README.md) | The tutorial, 01 to 11, on the built-in example pack: evaluate, benchmark, guard prompts, stream, serve, custom rules, generated SDK, receipts, outcome memory, your own compiled pack. |
| [`use_cases/`](use_cases/README.md) | Other engines in the runtime on business problems: recourse, forecasting, belief tracking, routing, rostering. |
| [`integrations/`](integrations/README.md) | Patterns that connect the runtime to other systems: batch files, an agent-framework guardrail, and scripts for a Helixor server. |
| `playbooks/` | `regulatory_pii_guard.yaml`, the playbook of the built-in example pack, to read before you write your own; `internal_ids.yaml` and `order_notes.yaml`, the two tutorial playbooks example 11 compiles. |
| `policy-tests/` | The "Testing policies" tutorial's pytest suite: golden set, properties, latency budget, streaming, and tests for your compiled pack. |
| `docs/` | [ARCHITECTURE.md](docs/ARCHITECTURE.md): what the 0.3.x runtime does and does not protect. |
| `scripts/` | `check_docs.py`: re-runs the examples and the README's commands and compares. |
| `tests/` | Checks that the examples compute what they print, their pinned outputs (`tests/expected/`), and repository hygiene. |

## Solving: embedded or hosted (Preview)

`use_cases/fleet_routing.py` and `shift_rostering.py` call `HelixorSolver`,
which runs in one of two deployment models, chosen explicitly with
`--mode embedded` or `--mode hosted`. There is no default and no fallback
between them. Neither runs with the wheels in this guide:

- **Embedded** needs the `helixor_solvers` wheel, which ships in the private
  release of a later runtime release (Planned; 0.3.1 does not include it),
  and a license carrying the `solver.embedded` feature. Without it the scripts
  stop at their first step with `SolverEngineUnavailableError`.
- **Hosted** needs access to the Helixor solver service
  (`HELIXOR_SOLVER_URL`, `HELIXOR_SOLVER_TOKEN`), which is not part of the
  Developer license request.

What each script prints in both models, and what it checks before solving, is
in [Solving routes and rosters, embedded or hosted](https://helixor.dev/tutorials/solver-deployment-models.html)
(Preview) and [use_cases/README.md](use_cases/README.md).

## License

The code in this repository (examples, use cases, integrations, the demo
playbooks, policy tests, generated SDK client code and documentation) is
licensed under the [Apache License 2.0](LICENSE).

The Helixor runtime it calls is **not** covered by that license. It is
proprietary software of Helixor AI, Inc. (patent pending), licensed separately
and only under the Helixor Software License Agreement
(`helixor-software-license-agreement-v1`). Its published page is Planned.
See [NOTICE](NOTICE).
