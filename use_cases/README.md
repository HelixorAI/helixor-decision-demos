# Phase 2: Use Case Showcase

After walking through the [PII Guard tutorial](../examples/README.md), explore
these use cases to see the full range of business problems the Helixor Decision
Runtime solves.

Every use case runs in-process on local CPU in microseconds with zero network
egress, zero LLM tokens, and tamper-evident audit proofs.

## Use Cases

| File | Business Problem | Key Features |
|------|-----------------|--------------|
| `fleet_optimization.py` | **Logistics: Fleet Routing & Bin Packing** | VRP solver, capacity constraints, constraint networks |
| `loan_recourse.py` | **Lending: Loan Approval with Counterfactual Recourse** | Pearl Level 3 causal search, CFPB/ECOA mandated recourse, stress testing |
| `demand_forecasting.py` | **Supply Chain: Adaptive Demand Forecasting** | Bayesian regime detection, 95% credible intervals, regime switching within a few observations |
| `sales_arbitration.py` | **Sales: Enterprise Dialogue Arbitration** | Intent classification, battle card citations, contact deferral rules |
| `belief_tracking.py` | **Operations: Epistemic Belief Tracking** | Beta posteriors, asymmetric falsification, contextual belief isolation |

## Running

```bash
# Each use case is self-contained
python use_cases/fleet_optimization.py
python use_cases/loan_recourse.py
python use_cases/demand_forecasting.py
python use_cases/sales_arbitration.py
python use_cases/belief_tracking.py
```

## What Problem Type Do You Have?

| If you need to... | Use this engine |
|---|---|
| Detect/redact PII, enforce regulatory invariants | `HelixorEngine` (PII Guard) |
| Route vehicles, pack bins, verify constraints | `HelixorSolver` |
| Approve/deny with evidence, typed questions, abstention | `HelixorDecisionEngine` |
| Find minimal interventions to flip adverse decisions | `HelixorCounterfactualEngine` |
| Forecast demand with regime-aware Bayesian updating | `HelixorForecaster` |
| Arbitrate sales conversations with compliance rules | `HelixorSalesEngine` |
| Track confidence in hypotheses across contexts | `HelixorBeliefLedger` |
