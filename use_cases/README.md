# Phase 2: Use Case Showcase

After walking through the [PII Guard tutorial](../examples/README.md), explore
these use cases to see the full range of business problems the Helixor Decision
Runtime solves.

Every use case runs in-process on local CPU in microseconds with zero network
egress, zero LLM tokens, and tamper-evident audit proofs.

## Use Cases

| File | Business Problem | Key Features |
|------|-----------------|--------------|
| `fleet_routing.py` | **Logistics: Fleet Routing with Fallbacks** | Required vs optional inputs, pre-solve checks naming the shortfall, derived suggestions, ranked relaxed plans |
| `shift_rostering.py` | **Operations: Shift Rostering with Fallbacks** | Named hour shortfalls by week/skill/location, gate/hard/soft classes, least-bad rosters |
| `loan_recourse.py` | **Lending: Loan Approval with Counterfactual Recourse** | Pearl Level 3 causal search, CFPB/ECOA mandated recourse, stress testing |
| `demand_forecasting.py` | **Supply Chain: Adaptive Demand Forecasting** | Bayesian regime detection, 95% credible intervals, regime switching within a few observations |
| `sales_arbitration.py` | **Sales: Enterprise Dialogue Arbitration** | Intent classification, battle card citations, contact deferral rules |
| `belief_tracking.py` | **Operations: Epistemic Belief Tracking** | Beta posteriors, asymmetric falsification, contextual belief isolation |

## Running

```bash
# Each use case is self-contained
python use_cases/fleet_routing.py
python use_cases/shift_rostering.py
python use_cases/loan_recourse.py
python use_cases/demand_forecasting.py
python use_cases/sales_arbitration.py
python use_cases/belief_tracking.py
```

## What Problem Type Do You Have?

| If you need to... | Use this engine |
|---|---|
| Detect/redact PII, enforce regulatory invariants | `HelixorEngine` (PII Guard) |
| Route vehicles or roster shifts, with feasibility checks and fallbacks | `HelixorSolver` |
| Approve/deny with evidence, typed questions, abstention | `HelixorDecisionEngine` |
| Find minimal interventions to flip adverse decisions | `HelixorCounterfactualEngine` |
| Forecast demand with regime-aware Bayesian updating | `HelixorForecaster` |
| Arbitrate sales conversations with compliance rules | `HelixorSalesEngine` |
| Track confidence in hypotheses across contexts | `HelixorBeliefLedger` |

## Solver use cases: what runs and what needs a licence

`fleet_routing.py` and `shift_rostering.py` walk the same five steps:

1. **Inputs**: required vs optional fields, and the default the solver applies to each omitted optional field.
2. **Pre-solve checks**: necessary conditions. A failed check names the stop, week, skill or location and the exact shortfall, and certifies that no plan can meet it. A passing check proves nothing on its own.
3. **Suggestions**: the smallest changes the checks prove necessary, derived from your data and given as alternatives.
4. **Constraint classes**:
   - *Gates* are never broken.
   - *Hard* rules make a plan infeasible.
   - *Soft* rules are minimized among feasible plans.
   - For routing, the list also says which constraints the route builder checks.
5. **Ranked fallbacks**: when nothing is feasible, up to three least-bad answers, each saying what it relaxes.

Steps 1–4 need no licence. Step 5 plans routes or rosters, so it needs a licence entitled to the solver. Save the licence as `~/.helixor/helixor.lic` or set `HELIXOR_LICENSE_FILE`. Rostering fallbacks also need the full solver engine installed. Without either, step 5 prints the typed reason it did not run.

Routing plans come from a capacity-aware construction admitted against the hard constraints it checks. They are **not optimized**. Time windows and shift length are checked before planning only.
