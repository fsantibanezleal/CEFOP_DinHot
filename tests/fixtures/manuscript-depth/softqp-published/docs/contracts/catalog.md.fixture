# SoftQP scientific contract catalog

Phase 2 of contract-first parallel delivery (ADR-0080; rule 11 sections 11 to 20 in CAOS_MANAGE). One row per
boundary and per model slot. Each schema file is the single source of its contract: the Python producers and
consumers validate against it in their tests, and the TypeScript types are generated from it
(`frontend/src/lib/contract.gen.ts`, from `docs/contracts/api.openapi.json`, whose components reference the schema
files). A change to a contract bumps its row's version and updates both sides in one pull request.

Checks: `python scripts/check_contracts.py docs/contracts/catalog.md --repo-root .` (every field, every path) and
`python scripts/check_skeleton.py docs/contracts/catalog.md` (exit 2 lists the rows still served by a provider;
allowed while a product is being built, never at a release). The readiness document
(`data/derived/readiness.json`) is computed from this file; editing the catalog makes it stale until
`python data-pipeline/run.py readiness` runs again (`scripts/check_readiness.py` fails meanwhile).

Versions and history: a contract's version moves with its schema, by semver (a removed or renamed field, a narrowed
type or a new required field is major; a new optional field is minor; a description or example change is patch), and
every version has a row in the History section below, whose `kind` is the semver step from the contract's previous row
(the first row is `initial`). `docs/contracts/versions.lock.json` holds each schema's version and digest (line endings
normalised to LF); `python scripts/check_contract_versions.py` fails when a schema changed under the same version, when
a version went down, when the lock is not current with the catalog, or when a row has no History entry for its current
version. After a deliberate bump and its History row, run `python scripts/check_contract_versions.py --update` and
commit the lock with the schema and both sides in one pull request.

The lock alone is trusted by that offline check, so a schema change with the lock edited by hand passes it. CI therefore
also runs `python scripts/check_contract_versions.py --base <ref>` (the push's `before` SHA, or `origin/develop`, on a
checkout with `fetch-depth: 0`; a ref it cannot resolve fails, it never passes silently). Against the schemas and the
catalog at that ref it fails when a schema changed and its version is not above the ref's, when the version goes down,
when a change that is breaking by the mechanical floor did not take a major step, and when a contract that had a schema
at the ref has none now without a `major` History row that records the removal. A contract with no row at the ref is a
first release. The mechanical floor is a minimal JSON Schema diff: a removed property, definition or enum value, a
property newly required, a changed const, a narrowed type, an added or tightened bound, pattern or format,
`additionalProperties` turned false or constrained, an added constraint on `items`, `not` or `$ref`, a removed `anyOf` or
`oneOf` alternative, an added `allOf` member, and for the OpenAPI file a removed path, operation, response or component.
It is the floor and not the judgement: a reviewer still decides the semantic breaks it cannot see (a changed meaning, a
unit, a default value), and a pull request that changes a contract states its step in the review.

The `documents` column (template 0.09.000) says which committed files a row's schema governs, so that
`scripts/check_documents.py` names no document and a product takes it verbatim. A cell is `-` (a contract with no committed
document, for example one only exchanged at run time) or one or more globs relative to the repository root, separated by `, `:
Python `pathlib` glob semantics (`*` within one path segment, `**` for any depth, so use it only where a depth varies); a glob
starting with `!` excludes what the row's other globs match (`data/derived/manifests/*.json, !data/derived/manifests/index.json`);
on a row whose schema file is the OpenAPI document each glob is written `path#ComponentName` and the files validate against
that component. The globs under `data/` and `models/` apply twice, at the repository root and in the provider tree
`docs/contracts/fixtures/`. The row's `example` cell is validated too when it is a file under `docs/contracts/examples/`. The
guard fails on a file two rows govern, on a JSON file under `data/derived` or `models` that no row covers (it would pass
unvalidated), and on a path outside the repository; `check_contracts.py` checks the cells. A glob that matches nothing is not an
error (`check_artifacts.py` and `check_readiness.py` judge absence), except that a row whose missing-data behavior begins
`missing:` and whose cell is one fixed path (the index) reports that path when it is absent.

A product instantiated from the template replaces these rows with its own, keeps the columns, the states and the
checks.

## Contracts

| id | version | owner | schema file | example | documents | producer test | consumer test | missing-data behavior | provider | model io | swap test | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| case-index | 3.1.0 | data-pipeline/pipeline/core/manifest.py | docs/contracts/schemas/case-index.schema.json | docs/contracts/fixtures/data/derived/manifests/index.json | data/derived/manifests/index.json | tests/contracts/test_documents.py::test_index_validates | frontend/src/lib/contract.test.ts | missing: the site build stops at copy-data (no site without an inventory), the API answers 503 missing, readiness says missing. stale: engine_version older than VERSION; readiness says stale with both versions and the views show it | fixture:docs/contracts/fixtures/data/derived/manifests/index.json | - | frontend/src/lib/contract.test.ts, tests/contracts/test_documents.py::test_fixture_tree_validates | real |
| case-manifest | 5.0.0 | data-pipeline/pipeline/core/manifest.py | docs/contracts/schemas/case-manifest.schema.json | docs/contracts/fixtures/data/derived/manifests/C01.json | data/derived/manifests/*.json, !data/derived/manifests/index.json | tests/contracts/test_documents.py::test_manifests_validate | frontend/src/lib/contract.test.ts | partial: a manifest the index lists is absent; readiness lists its path, the case selector marks the case not available yet and the other cases work, the API answers 404 for it. stale: as case-index | fixture:docs/contracts/fixtures/data/derived/manifests/C01.json | - | frontend/src/lib/contract.test.ts, tests/contracts/test_documents.py::test_fixture_tree_validates | real |
| readiness | 2.0.1 | data-pipeline/pipeline/core/readiness.py | docs/contracts/schemas/readiness.schema.json | docs/contracts/fixtures/data/derived/readiness.json | data/derived/readiness.json | tests/contracts/test_readiness.py::test_committed_readiness_is_current | frontend/src/readiness/readiness.test.ts | missing: the site build stops at copy-data; if the document cannot be loaded at run time the views keep working and each says readiness unknown; the API answers 503 missing | fixture:docs/contracts/fixtures/data/derived/readiness.json | - | frontend/src/readiness/readiness.test.ts | real |
| api | 2.1.0 | app/ | docs/contracts/api.openapi.json | docs/contracts/examples/api-unavailable.json | docs/contracts/examples/api-unavailable.json#UnavailableBody | tests/contracts/test_api.py::test_responses_match_the_openapi_document | frontend/src/lib/api.contract.test.ts | missing: a document the route serves is absent, the API answers 503 with state missing and the reason (never an empty body); an unknown case or artifact is 404. The static readiness says missing for this row while the API lane is dormant; /api/readiness says available | fixture:docs/contracts/fixtures/data/derived | - | tests/contracts/test_api.py::test_swap_fixture_tree_and_bake | real |
| softqp-index | 1.1.0 | data-pipeline/pipeline/softqp_run.py | docs/contracts/schemas/softqp-index.schema.json | docs/contracts/fixtures/data/derived/softqp/index.json | data/derived/softqp/index.json | tests/test_softqp_contracts.py::test_producer_documents_and_provider_match_schema | frontend/src/lib/softqp.contract.test.ts | missing: no scientific inventory; the workbench shows unavailable and no result; development state is displayed until the release matrix is complete | fixture:docs/contracts/fixtures/data/derived/softqp | - | tests/test_softqp_contracts.py::test_producer_documents_and_provider_match_schema | real |
| softqp-case-result | 2.3.0 | data-pipeline/pipeline/softqp_run.py | docs/contracts/schemas/softqp-case-result.schema.json | docs/contracts/fixtures/data/derived/softqp/C01.json | data/derived/softqp/C*.json | tests/test_softqp_contracts.py::test_producer_documents_and_provider_match_schema | frontend/src/lib/softqp.contract.test.ts | missing: a declared document is absent; the workbench says unavailable and reports the path; a failed run is recorded with its reason, and incompatible semantics never become an empty successful result | fixture:docs/contracts/fixtures/data/derived/softqp | - | tests/test_softqp_contracts.py::test_producer_documents_and_provider_match_schema | real |
| softqp-case-spec | 1.0.0 | data-pipeline/pipeline/io/contract.py | docs/contracts/schemas/softqp-case-spec.schema.json | docs/contracts/examples/softqp-case-spec.json | - | tests/test_softqp_requests.py | frontend/src/lib/softqp.local.test.ts | missing: local execution is unavailable until a complete matching request and validated export exist; replay remains available | fixture:docs/contracts/examples/softqp-case-spec.json | - | tests/test_softqp_requests.py, frontend/src/lib/softqp.local.test.ts | real |
| softqp-run-request | 1.1.0 | data-pipeline/pipeline/softqp_requests.py | docs/contracts/schemas/softqp-run-request.schema.json | docs/contracts/examples/softqp-run-request.json | - | tests/test_softqp_requests.py | frontend/src/lib/softqp.local.test.ts | missing: local execution is unavailable until a complete matching request and validated export exist; replay remains available | fixture:docs/contracts/examples/softqp-run-request.json | - | tests/test_softqp_requests.py, frontend/src/lib/softqp.local.test.ts | real |
| softqp-local-export | 1.1.0 | data-pipeline/pipeline/softqp_requests.py | docs/contracts/schemas/softqp-local-export.schema.json | docs/contracts/examples/softqp-local-export.json | docs/contracts/examples/softqp-local*-export.json | tests/test_softqp_requests.py | frontend/src/lib/softqp.local.test.ts | missing: local execution is unavailable until a complete matching request and validated export exist; replay remains available | fixture:docs/contracts/examples/softqp-local-export.json | - | tests/test_softqp_requests.py, frontend/src/lib/softqp.local.test.ts | real |
| softqp-stream | 1.0.0 | data-pipeline/pipeline/experiment_export.py | docs/contracts/schemas/softqp-stream.schema.json | docs/contracts/fixtures/data/derived/experiments/stream.json | data/derived/experiments/stream.json | tests/test_experiment_export.py | frontend/src/lib/experiments.contract.test.ts | missing: experiment evidence is unavailable; show the missing path and retain the other case records | fixture:docs/contracts/fixtures/data/derived/experiments | - | tests/test_experiment_export.py, frontend/src/lib/experiments.contract.test.ts | real |
| softqp-campaign | 1.0.0 | data-pipeline/pipeline/experiment_export.py | docs/contracts/schemas/softqp-campaign.schema.json | docs/contracts/fixtures/data/derived/experiments/campaign.json | data/derived/experiments/campaign.json | tests/test_experiment_export.py | frontend/src/lib/experiments.contract.test.ts | missing: experiment evidence is unavailable; show the missing path and retain the other case records | fixture:docs/contracts/fixtures/data/derived/experiments | - | tests/test_experiment_export.py, frontend/src/lib/experiments.contract.test.ts | real |
| softqp-datasets | 1.0.0 | data-pipeline/pipeline/experiment_export.py | docs/contracts/schemas/softqp-datasets.schema.json | docs/contracts/fixtures/data/derived/experiments/datasets.json | data/derived/experiments/datasets.json | tests/test_experiment_export.py | tests/test_experiment_export.py | missing: experiment evidence is unavailable; show the missing path and retain the other case records | fixture:docs/contracts/fixtures/data/derived/experiments | - | tests/test_experiment_export.py, tests/test_experiment_export.py | real |
| softqp-trial | 1.0.0 | data-pipeline/pipeline/experiment_export.py | docs/contracts/schemas/softqp-trial.schema.json | - | - | tests/test_experiment_export.py | tests/test_experiment_export.py | missing: experiment evidence is unavailable; show the missing path and retain the other case records | fixture:docs/contracts/fixtures/data/derived/experiments | - | tests/test_experiment_export.py, tests/test_experiment_export.py | real |
| softqp-experiment-index | 1.0.0 | data-pipeline/pipeline/experiment_export.py | docs/contracts/schemas/softqp-experiment-index.schema.json | docs/contracts/fixtures/data/derived/experiments/index.json | data/derived/experiments/index.json | tests/test_experiment_export.py | frontend/src/lib/experiments.contract.test.ts | missing: experiment evidence is unavailable; show the missing path and retain the other case records | fixture:docs/contracts/fixtures/data/derived/experiments | - | tests/test_experiment_export.py, frontend/src/lib/experiments.contract.test.ts | real |
| softqp-coupled-batch | 1.0.0 | data-pipeline/pipeline/coupled_contract.py | docs/contracts/schemas/softqp-coupled-batch.schema.json | docs/contracts/examples/softqp-coupled-batch.json | docs/contracts/examples/softqp-coupled-batch.json | tests/coupled/test_coupled_contract.py | tests/coupled/test_coupled_contract.py | missing: this offline research exchange has no declared validated replay adapter in the app; schema examples and archived evidence do not establish deployed data availability | fixture:docs/contracts/examples/softqp-coupled-batch.json | - | tests/coupled/test_coupled_contract.py | real |
| softqp-coupled-observation | 1.0.0 | data-pipeline/pipeline/coupled_campaign.py | docs/contracts/schemas/softqp-coupled-observation.schema.json | docs/contracts/examples/softqp-coupled-observation.json | docs/contracts/examples/softqp-coupled-observation.json | tests/coupled/test_coupled_export.py::test_complete_downstream_replay_and_exact_csv | tests/coupled/test_coupled_export.py::test_adversarial_replay_rejects_tampering_even_when_outer_checksums_are_recomputed | missing: this offline research exchange has no declared validated replay adapter in the app; schema examples and archived evidence do not establish deployed data availability | fixture:docs/contracts/examples/softqp-coupled-observation.json | - | tests/coupled/test_coupled_export.py::test_complete_downstream_replay_and_exact_csv, tests/coupled/test_coupled_export.py::test_adversarial_replay_rejects_tampering_even_when_outer_checksums_are_recomputed | real |
| softqp-coupled-campaign | 1.0.0 | data-pipeline/pipeline/coupled_campaign.py | docs/contracts/schemas/softqp-coupled-campaign.schema.json | docs/contracts/examples/softqp-coupled-campaign.json | docs/contracts/examples/softqp-coupled-campaign.json | tests/coupled/test_coupled_export.py::test_complete_downstream_replay_and_exact_csv | tests/coupled/test_coupled_export.py::test_adversarial_replay_rejects_tampering_even_when_outer_checksums_are_recomputed | missing: this offline research exchange has no declared validated replay adapter in the app; schema examples and archived evidence do not establish deployed data availability | fixture:docs/contracts/examples/softqp-coupled-campaign.json | - | tests/coupled/test_coupled_export.py::test_complete_downstream_replay_and_exact_csv, tests/coupled/test_coupled_export.py::test_adversarial_replay_rejects_tampering_even_when_outer_checksums_are_recomputed | real |
| softqp-coupled-lesson | 1.0.0 | data-pipeline/pipeline/coupled_lesson_worker.py | docs/contracts/schemas/softqp-coupled-lesson.schema.json | docs/contracts/examples/softqp-coupled-lesson.json | docs/contracts/examples/softqp-coupled-lesson.json | tests/test_coupled_lessons.py::test_adversarial_real_methods_share_the_original_objective | tests/test_coupled_lessons.py::test_adversarial_real_methods_share_the_original_objective | missing: the separately configured offline teaching runtime has no browser replay adapter; a generated shape example does not establish deployed solver execution | fixture:docs/contracts/examples/softqp-coupled-lesson.json | - | tests/test_coupled_lessons.py::test_adversarial_real_methods_share_the_original_objective, tests/test_coupled_lessons.py::test_adversarial_external_lesson_boundary | real |

## Missing-data states

The native pipeline computes readiness from this catalog, product version and scientific deployment inventory. It uses the shared six-state vocabulary. There is no trained model in this product, so no training-state producer is declared. Runtime contracts can be available without a user having submitted a local request; this describes implemented capability, not execution of every possible input.

| state | condition | provenance | surface behavior | reason en | reason es |
|---|---|---|---|---|---|
| provider | status active | declared provider kind | Show a visible provider label | Served by its declared provider; the producer is incomplete. | Servido por su proveedor declarado; el productor estÃƒÂ¡ incompleto. |
| missing | dormant API | null | Static reader remains available | The API lane is dormant; the browser reads static artifacts. | La API estÃƒÂ¡ inactiva; el navegador lee artefactos estÃƒÂ¡ticos. |
| missing | inventory absent or unreadable | null | Show unavailable, with its reason | The scientific inventory has not been baked. | El inventario cientÃƒÂ­fico no ha sido generado. |
| partial | declared manifests or results absent | real | Keep other cases and list missing paths | Declared scientific files are absent. | Faltan archivos cientÃƒÂ­ficos declarados. |
| stale | deployment inventory version differs | real | Show a stale note | Baked by {engine_version}; the product is {version}. | Generado por {engine_version}; el producto es {version}. |
| available | applicable checks above pass | real | Render verified records | none | ninguna |

Schema and byte integrity are separate checks. Available readiness never substitutes for JSON Schema, native original-space acceptance, checksums, full UI review, scientific novelty review or release acceptance. A provider inventory is isolated to C01 and uses the actual loader and checksum path.

## Provider inventory

`docs/contracts/fixtures/data/derived` carries a C01-only scientific result, inventory, deployment manifest and readiness document. `scripts/update_softqp_fixtures.py` builds it from the canonical checked record without rerunning a solver. `VITE_SOFTQP_SOURCE=fixture` selects the labelled scientific source in the browser; `CAOS_DATA_ROOT` selects deployment files at build time and `DATA_DIR` selects the dormant read-only API source.

## History

One row per version of every contract, newest last within a contract. `kind` is initial, major, minor or patch, per
the rules above. The rows of 0.04.000 record the versions that release shipped; an earlier shape of a contract is
not reconstructed.

| contract | version | date | change | kind |
|---|---|---|---|---|
| params-record | 1.0.0 | 2026-10-11 | the ingestion record: case id, retired example parameters with the bounds of contract 1 | initial |
| case-index | 2.0.0 | 2026-10-11 | the index of cases with bilingual titles, categories and the default case (retired inherited index) | initial |
| case-manifest | 4.0.0 | 2026-10-11 | the per-case manifest with lane verdict, metrics and the model behind them (retired inherited manifest) | initial |
| trace | 1.0.0 | 2026-10-11 | the per-case trace, at most 200 points, with a summary (retired inherited trace) | initial |
| surrogate-model | 1.0.0 | 2026-10-11 | the slot r0 to peak infected fraction, with the analytic baseline behind it | initial |
| readiness | 1.0.0 | 2026-10-11 | what is real in a build, row by row, in one of six declared states | initial |
| api | 1.0.0 | 2026-10-11 | the dormant read-only API, GET only, 503 with the declared state when a document is absent | initial |
| softqp-index | 1.0.0 | 2026-10-31 | Development scientific inventory and SHA-256 hashes | initial |
| softqp-case-result | 1.0.0 | 2026-10-31 | Original-space results with explicit failure and incompatibility | initial |
| api | 1.1.0 | 2026-10-31 | Add scientific result and index schema components for generated consumers | minor |
| softqp-case-result | 2.0.0 | 2026-10-31 | Require physical units and hard/soft policy per original row; version the result identifier | major |
| softqp-case-result | 2.1.0 | 2026-10-31 | Add DAQP method and optional actual backend settings | minor |
| softqp-case-result | 2.2.0 | 2026-10-31 | Add optional sparse original problem for local cost editing and independent checks | minor |
| softqp-case-spec | 1.0.0 | 2026-10-31 | Sparse original-space problem serialization with null absent bounds | initial |
| softqp-run-request | 1.0.0 | 2026-10-31 | Bounded cost edits tied to one checksummed committed case | initial |
| softqp-local-export | 1.0.0 | 2026-10-31 | Local execution envelope retaining request and complete result | initial |
| api | 1.2.0 | 2026-10-31 | Add specification, request and local export components | minor |
| params-record | 2.0.0 | 2026-10-31 | Remove inherited domain parameters; sparse scientific specification replaces them | major |
| trace | 2.0.0 | 2026-10-31 | Remove inherited trajectory; original-space scientific result replaces it | major |
| surrogate-model | 2.0.0 | 2026-10-31 | Remove unrelated trained surrogate; all implemented solvers are deterministic | major |
| case-index | 3.0.0 | 2026-10-31 | Replace inherited index with declared scientific deployment inventory | major |
| case-manifest | 5.0.0 | 2026-10-31 | Replace inherited simulation fields with scientific result metadata and replay gate | major |
| readiness | 2.0.0 | 2026-10-31 | Scientific inventory readiness without example model or training dependencies | major |
| api | 2.0.0 | 2026-10-31 | Replace example response bodies with scientific inventory, manifest and result types | major |
| readiness | 2.0.1 | 2026-10-31 | Explicit redundant array types in conditional branches for strict runtime validation | patch |
| api | 2.0.1 | 2026-10-31 | Replace inherited example identifiers in dormant endpoint examples | patch |
| softqp-index | 1.1.0 | 2026-10-31 | Add optional engine source and loaded binary provenance | minor |
| softqp-case-result | 2.3.0 | 2026-10-31 | Admit fixed-parameter FlexQP and published ElastiQP comparison cells | minor |
| softqp-run-request | 1.1.0 | 2026-10-31 | Allow a zero quadratic factor as an explicit pure L1 variant | minor |
| softqp-local-export | 1.1.0 | 2026-10-31 | Admit pure L1 reference results and optional numerical environment provenance | minor |
| case-index | 3.1.0 | 2026-10-31 | Allow declared raw CSV and JSONL experiment evidence alongside JSON documents | minor |
| api | 2.1.0 | 2026-10-31 | Add stream, campaign and experimental inventory schema components for typed readers | minor |
| softqp-stream | 1.0.0 | 2026-10-31 | Initial preregistered experimental stream boundary | initial |
| softqp-campaign | 1.0.0 | 2026-10-31 | Initial preregistered experimental campaign boundary | initial |
| softqp-datasets | 1.0.0 | 2026-10-31 | Initial preregistered experimental datasets boundary | initial |
| softqp-trial | 1.0.0 | 2026-10-31 | Initial preregistered experimental trial boundary | initial |
| softqp-experiment-index | 1.0.0 | 2026-10-31 | Initial preregistered experimental experiment-index boundary | initial |
| softqp-coupled-batch | 1.0.0 | 2026-11-01 | Original-space disjoint groups, sparse CSC matrices,32-forecast vector inputs and explicit physical unit maps; prospective study remains independently gated | initial |
| softqp-coupled-observation | 1.0.0 | 2026-11-01 | Full oracle/method frame evidence with failure and candidate-status semantics; prospective study remains independently gated | initial |
| softqp-coupled-campaign | 1.0.0 | 2026-11-01 | Checksummed complete inventory, raw journal, exact CSV and independent replay/primary analysis; prospective study remains independently gated | initial |
| softqp-coupled-lesson | 1.0.0 | 2026-11-02 | Actual separate-runtime directional worked-example exchange with input/source/SDK identity and explicit method states | initial |
