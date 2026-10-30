# The data contracts

A product is real when its data flows through enforced contracts. Every boundary of DinHot is a row of [`docs/contracts/catalog.md`](../contracts/catalog.md) (ADR-0080): its owner, its version, one language-neutral
schema file, an example, a test on each side, its missing-data behavior, a provider that serves it until the real producer exists, and a swap test that runs the same consumer assertions against both. The schema files are the single source:
Python validates against them in its tests, and the TypeScript types are generated from them.

## The rows

| Row | Version | Schema | Producer | Consumer |
|---|---|---|---|---|
| params-record | 1.0.0 | `docs/contracts/schemas/params-record.schema.json` | a source table of cases (`data/examples/cases.json`) | contract 1, `data-pipeline/pipeline/io/contract.py` |
| case-index | 1.0.0 | `docs/contracts/schemas/case-index.schema.json` | `data-pipeline/pipeline/core/manifest.py` | the web, the API |
| case-manifest | 1.0.0 | `docs/contracts/schemas/case-manifest.schema.json` | `data-pipeline/pipeline/core/manifest.py` | the web, the API |
| trace | 1.0.0 | `docs/contracts/schemas/trace.schema.json` | `data-pipeline/pipeline/core/trace.py` | the web, the API |
| benchmark-results | 1.0.0 | `docs/contracts/schemas/benchmark-results.schema.json` | `data-pipeline/pipeline/stages/benchmark.py` | the web, the API |
| cgh-net (model slot) | 1.0.1 | `docs/contracts/schemas/model-card.schema.json` | the training stage | the bake, the web (ONNX inference) |
| warmstart-model (model slot) | 1.0.1 | `docs/contracts/schemas/model-card.schema.json` | the training stage | the bake, the web (ONNX inference) |
| model-metrics | 1.0.1 | `docs/contracts/schemas/model-metrics.schema.json` | the evaluate stage | the web, the API |
| engine-reference | 1.0.0 | `docs/contracts/schemas/engine-reference.schema.json` | the engine-reference writer of the Python engine | the TypeScript engine's parity tests |
| readiness | 1.0.0 | `docs/contracts/schemas/readiness.schema.json` | `data-pipeline/pipeline/core/readiness.py` | the web, the API |
| api | 1.0.0 | `docs/contracts/api.openapi.json` (OpenAPI 3.1) | `app/` | any HTTP client |

The schema identifiers are `dinhot.trace/v1`, `dinhot.manifest/v1`, `dinhot.index/v1`, `dinhot.benchmark/v1`, `dinhot.model-card/v1` and `dinhot.model-metrics/v1`.

## Contract 1, ingestion (raw to pipeline)

`data-pipeline/pipeline/io/contract.py` applies the params-record schema to a source table, read through a standard-library validator (`jsonschema_lite.py`) so that readiness runs in CI with nothing installed. A case is a
record with: the optical setup, the device, the target, the aberration, the method set and the reference method, the budget, the seed, and for the dynamic cases the camera feedback, the particle and the rearrangement,
and its expected ranges.

| Block | Fields and units | Range enforced by the schema |
|---|---|---|
| setup | wavelength (nm), focal length (mm), numerical aperture, immersion index, SLM side in pixels, pixel pitch (um), padding, input beam | 300 to 2000 nm; 0.5 to 1000 mm; NA 0.05 to 1.5; index 1.0 to 1.6; pixels 64, 128, 256, 512 or 1024; pitch 1 to 50 um; padding 1 to 4 |
| device | bit depth, crosstalk (sigma per pixel, q), upsampling, fill factor, flicker (rad), LUT gamma | bits 1 to 16 or none; upsampling 1 to 5; fill 0.5 to 1; flicker 0 to 1 rad; gamma 0.5 to 2 |
| trap | id, x, y, z (um), relative weight, topological charge | id 0 to 4095; positions within plus or minus 100000 um; weight 0.01 to 100; charge -20 to 20 |
| seed | integer | 0 to 2147483647 |

Beyond the schema, the rules a schema cannot state: unique ids, the reference method is in the method set, the numerical aperture does not exceed the immersion index, a device model is read at the focal plane only, so it excludes traps off the focal plane or with a vortex charge, and it excludes an aberration (not modelled together),
the camera, particle and rearrangement blocks need a trap target and name traps of it, a shaped target has the dimensions its shape needs and fits the field of view, and every expect key is a known metric. **A trap at or beyond the unaliased field bound $\lambda f/(2p)$ is rejected, with the bound in the reason**
(case C11 exists to prove it); this is stricter than the schema text.

**Outliers and missing data.** A record is rejected with its reason when a value is missing, non-numeric, NaN, infinite or out of range; nothing is coerced (a string is not a number, a NaN is not a value). A plausible but
unusual record is accepted and flagged, and the flag is carried into the manifest: the scalar model is flagged from a numerical aperture of 0.7 (vectorial focusing is not modelled), and traps closer than the focal spot are flagged. Trap coordinates are rounded to 0.1 nm once, here, before any run, and stored as accepted. A rejected case is dropped with its reason and the bake continues with the others; the index lists it as refused, with no
manifest and no trace. A test holds the schema's bounds equal to the code's. This is the door through which a reader's own case enters ([guide 02](../guides/02_bring-your-own-data.md)).

## Contract 2, artifacts (pipeline to web)

The bake writes, into `data/derived/`:

- the case index (`dinhot.index/v1`): every case with its bilingual title and category, baked or refused, and the case the App opens on;
- one manifest per baked case (`dinhot.manifest/v1`): the parameters as the producer used them, the seed, the engine and its version, the artifact and its byte size, the lane verdict and the gate, the flags from contract 1 and
  from the bake, the verdict per method (the metrics recomputed by the scorer), the model slots behind it, the expected ranges, the bilingual expected band and the published anchor;
- one trace per case (`dinhot.trace/v1`, at most 256 KiB, see [determinism and the trace](02_determinism-and-trace.md));
- the benchmark results (`dinhot.benchmark/v1`): the table method by geometry by budget, medians and inter-quartile ranges over seeds, the Pareto fronts, the skipped cells;
- the model metrics (`dinhot.model-metrics/v1`): the held-out metrics of the two slots against their baselines;
- the readiness document: what is real in this build, row by row.

A manifest is a pure function of `(params, seed)`: no clock. Units are fixed (see [the units gate](03_the-gate.md)): positions in micrometres, relative standard deviation in percent, intensities relative to the mean trap.

## The model slots

Two slots, each an ONNX graph plus a card (the card names its own slot, its byte size and its SHA-256). **cgh-net**: input `target` float32 [1, 3, 128, 128] (the target amplitudes of three focal planes at -8, 0 and +8 SLM-limited Rayleigh
ranges, unit-sum intensities, for a 128 x 128 SLM with pad 1), output `phase` float32 [1, 1, 128, 128] in radians; baseline: the volumetric GS
([M19](../frameworks/M19_volumetric-3d-gs.md)) at 30 iterations. **warmstart-model**: input `traps` float32 [1, 1024, 4] (x and y in focal bins over the half field, z in Rayleigh
ranges, weight; padded) and `mask` float32 [1, 1024], output `trap_phase` float32 [1, 1024] in radians; baseline: the random trap phases of the portable generator ([P07](../frameworks/P07_portable-rng.md)). A slot is released
only when its card validates and its graph exists with the card's size and hash (`data-pipeline/pipeline/io/model_card.py`); otherwise the baseline answers and readiness says `training`. A swap test runs the same assertions
against the baseline and the released model. The baselines are in `data-pipeline/pipeline/model/baseline.py`; they need no released model.

## Missing data is a declared state

Every row has one of six states, computed by `data-pipeline/pipeline/core/readiness.py` from the catalog and the repository and written to the readiness document: `available`, `partial` (what is absent is listed), `stale` (an older bake
answered), `provider` (the row's provider answered), `training` (a model slot answered with the released model or the baseline while a newer one trains, or with the baseline while none is released) and `missing`. The rules
and their bilingual reasons are the catalog's section Missing-data states. The site labels every view that a provider, a stale bake or the baseline serves, and shows "not available yet" with the reason for what is missing; the dormant API
answers 503 with the state and the reason instead of an empty body that looks like data. The document carries the product version and the catalog's SHA-256 instead of a time, so a re-bake does not dirty the tree.

## The walking skeleton

`docs/contracts/fixtures/data/derived/` is a provider tree in the layout of `data/derived/`: one small case (`FX01_fixture`, three traps, three methods), its manifest and trace, an index that lists one refused case, a benchmark
document with two rows and one skipped cell, a model-metrics document and a readiness document that says provider for every row but the dormant API. The site builds on it
(`CAOS_DATA_ROOT=docs/contracts/fixtures/data/derived npm run build`) and the API serves it (`DATA_DIR=docs/contracts/fixtures/data/derived`), so the frontend and the API are deployed and checked before the first real bake,
and every contract test runs against it and against the bake with the same assertions.

## How they are held

- The bake fails when a result lies outside its case's expected range (`data-pipeline/pipeline/core/expect.py`).
- `tests/contracts/` validates every document the pipeline writes (a fresh sandbox bake and the committed one), the provider tree, the model slots and every API response against the schema files and the OpenAPI document.
- The generated types of the web come from `docs/contracts/api.openapi.json`; the web build fails when they are not current, and the web's contract test reads every committed document and the provider tree against the
  descriptors in both directions.
- `scripts/check_artifacts.py` checks that the index, the manifests and the artifacts agree, byte sizes included, and that each lane matches its gate; `scripts/check_readiness.py` that the committed readiness is current;
  `scripts/check_contracts.py` that every catalog field and path is valid; `scripts/check_contract_versions.py` that a schema did not change under the same version.
