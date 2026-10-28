# U3b fragment (for the main session to merge into the SDD, the catalog and the changelog)

## SDD changes

- Section "Sizing and contracts", item Ingestion: contract 1 is `data-pipeline/pipeline/io/contract.py` over a standard-library
  validator (`io/jsonschema_lite.py`) of `docs/contracts/schemas/params-record.schema.json`; a trap at or beyond the half-field
  `lambda f / (2 p)` is refused (the engine's rule: the bin at the bound is outside the centred FFT grid).
- Section "Cases": the expected ranges are `expect` keys `<metric>` (reference method), `<method>.<metric>` and the case metrics
  `feedback_initial_rel_std_pct`, `feedback_final_rel_std_pct`, `fc_ratio`, `boltzmann_tv`, `min_transient`, `final_filling`
  (`core/expect.py`). Case ids: `C01_square_grid`, `C02_grid_feedback` (default), `C03_large_array`, `C04_disc_crosstalk`,
  `C05_multiplane_vortices`, `C06_vortex_ring_line`, `C07_high_na`, `C08_device_limited`, `C09_aberrated`, `C10_rearrangement`,
  `C11_outside_field`, `C12_calibration`. A device case excludes traps off the focal plane, vortex charge and an aberration.
- Section "Lanes": the lane gate judges the reference method (live or both in its spec, one warm run at most 1500 ms, trace at most
  256 KiB); each method gets its own lane. A trace over the gate is squeezed in five fixed steps (`core/trace.py` `SQUEEZE`) and the
  step is recorded as a manifest flag.
- Benchmark protocol: one converged run per seed also serves as the 60 s row; the 50 ms and 1 s rows are time-capped runs; the 10, 30
  and 100 iteration rows are runs of exactly that length; every run is scored from its final phase through the device. Tuned rows exist
  only for methods that declare `TUNING` (four candidate keyword dictionaries) or have an entry in `FALLBACK_TUNING`. G6 is the
  32 x 32 lattice only (the disordered 819 set is not in the table); G7 pools four shaped targets (seed `s` runs shape `s mod 4`).
- Test paths: `tests/bake/` (planted-method tests of the bake, gates and benchmark) is new.
- Resources: measured resources of the bake and the benchmark replace the bounds once the canonical run exists.

## Catalog (docs/contracts, not in this unit's scope)

- After the canonical bake: set `status` to `real` for params-record, case-index, case-manifest, trace and benchmark-results, and
  recompute `data/derived/readiness.json`.
- `readiness.schema.json` keeps the const `example.readiness/v1` (U3a open question 1); `core/readiness.py` writes that value.
- `trace`: `shape.mask_rle` is the run-length code of the shape over the focal crop, row-major, alternating false and true runs,
  starting with false. `dynamics.x_um` and `y_um` are displacements from the trap centre in micrometres; `fc_hz` is the fitted corner
  frequency of a bead and the spectral peak of an atom.

## Interfaces assumed of the method units (UNVERIFIED until E2 and E3 merge)

- `run(setup, target, *, device, budget, rng, init)` as `core/types.py`; an `aberration` parameter (Noll coefficients in waves,
  index 0 = piston) is passed to a method that declares it (M14); `TUNING` (list of four keyword dictionaries) is read from a method
  module; `Result.meta` may carry `iterations`, `converged` and, for B5, `pareto` (list of `{lambda, efficiency, uniformity}`).
- Case-level drivers (feedback, rearrangement) use a weight-aware registered method (M07, else M06, else M04) with `init` and
  weights in the target; they do not call M12 or M16 internals.
