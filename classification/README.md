# Classify an incoming order question

An operations inbox receives questions in different words. Before checking stock
or delivery dates, the application needs to know **which question is being asked**.
This is a classic intent-classification task: English in, one category from a
fixed set out.

| Category | Meaning | Use after admission |
| --- | --- | --- |
| `fulfillment` | Can this order be fulfilled from stock? | Start the declared fulfillment assessment. |
| `expedite` | Does this order need faster delivery? | Start the declared expedite assessment. |
| `unsupported` | Outside the supported single-question contract. | Ask for clarification or send to a person. |

The application has already selected the order. This model does not resolve order
identity, decide whether stock is sufficient, or authorize shipping or a courier
upgrade. Those require validated facts and the reasoning/runtime path.

## Inspect actual model predictions

Prerequisites: clone this repository and use Python 3.11 or 3.12. These commands
need only the standard library, with no wheel, license, model download, API key,
GPU or server:

```bash
python3 classification/review.py
python3 classification/review.py --case ontology.test.00.02 --json
python3 classification/recompute.py
```

The walkthrough shows five **recorded model predictions**, including two errors.
The JSON option shows how software consumes a finite category and scores; Python
serializes this object. The neural model did not generate JSON tokens.
`recompute.py` checks evidence hashes and recalculates the published aggregate,
calibration and timing figures. Both commands stop on inconsistent evidence.
They inspect the recorded run, not new English input.

For example, “Does the extractor order need a faster courier to make the
customer's date?” received `expedite` with a 97.89% model score. “Before the
carrier pickup, go ahead and send the Langstroth hive-body order out from stock.”
received `unsupported`: it asks for an action rather than the supported assessment.

The hard example asks both about a quality hold and whether normal delivery will
miss a deadline. The model picked `expedite` with 98.38%, but the expected label
is `unsupported` because the contract accepts one assessment at a time.
This is why a high score alone is not a release gate.

## The pipeline and the business handoff

```text
English question + declared categories
    -> neural encoder -> vector -> finite category scores
    -> typed candidate -> validation and calibration admission
    -> declared assessment OR clarification / human review
```

With a qualified model binding, the application could use an admitted category to
choose the appropriate stock or delivery check. The runtime would then fetch the
declared facts and apply the reviewed policy. Classification selects the check;
the policy determines its result; application permissions govern any action.

**In this recorded snapshot, admission remains closed.** Candidate accuracy was
221/233 (94.85%), but no threshold met the calibration requirement of at least
98% observed precision with 30 accepted calibration cases. All 233 test candidates
were withheld. Even a correctly predicted category in this demo is not an
admitted route. `unsupported` is a category; `accepted: false` is the separate
admission outcome. A business application should request review or clarification
while the binding is unqualified.

The labels are synthetic model-authored/model-judged examples, not human-reviewed
business ground truth. This is evidence for a bounded classification task, not
an inbox deployment or a promise of production accuracy. The intended business
value is less manual triage; time saved and routing quality still need to be
measured on representative requests.

## Run fresh inference in the source integration

The public runtime 0.3.1 wheel has no classifier entry point for this trained
model. You need the source integration with its declared native provider, the
controlled checkpoint and tokenizer, the exact language contract and calibration
artifact, and a compatible model binding. These artifacts are not distributed in
this public repository. See [native language lowering](https://helixor.dev/domain-packs/native-lowering.html)
and [prepare a language contract](https://helixor.dev/tutorials/domain-contract.html).
Do not substitute the recorded-output script for a live provider or loosen the
calibration gate to turn this example into an automatic route.

## Evidence provenance

`manifest.json`, `predictions.json`, `calibration.json`,
`provider-regression.json` and `recompute.py` are unchanged copies of the
[published native-lowering evidence](https://helixor.dev/benchmarks/native-lowering.html#reproduce),
recorded on 2026-10-03. The manifest identifies the source snapshot, model and
contract digests, hardware, splits, labeling limits and data-file hashes.
`review.py` selects readable examples from the full 233-row record; its five
examples are an explanation, not a separate benchmark sample.
