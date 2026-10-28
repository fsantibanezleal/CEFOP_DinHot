# The data contracts

A product is real when its data flows through enforced contracts. Every boundary of the template is a row of
[`docs/contracts/catalog.md`](../contracts/catalog.md) (ADR-0080): its owner, its version, one language-neutral
schema file, an example, a test on each side, its missing-data behavior, a provider that serves it until the real
producer exists, and a swap test that runs the same consumer assertions against both. The schema files are the
single source: Python validates against them in its tests, and the TypeScript types are generated from them.

## The rows

| Row | Schema | Producer | Consumer |
|---|---|---|---|
| params-record | `docs/contracts/schemas/params-record.schema.json` | a source table (`data/examples/params.csv`) | contract 1, `data-pipeline/pipeline/io/contract.py` |
| case-index | `docs/contracts/schemas/case-index.schema.json` | `data-pipeline/pipeline/core/manifest.py` | the web, the API |
| case-manifest | `docs/contracts/schemas/case-manifest.schema.json` | `data-pipeline/pipeline/core/manifest.py` | the web, the API |
| trace | `docs/contracts/schemas/trace.schema.json` | `data-pipeline/pipeline/core/trace.py` | the web, the API |
| surrogate-model (model slot) | `docs/contracts/schemas/surrogate-model.schema.json` | `data-pipeline/pipeline/stages/train.py` | `data-pipeline/pipeline/stages/evaluate.py` |
| readiness | `docs/contracts/schemas/readiness.schema.json` | `data-pipeline/pipeline/core/readiness.py` | the web, the API |
| api | `docs/contracts/api.openapi.json` (OpenAPI 3.1) | `app/` | any HTTP client |

## Contract 1, ingestion (raw to pipeline)

`data-pipeline/pipeline/io/contract.py` applies the params-record schema to a source table: the required fields,
their units and ranges, and the outlier policy. A record is rejected with its reason when a value is missing,
non-numeric, NaN, infinite or out of range (and, in the example, when the initial infected exceed the population); a
plausible but unusual record is accepted and flagged (the example flags R0 above 20), and the flag is carried into
the manifest. Nothing is coerced. A test holds the schema's bounds equal to the code's. This is the door through
which a reader's own data enters ([guide 02](../guides/02_bring-your-own-data.md)).

## Contract 2, artifacts (pipeline to web)

`data-pipeline/pipeline/core/trace.py` and `data-pipeline/pipeline/core/manifest.py` write, into `data/derived/`:

- `data/derived/manifests/index.json` (`example.index/v2`): every case with its bilingual title and category, and the
  case the App opens on;
- `manifests/<case>.json` (`example.manifest/v4`): parameters, seed, engine and version, the artifact and its byte
  size, the lane verdict, the evaluation metrics and the model that produced them (released or baseline), the
  expected ranges, and the bilingual expected band;
- `<case>/trace.json` (`example.trace/v1`): at most 200 points of the trajectory and its summary.

## The model slot

The surrogate maps r0 = beta / gamma to the peak infected fraction, clamped to [0, 1]. Its released bundle is
`models/surrogate.json`; when no valid bundle exists, the baseline `data-pipeline/pipeline/model/baseline.py`
answers (the SIR peak with S0 = 1: `1 - (1 + ln r0) / r0` for r0 > 1, else 0), so the product never waits for a
model. A swap test runs the same assertions against the baseline and the trained bundle. `--no-train` bakes with the
released bundle or the baseline and never trains.

## Missing data is a declared state

Every row has one of six states, computed by `data-pipeline/pipeline/core/readiness.py` from the catalog and the
repository and written to `data/derived/readiness.json`: `available`, `partial` (what is absent is listed),
`stale` (an older bake answered), `provider` (the row's provider answered), `training` (a model slot answered with
the released model or the baseline while a newer one trains, or with the baseline while none is released) and
`missing`. The rules and their bilingual reasons are the catalog's section Missing-data states. The site labels
every view a provider, a stale bake or the baseline serves and shows not available yet, with the reason, for what is
missing; the dormant API answers 503 with the state and the reason instead of an empty body that looks like data.
The readiness document carries the product version and the catalog's SHA-256 instead of a time, so a re-bake does
not dirty the tree.

## The walking skeleton

`docs/contracts/fixtures/data/derived/` is a provider tree in the layout of `data/derived/`: one case, its
manifest and trace, the index, and a readiness document that says provider for every row but the dormant api. The site builds on it
(`CAOS_DATA_ROOT=docs/contracts/fixtures/data/derived npm run build`) and the API serves it
(`DATA_DIR=docs/contracts/fixtures/data/derived`), so a product's frontend and API are deployed and checked before
its first real bake, and every contract test runs against it and against the bake with the same assertions.

## How they are held

- The bake fails when a result lies outside its case's expected range (`data-pipeline/pipeline/core/expect.py`).
- `tests/contracts/` validates every document the pipeline writes (a fresh sandbox bake and the committed one), the
  provider tree, the model slot and every API response against the schema files and the OpenAPI document
  (`tests/contracts/contract_schemas.py`, jsonschema with Draft 2020-12).
- `frontend/src/lib/contract.gen.ts` is generated from `docs/contracts/api.openapi.json` by
  `frontend/scripts/gen-contract-types.mjs`; the web build fails when it is not current. `frontend/src/lib/contract.types.ts`
  names the generated types and ties the run-time descriptors to them by `tsc`; `frontend/src/lib/contract.test.ts`
  reads every committed document and the provider tree against the descriptors in both directions.
- `scripts/check_artifacts.py` checks that the index, the manifests and the artifacts agree, byte sizes included,
  and that each lane matches its gate; `scripts/check_readiness.py` that the committed readiness is current;
  `scripts/check_contracts.py` that every catalog row is complete and every path it names exists;
  `scripts/check_skeleton.py` lists the rows still served by a provider (allowed while a product is built, never at a
  release).
- `frontend/scripts/copy-data.mjs` copies exactly the declared files into the site, the readiness document included,
  and fails on a missing one; the web fetches them with the version in the address and refuses an answer that is not
  JSON.
