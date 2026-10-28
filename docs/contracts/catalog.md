# Contract catalog: the template's example product

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
| params-record | 1.0.0 | data-pipeline/pipeline/io/contract.py | docs/contracts/schemas/params-record.schema.json | docs/contracts/examples/params-record.json | - | tests/contracts/test_params_record.py::test_accepted_records_match_the_schema | tests/contracts/test_params_record.py::test_adversarial_schema_valid_records_are_accepted, tests/test_contract.py | partial: a rejected row is dropped with its reason and the bake goes on with the accepted rows; readiness lists the rejected case ids. missing: no source table; readiness says missing and the bake uses the registry's cases | fixture:docs/contracts/fixtures/data/examples/params.csv | - | tests/contracts/test_params_record.py::test_swap_fixture_and_example_sources | real |
| case-index | 2.0.0 | data-pipeline/pipeline/core/manifest.py | docs/contracts/schemas/case-index.schema.json | docs/contracts/fixtures/data/derived/manifests/index.json | data/derived/manifests/index.json | tests/contracts/test_documents.py::test_index_validates | frontend/src/lib/contract.test.ts | missing: the site build stops at copy-data (no site without an inventory), the API answers 503 missing, readiness says missing. stale: engine_version older than VERSION; readiness says stale with both versions and the views show it | fixture:docs/contracts/fixtures/data/derived/manifests/index.json | - | frontend/src/lib/contract.test.ts, tests/contracts/test_documents.py::test_fixture_tree_validates | real |
| case-manifest | 4.0.0 | data-pipeline/pipeline/core/manifest.py | docs/contracts/schemas/case-manifest.schema.json | docs/contracts/fixtures/data/derived/manifests/FX01_fixture.json | data/derived/manifests/*.json, !data/derived/manifests/index.json | tests/contracts/test_documents.py::test_manifests_validate | frontend/src/lib/contract.test.ts | partial: a manifest the index lists is absent; readiness lists its path, the case selector marks the case not available yet and the other cases work, the API answers 404 for it. stale: as case-index | fixture:docs/contracts/fixtures/data/derived/manifests/FX01_fixture.json | - | frontend/src/lib/contract.test.ts, tests/contracts/test_documents.py::test_fixture_tree_validates | real |
| trace | 1.0.0 | data-pipeline/pipeline/core/trace.py | docs/contracts/schemas/trace.schema.json | docs/contracts/fixtures/data/derived/FX01_fixture/trace.json | data/derived/*/trace.json | tests/contracts/test_documents.py::test_traces_validate | frontend/src/lib/contract.test.ts | partial: an artifact a manifest names is absent; readiness lists its path and that case's views show not available yet with the reason, the API answers 404 for it. stale: as case-index | fixture:docs/contracts/fixtures/data/derived/FX01_fixture/trace.json | - | frontend/src/lib/contract.test.ts, tests/contracts/test_documents.py::test_fixture_tree_validates | real |
| surrogate-model | 1.0.0 | data-pipeline/pipeline/stages/train.py | docs/contracts/schemas/surrogate-model.schema.json | docs/contracts/examples/surrogate-model.json | models/surrogate.json | tests/contracts/test_surrogate.py::test_trained_bundle_validates | tests/contracts/test_surrogate.py::test_evaluate_reads_any_valid_bundle | training: no valid released bundle, the baseline answers (provenance baseline); or the marker models/training/surrogate-model exists, the released bundle answers (provenance real) while a newer one trains. The Benchmark page labels the surrogate metrics with the model that answered | baseline:data-pipeline/pipeline/model/baseline.py | in: r0 = beta / gamma (number, dimensionless, > 0); out: peak_frac = peak_I / N (number in [0, 1]); trained on the cases' r0 (0.72 to 6) and held monotone to r0 = 10, beyond which the 4-term fit turns down (the baseline holds to 20) | tests/contracts/test_surrogate.py::test_adversarial_swap_baseline_and_trained | real |
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
| case-manifest | a manifest the index lists is absent | `partial` | `real` | {n} of {total} manifests are absent. | Faltan {n} de {total} manifiestos. |
| trace | an artifact a present manifest names is absent | `partial` | `real` | {n} of {total} artifacts are absent. | Faltan {n} de {total} artefactos. |
| case-index, case-manifest, trace | the index `engine_version` differs from `VERSION` | `stale` | `real` | Baked by {engine_version}; the product is {version}. | Generado por {engine_version}; el producto es {version}. |
| params-record | `data/examples/params.csv` is absent | `missing` | null | No source table; the bake uses the registry's cases. | No hay tabla de origen; la generación usa los casos del registro. |
| params-record | contract 1 rejects some rows | `partial` | `real` | {n} of {total} rows rejected by contract 1. | {n} de {total} filas rechazadas por el contrato 1. |
| surrogate-model | `models/surrogate.json` is absent or fails its schema | `training` | `baseline` | No released surrogate; the analytic baseline answers. | No hay un sustituto publicado; responde la línea base analítica. |
| surrogate-model | a manifest records that the baseline produced its metrics (`models` of the manifest) | `training` | `baseline` | The bake's metrics come from the analytic baseline; bake again to use the released surrogate. | Las métricas de la generación vienen de la línea base analítica; genere de nuevo para usar el sustituto publicado. |
| surrogate-model | the marker file `models/training/surrogate-model` exists | `training` | `real` | The released surrogate answers; a newer one is training. | Responde el sustituto publicado; uno más nuevo está en entrenamiento. |
| api | always, in the static document | `missing` | null | The API lane is dormant; the site reads the committed documents. | La API está inactiva; el sitio lee los documentos versionados. |
| any | otherwise | `available` | `real` | null | null |

The `status` column holds `real` or `active` only, in lower case; any other value fails the readiness computation (and so
`scripts/check_readiness.py`), because a status the rules do not know would be published as real. `{provider}` is
the row's provider cell (`kind:path`); `{n}`, `{total}`, `{engine_version}` and `{version}` are
filled from the repository. `missing` is a list of strings, non-empty exactly when the state is `partial`: the
absent paths relative to `data/derived/` (manifests, artifacts) or the rejected case ids (params-record), sorted.
`/api/readiness` returns the committed document with the `api` row set to status `real`, state `available`, provenance `real`, reason
null. What each surface does:

| state | the frontend shows | the API answers |
|---|---|---|
| `available` | the result | 200 |
| `partial` | the result for what exists; each absent case or artifact says not available yet | 200 for what exists, 404 for the absent paths |
| `stale` | the result and a note with the version that baked it | 200 |
| `provider` | the result and a note naming the provider kind | 200 |
| `training` | the result and a note naming the model that answered, and that a newer one is training (or that none is released) | 200 |
| `missing` | an explicit not available yet with the reason, never an empty chart | 503 with `{"detail": {"state": "missing", "reason": {...}}}` |

A `partial` bake builds: `frontend/scripts/copy-data.mjs` and `scripts/check_artifacts.py` accept an absent
manifest or artifact only when the readiness document lists it in the `missing` of a `partial` row (and the
readiness is current, `scripts/check_readiness.py`); any other absent file stops them.

## Providers

- `docs/contracts/fixtures/data/derived/`: a provider tree in the layout of `data/derived/` (one case,
  `FX01_fixture`, its manifest and trace, the index and a readiness document that says `provider` for every row but `api`, which is
dormant and so `missing`). The
  frontend builds on it with `CAOS_DATA_ROOT=docs/contracts/fixtures/data/derived` (a walking skeleton before any
  bake), the API serves it with `DATA_DIR=docs/contracts/fixtures/data/derived`, and the contract tests run against
  it and against `data/derived/` with the same assertions (the swap tests).
- `docs/contracts/fixtures/data/examples/params.csv`: a two-row source table for contract 1.
- `data-pipeline/pipeline/model/baseline.py`: the surrogate slot's baseline, the SIR peak with S0 = 1,
  `1 - (1 + ln r0) / r0` for `r0 > 1`, else 0. It needs no trained bundle.

A provider is scaffolding: labelled on every surface by the readiness document, never counted as done for the unit
that owes the real producer.

## History

One row per version of every contract, newest last within a contract. `kind` is initial, major, minor or patch, per
the rules above. The rows of 0.04.000 record the versions that release shipped; an earlier shape of a contract is
not reconstructed.

| contract | version | date | change | kind |
|---|---|---|---|---|
| params-record | 1.0.0 | 2026-10-11 | the ingestion record: case id, SIR parameters with the bounds of contract 1 | initial |
| case-index | 2.0.0 | 2026-10-11 | the index of cases with bilingual titles, categories and the default case (`example.index/v2`) | initial |
| case-manifest | 4.0.0 | 2026-10-11 | the per-case manifest with lane verdict, metrics and the model behind them (`example.manifest/v4`) | initial |
| trace | 1.0.0 | 2026-10-11 | the per-case trace, at most 200 points, with a summary (`example.trace/v1`) | initial |
| surrogate-model | 1.0.0 | 2026-10-11 | the slot r0 to peak infected fraction, with the analytic baseline behind it | initial |
| readiness | 1.0.0 | 2026-10-11 | what is real in a build, row by row, in one of six declared states | initial |
| api | 1.0.0 | 2026-10-11 | the dormant read-only API, GET only, 503 with the declared state when a document is absent | initial |
