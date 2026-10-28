# Contract catalog: DinHot

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
| params-record | 1.0.0 | data-pipeline/pipeline/io/contract.py | docs/contracts/schemas/params-record.schema.json | docs/contracts/examples/params-record.json | - | tests/contracts/test_params_record.py::test_accepted_records_match_the_schema, tests/contracts/test_params_record.py::test_c11_is_rejected_with_the_field_bounds | tests/contracts/test_params_record.py::test_adversarial_schema_valid_records_are_accepted, tests/contracts/test_params_record.py::test_adversarial_rejections_carry_their_reason, tests/test_contract.py | partial: a rejected record is dropped with its reason and the bake goes on with the accepted records; readiness lists the rejected case ids (C11 is rejected by design and the index records it as refused with the reason). missing: no source document data/examples/cases.json; readiness says missing and the bake uses the registry's cases | fixture:docs/contracts/fixtures/data/examples/cases.json | - | tests/contracts/test_params_record.py::test_swap_fixture_and_example_sources | real |
| case-index | 1.0.0 | data-pipeline/pipeline/core/manifest.py | docs/contracts/schemas/case-index.schema.json | docs/contracts/fixtures/data/derived/manifests/index.json | data/derived/manifests/index.json | tests/contracts/test_documents.py::test_index_validates, tests/contracts/test_documents.py::test_refused_case_has_no_manifest | frontend/src/lib/contract.test.ts | missing: the site build stops at copy-data (no site without an inventory), the API answers 503 missing, readiness says missing. stale: engine_version older than VERSION; readiness says stale with both versions and the views show it. A refused case has no manifest: the workbench shows its reason | fixture:docs/contracts/fixtures/data/derived/manifests/index.json | - | frontend/src/lib/contract.test.ts, tests/contracts/test_documents.py::test_fixture_tree_validates | real |
| case-manifest | 1.0.0 | data-pipeline/pipeline/core/manifest.py | docs/contracts/schemas/case-manifest.schema.json | docs/contracts/fixtures/data/derived/manifests/FX01_fixture.json | data/derived/manifests/*.json, !data/derived/manifests/index.json | tests/contracts/test_documents.py::test_manifests_validate | frontend/src/lib/contract.test.ts | partial: a manifest the index lists is absent; readiness lists its path, the case selector marks the case not available yet and the other cases work, the API answers 404 for it. stale: as case-index | fixture:docs/contracts/fixtures/data/derived/manifests/FX01_fixture.json | - | frontend/src/lib/contract.test.ts, tests/contracts/test_documents.py::test_fixture_tree_validates | real |
| trace | 1.0.0 | data-pipeline/pipeline/core/trace.py | docs/contracts/schemas/trace.schema.json | docs/contracts/fixtures/data/derived/FX01_fixture/trace.json | data/derived/*/trace.json | tests/contracts/test_documents.py::test_traces_validate, tests/contracts/test_documents.py::test_trace_base64_fields_have_their_sizes | frontend/src/lib/contract.test.ts | partial: an artifact a manifest names is absent; readiness lists its path and that case's replay views show not available yet with the reason (the live lane still runs from the manifest's params), the API answers 404 for it. stale: as case-index | fixture:docs/contracts/fixtures/data/derived/FX01_fixture/trace.json | - | frontend/src/lib/contract.test.ts, tests/contracts/test_documents.py::test_fixture_tree_validates | real |
| benchmark-results | 1.0.0 | data-pipeline/pipeline/stages/benchmark.py | docs/contracts/schemas/benchmark-results.schema.json | docs/contracts/fixtures/data/derived/benchmark/results.json | data/derived/benchmark/results.json | tests/contracts/test_documents.py::test_benchmark_validates, tests/contracts/test_documents.py::test_skipped_cells_are_absent_from_rows | frontend/src/lib/contract.test.ts | missing: the document is absent; readiness says missing and the Benchmark views say not available yet with the reason, never a number from an older bake. partial: a cell not run is absent from rows and listed in skipped; readiness lists the cells (method/geometry) and the views mark each not run. stale: engine_version older than VERSION; readiness says stale | fixture:docs/contracts/fixtures/data/derived/benchmark/results.json | - | tests/contracts/test_documents.py::test_fixture_tree_validates | real |
| cgh-net | 1.0.0 | data-pipeline/pipeline/stages/train.py | docs/contracts/schemas/model-card.schema.json | docs/contracts/examples/cgh-net.json | models/cgh-net.json, models/cgh-net.onnx | tests/contracts/test_documents.py::test_model_cards_validate | tests/contracts/test_documents.py::test_onnx_graphs_match_their_cards, frontend/src/lib/contract.test.ts | training: no valid released model (the card or the graph is absent, fails its schema or its sha256), the baseline answers (provenance baseline), readiness says training; or the marker models/training/cgh-net exists, the released model answers (provenance real) while a newer one trains. The views label the result with the model that answered | baseline:data-pipeline/pipeline/model/baseline.py | in: target float32 [1, 1, 128, 128] (the target amplitude on the focal crop, normalised to unit energy); out: phase float32 [1, 1, 128, 128] in radians; baseline: GS (M04) at 30 iterations | tests/contracts/test_documents.py::test_adversarial_swap_gs_baseline_and_cgh_net | active |
| warmstart-model | 1.0.0 | data-pipeline/pipeline/stages/train.py | docs/contracts/schemas/model-card.schema.json | docs/contracts/examples/warmstart-model.json | models/warmstart.json, models/warmstart.onnx | tests/contracts/test_documents.py::test_model_cards_validate | tests/contracts/test_documents.py::test_onnx_graphs_match_their_cards, frontend/src/lib/contract.test.ts | training: as cgh-net, with the marker models/training/warmstart-model; the baseline is the random trap phases of the portable RNG (the M02 start) | baseline:data-pipeline/pipeline/model/baseline.py | in: traps float32 [1, 1024, 4] (x and y in focal bins over the half field, z in Rayleigh ranges, weight; padded) and mask float32 [1, 1024]; out: trap_phase float32 [1, 1024] in radians; baseline: random trap phases from the portable RNG | tests/contracts/test_documents.py::test_adversarial_swap_random_start_and_warmstart_model | active |
| model-metrics | 1.0.0 | data-pipeline/pipeline/stages/evaluate.py | docs/contracts/schemas/model-metrics.schema.json | docs/contracts/fixtures/data/derived/models/metrics.json | data/derived/models/metrics.json | tests/contracts/test_documents.py::test_model_metrics_validate | frontend/src/lib/contract.test.ts | missing: the document is absent; readiness says missing and the Benchmark model views say not available yet with the reason, never a number from an older bake. stale: engine_version older than VERSION; readiness says stale. A slot with no released model has no entry and its views say so | fixture:docs/contracts/fixtures/data/derived/models/metrics.json | - | tests/contracts/test_documents.py::test_fixture_tree_validates | active |
| engine-reference | 1.0.0 | data-pipeline/pipeline/stages/engine_reference.py | docs/contracts/schemas/engine-reference.schema.json | docs/contracts/examples/engine-reference.json | tests/fixtures/engine/*.json | tests/contracts/test_documents.py::test_engine_reference_validates | frontend/src/lib/contract.test.ts | missing: tests/fixtures/engine/ holds no reference file; readiness says missing and the TypeScript parity tests fail naming the absent file (a test input, never a run-time document) | fixture:docs/contracts/examples/engine-reference.json | - | tests/contracts/test_documents.py::test_engine_reference_example_validates | active |
| readiness | 1.0.0 | data-pipeline/pipeline/core/readiness.py | docs/contracts/schemas/readiness.schema.json | docs/contracts/fixtures/data/derived/readiness.json | data/derived/readiness.json | tests/contracts/test_readiness.py::test_committed_readiness_is_current | frontend/src/readiness/readiness.test.ts | missing: the site build stops at copy-data; if the document cannot be loaded at run time the views keep working and each says readiness unknown; the API answers 503 missing | fixture:docs/contracts/fixtures/data/derived/readiness.json | - | frontend/src/readiness/readiness.test.ts | real |
| api | 1.0.0 | app/ | docs/contracts/api.openapi.json | docs/contracts/examples/api-unavailable.json | docs/contracts/examples/api-unavailable.json#UnavailableBody | tests/contracts/test_api.py::test_responses_match_the_openapi_document | frontend/src/lib/api.contract.test.ts | missing: a document the route serves is absent, the API answers 503 with state missing and the reason (never an empty body); an unknown case or artifact is 404. The static readiness says missing for this row while the API lane is dormant; /api/readiness says available | fixture:docs/contracts/fixtures/data/derived | - | tests/contracts/test_api.py::test_swap_fixture_tree_and_bake | real |

## Missing-data states

One vocabulary for every row (ADR-0080 decision 3). `data-pipeline/pipeline/core/readiness.py` computes each row's
state from this catalog and the repository; the frontend and the API show it. Rules, applied in this order, first
match wins:

| Row kind | Condition | state | provenance | reason en | reason es |
|---|---|---|---|---|---|
| any | the catalog `status` is `active` | `provider` | the provider kind | Served by its provider ({provider}); the real producer is not built yet. | Lo sirve su proveedor ({provider}); el productor real aún no está construido. |
| case-index, case-manifest, trace | `data/derived/manifests/index.json` is absent | `missing` | null | The pipeline has not baked this build. | El pipeline no ha generado esta versión. |
| case-manifest | a manifest the index lists as baked is absent | `partial` | `real` | {n} of {total} manifests are absent. | Faltan {n} de {total} manifiestos. |
| trace | an artifact a present manifest names is absent | `partial` | `real` | {n} of {total} artifacts are absent. | Faltan {n} de {total} artefactos. |
| case-index, case-manifest, trace, benchmark-results, model-metrics | the document's `engine_version` (the index's, for a manifest and a trace) differs from `VERSION` | `stale` | `real` | Baked by {engine_version}; the product is {version}. | Generado por {engine_version}; el producto es {version}. |
| params-record | `data/examples/cases.json` is absent | `missing` | null | No source document; the bake uses the registry's cases. | No hay documento de origen; la generación usa los casos del registro. |
| params-record | contract 1 rejects some records | `partial` | `real` | {n} of {total} records rejected by contract 1. | {n} de {total} registros rechazados por el contrato 1. |
| benchmark-results | `data/derived/benchmark/results.json` is absent | `missing` | null | The benchmark has not run for this build. | El benchmark no se ha ejecutado para esta versión. |
| benchmark-results | the document's `skipped` is not empty | `partial` | `real` | {n} of {total} benchmark cells were not run. | {n} de {total} celdas del benchmark no se ejecutaron. |
| model-metrics | `data/derived/models/metrics.json` is absent | `missing` | null | The model metrics have not been computed for this build. | Las métricas de los modelos no se han calculado para esta versión. |
| cgh-net, warmstart-model | the slot's card or graph (`models/cgh-net.*`, `models/warmstart.*`) is absent or fails its schema or its sha256 | `training` | `baseline` | No released model; the slot's baseline answers (GS for cgh-net, random trap phases for warmstart-model). | No hay un modelo publicado; responde la línea base del espacio (GS para cgh-net, fases aleatorias de las trampas para warmstart-model). |
| cgh-net, warmstart-model | a manifest records that the baseline produced its metrics (`models` of the manifest) | `training` | `baseline` | The bake's metrics come from the baseline; bake again to use the released model. | Las métricas de la generación vienen de la línea base; genere de nuevo para usar el modelo publicado. |
| cgh-net, warmstart-model | the marker file `models/training/<slot>` exists | `training` | `real` | The released model answers; a newer one is training. | Responde el modelo publicado; uno más nuevo está en entrenamiento. |
| engine-reference | no JSON file under `tests/fixtures/engine/` | `missing` | null | The engine reference values are absent; the parity tests cannot run. | Faltan los valores de referencia del motor; las pruebas de paridad no pueden ejecutarse. |
| api | always, in the static document | `missing` | null | The API lane is dormant; the site reads the committed documents. | La API está inactiva; el sitio lee los documentos versionados. |
| any | otherwise | `available` | `real` | null | null |

The `status` column holds `real` or `active` only, in lower case; any other value fails the readiness computation (and so
`scripts/check_readiness.py`), because a status the rules do not know would be published as real. `{provider}` is
the row's provider cell (`kind:path`); `{n}`, `{total}`, `{engine_version}` and `{version}` are
filled from the repository. `missing` is a list of strings, non-empty exactly when the state is `partial`: the
absent paths relative to `data/derived/` (manifests, artifacts), the rejected case ids (params-record) or the skipped
cells as `method/geometry` (benchmark-results), sorted.
`/api/readiness` returns the committed document with the `api` row set to status `real`, state `available`, provenance `real`, reason
null. What each surface does:

| state | the frontend shows | the API answers |
|---|---|---|
| `available` | the result | 200 |
| `partial` | the result for what exists; each absent case, artifact or benchmark cell says not available yet | 200 for what exists, 404 for the absent paths |
| `stale` | the result and a note with the version that baked it | 200 |
| `provider` | the result and a note naming the provider kind | 200 |
| `training` | the result and a note naming the model that answered, and that a newer one is training (or that none is released) | 200 |
| `missing` | an explicit not available yet with the reason, never an empty chart | 503 with `{"detail": {"state": "missing", "reason": {...}}}` |

A `partial` bake builds: `frontend/scripts/copy-data.mjs` and `scripts/check_artifacts.py` accept an absent
manifest or artifact only when the readiness document lists it in the `missing` of a `partial` row (and the
readiness is current, `scripts/check_readiness.py`); any other absent file stops them.

## Providers

- `docs/contracts/fixtures/data/derived/`: a provider tree in the layout of `data/derived/`. It holds one small case,
  `FX01_fixture` (three traps at n_pix 64 on a 3 x 3 focal crop, three methods: M02, M04 and M06), its manifest and its
  trace (7365 bytes, far under the 256 KiB gate); the index (`manifests/index.json`), which lists one refused case
  (`C11_fixture`, no manifest, with its reason) to exercise that path; a benchmark-results document with two rows and one
  skipped cell (`benchmark/results.json`); a model-metrics document (`models/metrics.json`); and a readiness document that
  says `provider` for every row but `api`, which is dormant and so `missing`. The frontend builds on it with
  `CAOS_DATA_ROOT=docs/contracts/fixtures/data/derived` (a walking skeleton before any bake), the API serves it with
  `DATA_DIR=docs/contracts/fixtures/data/derived`, and the contract tests run against it and against `data/derived/` with the
  same assertions (the swap tests).
- `docs/contracts/fixtures/data/examples/cases.json`: a two-record source document for contract 1 (`C01_fixture`, accepted, and
  `C11_fixture`, whose trap lies outside the unaliased field of view and is rejected with the field's bounds).
- `data-pipeline/pipeline/model/baseline.py`: the baselines of the two model slots behind the same contracts, GS (M04) at
  30 iterations for cgh-net and the random trap phases of the portable RNG (the M02 start) for warmstart-model. They need no
  released model.
- `docs/contracts/examples/engine-reference.json`: the one reference document of the engine-reference row until the engine
  writes `tests/fixtures/engine/*.json`.

A provider is scaffolding: labelled on every surface by the readiness document, never counted as done for the unit
that owes the real producer.

## History

One row per version of every contract, newest last within a contract. `kind` is initial, major, minor or patch, per
the rules above. The rows of 0.04.000 record the versions that release shipped; an earlier shape of a contract is
not reconstructed.

| contract | version | date | change | kind |
|---|---|---|---|---|
| params-record | 1.0.0 | 2026-10-28 | the case record: optical setup, device, target (traps or shaped), aberration, methods, budget, seed, feedback, dynamics, rearrangement and expected ranges (`dinhot.params/v1` fields) | initial |
| case-index | 1.0.0 | 2026-10-28 | the index of the twelve cases with bilingual titles and categories, the default case and the baked or refused status with the reason (`dinhot.index/v1`) | initial |
| case-manifest | 1.0.0 | 2026-10-28 | the per-case manifest with lane verdict, the verdict per method, the models behind it and the published anchor (`dinhot.manifest/v1`) | initial |
| trace | 1.0.0 | 2026-10-28 | the per-case trace: metric series per method, the reference method's phase mask and focal map, axial cut, feedback, dynamics and rearrangement, at most 256 KiB (`dinhot.trace/v1`) | initial |
| benchmark-results | 1.0.0 | 2026-10-28 | the benchmark table method by geometry by budget with medians and inter-quartile ranges, the Pareto fronts and the skipped cells (`dinhot.benchmark/v1`) | initial |
| cgh-net | 1.0.0 | 2026-10-28 | the model slot target amplitude to phase mask, with GS (M04) behind it as the baseline (`dinhot.model-card/v1`) | initial |
| warmstart-model | 1.0.0 | 2026-10-28 | the model slot trap list to trap phases, with the random trap phases (M02 start) behind it as the baseline (`dinhot.model-card/v1`) | initial |
| model-metrics | 1.0.0 | 2026-10-28 | the held-out metrics of the two model slots against their baselines (`dinhot.model-metrics/v1`) | initial |
| engine-reference | 1.0.0 | 2026-10-28 | the reference values of the Python engine read by the TypeScript parity tests (`dinhot.engine-ref/v1`) | initial |
| readiness | 1.0.0 | 2026-10-28 | what is real in a build, row by row, in one of six declared states, with the training rules for each model slot | initial |
| api | 1.0.0 | 2026-10-28 | the dormant read-only API, GET only: index, manifest, artifact, benchmark results, model metrics and readiness; 503 with the declared state when a document is absent | initial |
