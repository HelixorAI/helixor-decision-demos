# Helixor Decision Runtime: Demos and Tutorials

Runnable examples for the Helixor Decision Runtime, an in-process decision
engine. You pass it a payload; it returns an action from a closed set, the
rules that fired, a repaired payload and a receipt hash. Evaluation runs in
your Python process with no network or model calls.

The runtime in 0.3.x is a pure-Python reference implementation. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for exactly what it does and does
not protect.

This guide is the same seven steps as the
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
- the runtime wheel (`helixor_runtime-0.3.0-py3-none-any.whl`) and the
  constraint-network wheel it depends on
  (`helixor_constraint_network-1.0.1-py3-none-any.whl`), each with its
  SHA-256 checksum.

A web sign-up form is Planned; see
[Create an account](https://helixor.dev/guide/account.html#request-access).

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
shasum -a 256 ~/Downloads/helixor_runtime-0.3.0-py3-none-any.whl \
              ~/Downloads/helixor_constraint_network-1.0.1-py3-none-any.whl   # or sha256sum; compare with the emailed checksums
pip install ~/Downloads/helixor_constraint_network-1.0.1-py3-none-any.whl \
            ~/Downloads/helixor_runtime-0.3.0-py3-none-any.whl
python -c "import helixor_runtime as h; e = h.HelixorEngine(); print(h.__version__, e.pack_id, e.tier)"
```

```text
0.3.0 compliance.regulatory_pii_guard.v1 COMMUNITY
```

Install the runtime only from the wheels you were sent, and install both in
the same `pip install`. Neither is on any public package index, so
`pip install helixor-runtime`, or installing the runtime wheel without the
constraint-network wheel beside it, would make pip look for a package of that
name on the index and install whatever someone else publishes under it. This
repository does not declare either as a dependency for the same reason.

**Place your license.** Steps 4 to 6 run on the Community tier and need no
license file. Put your Developer license in place now so it is ready for your
own rules:

```bash
mkdir -p ~/.helixor
mv ~/Downloads/helixor.lic ~/.helixor/helixor.lic
chmod 600 ~/.helixor/helixor.lic
helixor-pack inspect-license
```

`inspect-license` prints your license ID, tier, expiry and whether the
signature verified. It needs the license you were issued, so it is the one
step here that was not part of the verified Community-tier run below.

### 4. Run your first decision

Evaluate four payloads against the runtime's built-in example pack (data
protection, `compliance.regulatory_pii_guard.v1`).

```bash
python examples/01_quickstart.py
```

```text
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
fingerprint of the decision that you can recompute. It is not signed.

### 5. Run three more examples

Each one shows a different use of the runtime.

**Guard a model prompt.** Decide on each prompt before it goes to a language
model: send it, send a redacted copy, or stop it.

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
email, phone number or SSN is emitted.

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

```bash
python use_cases/loan_recourse.py
```

```text
[1] Evaluating loan application...
  Approved:    False
  DTI:         0.512 (cap 0.43)
  Violations:  ['DTI_ABOVE_CAP']
...
  Flipped to approved:  True
  Minimal change:       monthly_debt 3,200 -> 2,600 (-600)
  Cost:                 0.1875
```

### 6. Make one change

The lending rules are the three constants at the top of
`use_cases/loan_recourse.py`. Tighten the debt-to-income cap and run it again:

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

- Run everything that works with the wheel alone: `./run_all.sh` (below).
- Write your own detection rules in a playbook and compile it with your
  Developer license: [Write a custom rule](https://helixor.dev/tutorials/custom-rules.html).
- Walk the rest of this repository: [the demo repository tour](https://helixor.dev/tutorials/demo-repo.html).

### How these steps were verified

Steps 2 to 6 were run as written, on a clean checkout of this repository,
Python 3.12, runtime wheels `helixor_runtime-0.3.0-py3-none-any.whl` and
`helixor_constraint_network-1.0.1-py3-none-any.whl`, on 2026-09-29. The outputs above are copied from that run (latencies vary by
machine). The actions, redactions and recourse amounts were checked
independently: the expected action for each input recomputed from its pattern
and a Luhn check, the emitted stream compared with the input redacted by
pattern, and the cheapest passing loan change recomputed by hand. The commands
took 8 seconds of machine time end to end, 2 of them installing the wheels.

## Run everything

```bash
./run_all.sh        # add -v to see the last lines of any failure
```

It prints one line per example: `PASS`, `FAIL` (exit status), `SKIP` (what the
example needs that the wheel does not provide) or `KNOWN` (a documented
runtime defect), then a summary, and exits non-zero on any `FAIL`. On a clean
checkout with only the runtime wheel installed:

```text
Result: 13 passed, 0 failed, 7 skipped, 1 known issues
```

To run the tests: `pip install -e ".[dev]"` then `python -m pytest`.

## What is in this repository

| Directory | What it is for |
|-----------|----------------|
| [`examples/`](examples/README.md) | The tutorial, 01 to 08, on the built-in example pack: evaluate, benchmark, guard prompts, stream, serve over HTTP, custom rules, generated SDK. |
| [`use_cases/`](use_cases/README.md) | Other engines in the runtime on business problems: recourse, forecasting, belief tracking, routing, rostering, sales. |
| [`integrations/`](integrations/README.md) | Patterns that connect the runtime to other systems: batch files, an agent-framework guardrail, and scripts for a Helixor server. |
| `playbooks/` | `regulatory_pii_guard.yaml`, the playbook of the built-in example pack, to read before you write your own. |
| [`sdks/`](sdks/README.md) | The typed Python and Java clients generated from the example pack's manifest. |
| `docs/` | [ARCHITECTURE.md](docs/ARCHITECTURE.md): what the 0.3.x runtime does and does not protect. |
| `tests/` | Checks that the examples compute what they print, and repository hygiene. |

## What runs with the runtime wheel alone

| Runs | Needs more | Known issue in runtime 0.3.0 |
|------|------------|------------------------------|
| `examples/01`–`08`, `use_cases/loan_recourse.py`, `demand_forecasting.py`, `belief_tracking.py`, `integrations/06`–`07` | `use_cases/fleet_routing.py`, `shift_rostering.py`: the `helixor-solvers` package, which is not part of the wheel. `integrations/01`–`04`: a Helixor server (`HELIXOR_API_URL`). `integrations/05`: governed data access, which is Planned. | `use_cases/sales_arbitration.py` stops with `FileNotFoundError: sales binding not found`: the wheel does not include the sales playbook. |

`integrations/05_governed_query.py` fails closed (`UNAVAILABLE`, exit 3):
governed data access is Planned. Its `--simulate` flag runs a local simulation
of the planned contract in which every line is marked `[SIMULATION]`.

## Solving: embedded or hosted

The solver runs in one of two deployment models, chosen explicitly. There is
no default and no fallback between them:

```python
HelixorSolver(mode="embedded", license=lic)                                   # in this process
HelixorSolver(mode="hosted", base_url=os.environ["HELIXOR_SOLVER_URL"],
              auth=os.environ["HELIXOR_SOLVER_TOKEN"])                         # the Helixor solver service
```

Both return the same answer:

- the verdict;
- the plan, only when it is feasible;
- otherwise the named shortfalls and ranked alternates, each saying what it relaxes;
- a certificate;
- metadata naming the model and the engine that ran.

Both raise the same typed errors. The use cases take one switch:

```bash
python use_cases/fleet_routing.py --mode embedded
HELIXOR_SOLVER_URL=... HELIXOR_SOLVER_TOKEN=... python use_cases/fleet_routing.py --mode hosted
```

Output of step 6 of `fleet_routing.py`, identical in both models. It was
verified on 2026-09-29 in both models; the hosted run used a local solver
service. The `engine` line names the engine that ran; it is abbreviated here.

```
[6] Plan the routes
  Served by: embedded            (hosted: "Served by: hosted", otherwise identical)
  Today as stated: verdict=infeasible, plan returned: False
    shortfall: Total demand is 74 units but the fleet carries 40 (1 vehicle(s) x 40); shortfall 34 units. ...
    shortfall: ferry-kiosk: the earliest possible arrival is 8.79h (depot opens 7h, direct drive 107 min) but its window closes at 7.5h; ...
    alternate #1: relaxes capacity 40.0 -> 74.0
    alternate #2: relaxes n_vehicles 1 -> 3
    alternate #3: relaxes visit_all_customers all stops -> 4 of 7 stops
  With a second van and the kiosk moved: verdict=feasible
    engine: local search (auto: time windows declared: the local search sequences against them)
    seed 28.8 km -> optimised 23.1 km in a 2 s budget
    vehicle 1: school -> cafe -> market  load 39, 12.8 km
    vehicle 2: clinic -> hotel -> bakery  load 29, 10.3 km
    late stops: 0; not enforced by the search: ['return_to_depot_deadline', 'max_driver_hours']
```

`shift_rostering.py --mode embedded|hosted` answers the demo week (a
registered-nurse shortfall of 12 h) as `verdict=infeasible`. No roster is
returned as the solution; the three ranked alternates each name the hard rule
they break. Embedded rostering needs the runtime's full solver engine.

## License

The code in this repository (examples, use cases, integrations, the demo
playbook, generated SDK client code and documentation) is licensed under the
[Apache License 2.0](LICENSE).

The Helixor runtime it calls is **not** covered by that license. It is
proprietary software of Helixor AI, Inc. (patent pending), licensed separately
and only under the Helixor Software License Agreement
(`helixor-software-license-agreement-v1`). Its published page is Planned.
See [NOTICE](NOTICE).
