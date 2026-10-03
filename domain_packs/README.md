# Business decisions: shipping and purchasing

Start with a decision an operations team has to make, then inspect the facts,
policy and reason behind the result. These are original illustrative policies,
not customer deployments or measured cost savings.

| Business problem | Example | What you can inspect |
| --- | --- | --- |
| An order looks ready, but shipping it would consume the stock reserve. | [Shipment release](https://helixor.dev/domain-packs/shipment-release.html) | Stock, reserve and quality checks; exact boundary; missing quality status. |
| Staff send similar purchases to different reviewers. | [Purchase review](https://helixor.dev/domain-packs/purchase-review.html) | Supplier review takes priority; amount and approval decide the next route; missing approval blocks the check. |
| Finance wants to lower the approval threshold without surprising operations. | [Policy change](#compare-a-policy-change) | The same $3,000 request goes from the standard process to manager review when the threshold changes from $5,000 to $2,500. |

## 1. Inspect the recorded cases locally

**Prerequisites:** Git and Python 3.11 or 3.12. No packages, license file,
model weights, API keys, GPU or server are needed for this step.

From the repository root:

```bash
python3 domain_packs/review.py
python3 domain_packs/review.py --case shipment-reserve-shortfall
python3 domain_packs/review.py --case purchase-unapproved-supplier
python3 domain_packs/review.py --check
```

The first command walks through all 11 cases. Selecting a case shows its input,
recorded rule IDs and cited policy. `--check` verifies the five artifact hashes
and compares the recorded outcomes to the declared expectations; it exits 2 if
evidence is missing, changed or inconsistent. An unknown case exits 2 too.

Every run is labeled **RECORDED EVIDENCE ONLY**. These results came from a
structured-input run through the policy draft validator and declarative runtime
on 2026-10-03. This script reads and checks that evidence. It does not evaluate
rules, parse English, load a neural model, approve a policy, or execute a business
action. Editing an input invalidates its hash; it does not produce a new decision.
The hashes detect file drift, not authenticity or approval.

## 2. Run new inputs in Studio (source integration preview)

You need a provisioned Studio source-integration environment with the policy
authoring backend and declarative reasoning runtime, persistent draft/review
storage, and your normal authenticated access. This capability is not included
in the public 0.3.1 runtime wheel. A Developer license alone does not provision it.
Ask your Helixor integration contact for the Studio URL and access, or follow the
[Studio setup and workflow](https://helixor.dev/domain-packs/studio.html).
There is no public one-command server install for this preview.

1. Import `shipment-release.json` or `purchase-review.json` into Studio's policy
   authoring flow. Each file contains `source`, `specification` and `draft`.
2. Inspect the policy paragraphs, rule citations, rule order, allowed actions,
   required fields and unresolved source bindings. These example fields read
   directly from structured state; they do not connect to an inventory or
   purchasing system.
3. Enter the expected-answer and blocked test cases through the typed form.
   Cover every decision and rule. Record a review of the exact revision, have a
   different administrator approve the immutable release, then select **Install
   in runtime**. Importing a draft is not approval, and editing it invalidates
   earlier test/review evidence.
4. Choose the decision (`shipment` or `purchase_route`) and copy the `state`
   object from an entry in `cases.json` under **Run the installed policy**.
   Compare the fresh result with that entry's `expected_action` and the matching
   record's rule IDs or failure code. `cases.json` is a fixture list, not a Studio
   batch-import format.
5. Change one fact and run again. For shipping, try 120, 130 and 150 available
   units with a 100-unit order and a 30-unit reserve. Remove `quality_hold` and
   verify the run blocks with `VALUE_MISSING` instead of assuming clearance.

For purchasing, compare $5,000 with $5,001 while `approved_supplier` is true and
`manager_approved` is false. Then set `approved_supplier` to false: supplier
review takes priority. Removing `manager_approved` must block the check.

The result is a routing/check outcome. Your application still controls permission
to ship, place an order or pay. A real deployment must bind the required facts to
reviewed authoritative sources and define freshness and failure behavior.

### Compare a policy change

`purchase-review-v2.json` changes the example threshold to $2,500. Inspect both
the policy paragraph and the cited executable condition. `recorded-results.json`
includes the before/after result for the same $3,000 request.

The two fixture files have distinct example pack IDs so they can be inspected
side by side. For a real Studio version change, create a new revision of the
**same pack**, update its source and draft, test affected cases, review the changed
content and activate the admitted revision. Do not treat the separate v2 fixture
as an already approved replacement or copy an approval from v1.

## Where the language model fits

These examples isolate policy behavior using typed facts. A configured neural
lowerer can propose a supported decision and typed candidate fields from English;
validation, admission and the runtime still determine what may execute. The
shipped examples contain no trained model or calibrated model binding.

To inspect the separate language-model evidence, follow
[native lowering benchmarks](https://helixor.dev/benchmarks/native-lowering.html)
and its downloadable standard-library audit. Its reported 221/233 candidate
matches are not authorized decisions: that snapshot admitted zero cases. The
11 policy cases here do not measure language-understanding accuracy.

## Files and provenance

| File | Purpose |
| --- | --- |
| `shipment-release.json` | Shipping policy source, typed specification and draft. |
| `purchase-review.json` | Purchasing policy with a $5,000 threshold. |
| `purchase-review-v2.json` | Comparison fixture with a $2,500 threshold. |
| `cases.json` | Eleven inputs, expected actions and business explanations. |
| `recorded-results.json` | Recorded runtime outcomes, revision comparison and input hashes. |
| `manifest.json` | Hashes of all five artifacts and their publication provenance. |
| `review.py` | Offline integrity check and recorded-evidence walkthrough. |

The five JSON artifacts are byte-for-byte copies of the downloads linked from
the [domain-pack tutorials](https://helixor.dev/domain-packs/index.html).
`manifest.json` records the publication revision. Refresh all affected artifacts
together after a new source-integration run; changing checksums alone is not a
new evaluation.

This folder is separate from the older `playbooks/*.yaml` compiled-pack examples
and `integrations/03_playbook_studio.py`. That older client does not implement
the policy source/draft/review/version workflow described here.
