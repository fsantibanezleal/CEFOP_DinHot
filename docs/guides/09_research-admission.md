# Declaring a research study and its admission provider

An evaluation protocol or dataset is not a proposed forecasting method merely
because it has a paper. The software design document can declare these other
contributions in `## Novel contributions`, with identifiers `NC-1`, `NC-2` and
their actual scientific scope. A product manuscript can list those identifiers
in its `product.json` entry's `covers`. Method proposals continue to use the
existing identifiers and their separate method section. Empty coverage and
identifiers mentioned only in another section or a code example are rejected.

This distinction does not certify novelty, scientific validity, content depth
or publication readiness. Those remain separate reviews and checks. Coverage
must describe what the paper actually supports. A dataset manuscript must not
claim an unrelated model just to satisfy a metadata gate.

Some products admit immutable research studies rather than the template's
example-engine readiness document. They declare their existing read-only
validator in `scripts/local/workflow.json`:

```json
{"product_admission": true, "readiness_provider": "scripts/local/producer_bridge.py"}
```

The script exports `validate(root)`. It verifies the complete current catalog,
payload and scientific bindings, returning normally on success and raising an
exception on refusal. Returning `False` is also refusal. Validation never
generates artifacts, trains a model or promotes a candidate. Provider paths
stay within the checkout without symlinks or junctions. A missing declaration
for custom admission fails explicitly rather than importing an absent template
engine. Products that use the default engine keep its existing readiness path.
