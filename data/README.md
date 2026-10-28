# data/, the data contracts and layout of DinHot

This folder is governed by the two data contracts of ADR-0057, written in `docs/contracts/` (catalog `docs/contracts/catalog.md`,
one schema file per row in `docs/contracts/schemas/`). Everything here is synthetic: DinHot computes holograms in simulation, so a
"case" is a parameter record, and the baked artifacts are the evidence the site replays (ADR-0054).

## Layout

| Path | What | Git |
|---|---|---|
| `raw/` | private or large source inputs (none today) | git-ignored |
| `examples/cases.json` | the source document of contract 1: the twelve cases C01 to C12 as params records | committed |
| `derived/manifests/index.json` | the flat inventory of every case, baked or refused, with bilingual titles and categories | committed |
| `derived/manifests/<case>.json` | the manifest of one baked case (contract 2) | committed |
| `derived/<case>/trace.json` | the replay trace of that case, at most 256 KiB (contract 2) | committed |
| `derived/benchmark/results.json` | the benchmark table, method by geometry by budget, and the Pareto fronts | committed |
| `derived/models/metrics.json` | held-out metrics of the two model slots (written by the model unit) | committed |
| `derived/readiness.json` | what is real in this build, row by row, computed from the catalog | committed |
| `demo/`, `samples/`, `artifacts/` | small deterministic payloads for smoke runs | committed |

## CONTRACT 1, ingestion (cases.json to pipeline), the bring-your-own-case gate

`data-pipeline/pipeline/io/contract.py` reads `data/examples/cases.json` (an array of params records; shape in
`docs/contracts/schemas/params-record.schema.json`) with a standard-library validator over the schema file. A record is accepted
iff it passes the schema and these rules, rejected with a reason otherwise (never coerced), flagged when plausible but suspicious:

| Rule | Outcome |
|---|---|
| a field missing, not the stated type, NaN, or outside its range (wavelength 300 to 2000 nm, `n_pix` in 64..1024, and so on) | reject, naming the path and the bound |
| `reference_method` not among `methods`; duplicate trap ids; `na` above `n_imm` | reject |
| a trap with `abs(x_um)` or `abs(y_um)` at or beyond the unaliased half-field `lambda f / (2 p)` | reject, naming the bound (case C11 is this, on purpose) |
| a device model with traps off the focal plane or with vortex charge, or together with an aberration | reject (not modelled together) |
| `feedback`, `dynamics`, `rearrangement` on a shaped target; ids that name no trap | reject |
| a shaped target missing the dimensions its shape needs, or reaching the field edge | reject |
| an `expect` key that is not a known metric (or `<method>.<metric>`) or an empty range | reject |
| `na` at or above 0.7 | flag: the scalar model is past its validity |
| traps closer than the focal spot (`pad` bins); traps beyond 85 percent of the half-field | flag |

Trap coordinates are rounded once to 0.1 nm here, before any run; the manifest stores the values as accepted. A rejected record is
dropped, the bake goes on, the index lists it as `refused` with the reason, and `readiness.json` lists its id (row params-record,
state `partial`). Without `examples/cases.json` the bake uses the registry's twelve records and readiness says `missing`.
`python data-pipeline/run.py cases` rewrites the file from the registry.

## CONTRACT 2, artifact (pipeline to web)

`python data-pipeline/run.py` bakes every accepted case with every method valid for it (`methods` of the record, run through the
method registry), checks each against its expected ranges (`core/expect.py`; the bake fails naming case, method and metric), measures
the lane gate (reference method run time against 1500 ms and the trace against 256 KiB), runs the units gate and writes:

- `derived/<case>/trace.json` (schema `dinhot.trace/v1`): per method the metric series against iteration and the final per-trap
  intensities (relative to the mean trap); for the reference method the phase mask (`phase_u8`), the focal intensity in dB
  (`intensity_db_u8`, max-pooled to at most 128 x 128), the axial cut; the camera-feedback steps (C01 to C03), the particle
  trajectory and its spectrum (a bead in C01, a rubidium atom in C03), the rearrangement frames (C10). A shaped target's
  `mask_rle` is the run-length code of the shape over the focal crop (row-major, runs alternate false and true, starting with false).
- `derived/manifests/<case>.json` (schema `dinhot.manifest/v1`): params as used, seed, engine and version, the artifact and its bytes,
  the lane and gate verdict, flags, the verdict per method, the model slots behind the metrics (`real` or `baseline`), the expected
  ranges and the published anchor. A pure function of (params, seed): no wall-clock time.
- `derived/manifests/index.json` (schema `dinhot.index/v1`).
- `derived/benchmark/results.json` (schema `dinhot.benchmark/v1`): written by `python data-pipeline/run.py benchmark`, which
  carries wall-clock times (the only place they live) and says so in its protocol text.
- `derived/readiness.json`: `python data-pipeline/run.py readiness`.

The bake and the benchmark never run in CI (ADR-0074). Tests write only to temporary directories (`tests/conftest.py` guards
`data/` and `models/`). `python scripts/check_artifacts.py` and `python scripts/check_documents.py` validate the committed tree.

## Expected ranges

Each case states `[low, high]` per metric. A key `efficiency` applies to the case's reference method, `M04.uniformity` to that method,
and the case metrics (`feedback_final_rel_std_pct`, `fc_ratio`, `boltzmann_tv`, `min_transient`, `final_filling`) to the drivers'
measurements. The ranges are of two kinds, recorded per case in `pipeline/cases/library.py`: an anchor band (a published result, with
the seed spread as margin) or a provisional band (the physical limits of the case, to be replaced by a measured band with its
margin once the real methods have been baked).

## Provenance and licence

The data are generated by the engine in `data-pipeline/pipeline/model/holo/`; the published results a case is set against are cited by
DOI or arXiv link in its manifest (`anchor`), and the optics are those stated in `pipeline/cases/library.py`. Nothing here is
measured on an instrument; absolute numbers are those of the stated scalar model.
