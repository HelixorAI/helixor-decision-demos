# Use Cases

After the [tutorial examples](../examples/README.md), these scripts show the
runtime's other engines on business problems. Each is self-contained and runs
from the repository root. Timings they print are measured on your machine and
cover the engine call only.

## Use cases

| File | Business problem | Engine | Runs with the wheel alone |
|------|------------------|--------|---------------------------|
| `loan_recourse.py` | **Lending: loan approval with recourse.** A denied application gets the smallest change that would get it approved, then a stress test of the approved state. Getting-started steps 5 and 6. | `HelixorCounterfactualEngine` | Yes |
| `demand_forecasting.py` | **Supply chain: demand forecasting with regime switching.** A Bayesian forecaster switches regime after a run of surprising observations. | `HelixorForecaster` | Yes |
| `belief_tracking.py` | **Operations: belief tracking.** Confidence in a hypothesis per context, with contradictions weighted more than confirmations. | `HelixorBeliefLedger` | Yes |
| `fleet_routing.py` | **Logistics: fleet routing with feasibility checks and fallbacks.** | `HelixorSolver` | No: needs the `helixor-solvers` package |
| `shift_rostering.py` | **Operations: shift rostering with feasibility checks and fallbacks.** | `HelixorSolver` | No: needs the `helixor-solvers` package |
| `sales_arbitration.py` | **Sales: dialogue arbitration.** | `HelixorSalesEngine` | No: known issue in runtime 0.3.0 (below) |

```bash
python use_cases/loan_recourse.py
python use_cases/demand_forecasting.py
python use_cases/belief_tracking.py
```

### What the output shows, and what it does not

- **Loan recourse.** The rules are the three constants at the top of the file
  (`DTI_CAP`, `LTV_CAP`, `RESERVE_MONTHS`); edit one and re-run. The engine
  evaluates the candidate changes the script gives it and returns the cheapest
  passing one. It does not invent candidates.
- **Demand forecasting.** The `CI 95%` column is the forecaster's stated
  interval, not a calibrated one: in the demo run 8 of the 13 actuals fall
  outside it. Use it to see the regime switch, not as a coverage guarantee.
- **Belief tracking.** Beliefs are Beta posteriors per context; the numbers are
  the model's, not measured outcomes.

## Routing and rostering

`fleet_routing.py` and `shift_rostering.py` call `HelixorSolver`, which needs
the `helixor-solvers` package. That package is not part of the runtime wheel,
so with the wheel alone both scripts stop at their first step with
`SolverEngineUnavailableError` and `run_all.sh` reports them as `SKIP`. With
the package installed they walk six steps:

1. **Inputs**: required and optional fields, and the default applied to each omitted optional field.
2. **Pre-solve checks**: necessary conditions. A failed check names the stop, week, skill or location and the shortfall, and shows that no plan can meet it. A passing check proves nothing on its own.
3. **Suggestions**: the smallest changes the checks show are necessary, derived from your data.
4. **Constraint classes**: *gates* are never broken, *hard* rules make a plan infeasible, *soft* rules are minimized among feasible plans.
5. **Ranked fallbacks**: when nothing is feasible, up to three least-bad answers, each saying what it relaxes. This step also needs a license entitled to the solver (`~/.helixor/helixor.lic` or `HELIXOR_LICENSE_FILE`); without one it prints the typed reason it did not run.
6. **Solve**: `--mode embedded` or `--mode hosted` (see the top-level README). Without `--mode` the step says it did not run; there is no default model. It also needs the licence (embedded) or the service token (hosted).

In runtime 0.3.0, step 6 optimises routes: with time windows the local
search sequences stops against them; without them the hybrid genetic search
runs when the full solver engine is installed. The answer names the engine
that ran and the rules the search does not enforce (in the demo, the return
deadline and driver hours). Step 5's ranked fallbacks come from a
capacity-aware construction that does not check time windows, and say so.

## Known issue in runtime 0.3.0

`sales_arbitration.py` stops with
`FileNotFoundError: sales binding not found at .../site-packages/playbooks/sales_assistant.yaml`.
The engine looks for its playbook next to the installed package, and the wheel
does not include it. There is no workaround with the wheel alone; `run_all.sh`
reports it as `KNOWN`.

## Which engine fits your problem

| If you need to... | Engine |
|---|---|
| Detect and redact sensitive data, enforce regulatory rules | `HelixorEngine` (the built-in example pack) |
| Find the smallest change that flips an adverse decision | `HelixorCounterfactualEngine` |
| Forecast demand with regime-aware Bayesian updating | `HelixorForecaster` |
| Track confidence in hypotheses across contexts | `HelixorBeliefLedger` |
| Route vehicles or roster shifts, with feasibility checks and fallbacks | `HelixorSolver` (needs `helixor-solvers`) |
