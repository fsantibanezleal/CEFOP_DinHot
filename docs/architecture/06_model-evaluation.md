# Model evaluation: the benchmark protocol and the held-out tests

Evaluation is where the honesty of the product lives. No controlled published comparison of WGS, phase-fixed WGS, conjugate gradient, MRAF and a learned method on the same point-trap array was found in the research, so
the protocol below is DinHot's own, and its numbers are measured, never quoted.

## The scorer

A method reports its own history; the verdict the manifest and the benchmark carry is recomputed by `data-pipeline/pipeline/core/score.py` from the final phase, through the same forward model for every method and through
the case's device and aberration. Methods are compared on one footing and a method cannot grade itself. The metrics are efficiency, uniformity and relative standard deviation ([P01](../frameworks/P01_forward-models-and-metrics.md)),
plus the zero-order and ghost fractions.

## The benchmark protocol

`data-pipeline/pipeline/benchmark/protocol.py` runs the registry over geometries, devices, parameter sets and budgets; the geometries are in `data-pipeline/pipeline/benchmark/geometries.py`.

**Geometries** (lengths in Fourier units $u = \lambda f/(n_{pix}p)$, one unit is `pad` focal bins; the benchmark optics keep $u$ and the focal bin fixed across grids: 850 nm, pitch 20 um, $f$ scaled with $n_{pix}$, so $u$ = 0.996 um):

| Id | Geometry | Traps | Grid |
|---|---|---|---|
| G1 | square 10 by 10 at 8 u | 100 | 256 |
| G2 | ring of 36 traps | 36 | 256 |
| G3 | random, at least 3 u between traps | 100 | 256 |
| G4 | quasi-periodic (cut and project of the 5-dimensional lattice to a five-fold set, scaled 7 u) | 119 | 256 |
| G5 | 3D lattice 5 by 5 by 3, 8 u in the plane and 8 um between planes | 75 | 256 |
| G6 | large 32 by 32 at 6 u | 1024 | 512 |
| G7 | shaped fields, four pooled (a seed runs shape seed mod 4): ring, disc, line, Laguerre-Gaussian ring | none | 128 |

G4 is DinHot's own set (the quasi-periodic set of Polin et al. is not published as coordinates). G6 is the lattice only; the disordered 819-trap set of Kim et al. is not in the protocol, whose schema holds one target per
geometry id. The device cells use the C08 device (4 bits, crosstalk, fill factor 0.85, flicker 0.05 rad); a device cell on a 3D geometry is not run (the device model is read at the focal plane), and is listed.

**Runs.** For every method, geometry, device (ideal or device) and parameter set, over `seeds` seeds (default 20; seed $s$ is the engine seed, so every method of a cell starts from the same random numbers), six runs per seed:

- iteration budgets of 10, 30 and 100 iterations: a run of exactly that many;
- wall-clock budgets of 50 ms and 1 s: a run capped at that time and at the converged cap;
- converged: a run to the cap (300 iterations), which is also the 60 s row (the cap is reached well before 60 s on the benchmark grids).

**Tuning.** A method that declares a tuning grid of exactly four candidates, or has a fallback entry whose names its `run` accepts, is tuned: each candidate runs on 3 other seeds (offset 1000) at 30 iterations and the one with
the lowest median relative standard deviation among those with at least half the best median efficiency gives the `tuned` rows. The number of tuning runs is the same for every tuned method. A method without a grid has
`default` rows only; no row mixes one method's tuned parameters with another's defaults, and the `params` field of each row says which it is.

**Rows.** A row reports the median and the inter-quartile range over seeds of efficiency, uniformity, relative standard deviation (percent), the wall-clock seconds and the iterations. A cell that cannot run is in `skipped` with a
bilingual reason (the method is not registered, its spec does not take the geometry's target, or the device model cannot be read), never silently absent. The B5 Pareto front is stored from the method's metadata. Resume is per group;
the pool uses at most 12 worker processes. The document is the benchmark-results row of [the contracts](08_data-contracts.md).

Tests: `tests/bake/test_benchmark.py`, on a 64-pixel reduced grid with planted methods: schema validity, units, all budget kinds, skipped cells, tuned never mixed with default, equal tuning runs per method, resume, pool equals sequential.

Status: the full run over the 24-method ladder (`python data-pipeline/run.py benchmark --resume`) is not committed yet; the Benchmark page shows "not available yet" with the reason until it is. This page quotes no benchmark number.

## The oracles

The acceptance tests of the methods and the checks of the cases use independent solutions in `data-pipeline/pipeline/oracles.py`, which share no code with the engine: the overdamped bead's Lorentzian corner frequency and equipartition,
the random-mask efficiency about $1/M$, the vortex winding of $2\pi l$, Parseval, and the published rows of the calibration case. A disagreement is a finding about one of the two sides.

## The learned models

The two learned methods (M17, B3) are evaluated only on held-out geometries that the training never saw; the held-out set is written before training and its hash is recorded in the model card. The metrics document
(`model-metrics`) compares each model with its baseline (GS at the same wall-clock budget for the CNN; the random start for the warm start). A model that does not meet its acceptance criterion is not released: the baseline
answers, readiness says `training`, and the measured values are reported as they are. Training and evaluation run offline and locally (ADR-0069, ADR-0074).

## Honesty rules

- Held-out means disjoint from calibration and training; the acceptance values of each method card state seeds, grid and date.
- "Accurate" means agrees with the stated engine and device model, not matches a real instrument.
- A published number is labelled with its source and conditions; a DinHot measurement is labelled as one. Where DinHot does not reproduce a published number (M02 uniformity, M07 at its source default), the card says so.
