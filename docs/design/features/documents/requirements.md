# Requirements: the documents: the executive view first, then the five pages

EARS (Mavin et al., RE'09, doi:10.1109/RE.2009.9). Every requirement names the gate that fails when it is violated.
The Introduction lands on the executive view (`content/executive.json`, held by the feature `web`) and carries the technical view second; the
Methodology, Implementation, Experiments and Benchmark pages follow in the shell's frame. The pages hold prose and read every number at run time from the committed
artifacts, so that a page never restates a figure by hand: the Experiments page fills bilingual templates from the manifests and traces, the Implementation page lists
the rows of the contract catalog, the Benchmark page reads `results.json`. The architecture modal (ADR-0058, five bilingual diagrams) has the feature `architecture`.

| ID | Requirement | Gate |
|---|---|---|
| DC-001 | THE technical view of the Introduction SHALL declare the five areas of ADR-0017 section 2.1 (problem, principles, math, pipeline, honesty), each with the content it requires. | `frontend/src/content/introduction/technical.test.tsx::declares the five areas of ADR-0017 section 2.1, each with the content it requires` |
| DC-002 | THE technical view SHALL carry no em-dash and no arrow in either language. | `frontend/src/content/introduction/technical.test.tsx::carries no em-dash, no arrow, and no DinHot measured number` |
| DC-003 | THE Experiments page SHALL read every checked range of every method as inside, because the bake fails outside it, and SHALL score the ranges from the manifest alone. | `frontend/src/content/experiments/experiments.test.tsx::reads every checked range of every method as inside (the bake passed them)` |
| DC-004 | THE Implementation page SHALL list the rows of the contract catalog in order, with the catalog's own version and producer cells. | `frontend/src/content/implementation/contract.test.ts::lists the rows of the catalog, in order, with their version and producer` |
