# Determinism and the trace

**A run is a pure function of `(params, seed)`.** There is no global random generator anywhere (ADR-0054). Every random draw goes through the portable generator `Rng(seed)` of
`data-pipeline/pipeline/model/holo/core/rng.py` ([P07](../frameworks/P07_portable-rng.md)): xoshiro128** seeded by SplitMix32, whose uniforms and normals the TypeScript port reproduces bit for bit
(the uniforms) and to about 1e-15 (the normals). The draw order is part of the contract and is fixed in each module docstring (the starts, the camera gains and noise, the device flicker, the particle noise).

Every method of a case is given the same seed, so all of them start from the same random numbers and the same budget; the verdict of the bake is recomputed from the returned phase by the scorer
(`data-pipeline/pipeline/core/score.py`) through the same forward model for every method, so a method cannot grade itself.

Same inputs give byte-identical artifacts: the manifest carries no clock, and the only measured quantity behind it, the run time that decides the lane, is stored as a verdict and the deterministic budgets, never as
milliseconds. `tests/test_manifest.py` holds this (`test_adversarial_two_bakes_of_the_same_inputs_write_identical_bytes` compares every JSON of two bakes byte by byte). The pipeline tests also run in a sandbox that fails the session
if a committed artifact changes.

## The trace

The trace (`data-pipeline/pipeline/core/trace.py`, schema `dinhot.trace/v1`, catalog row trace) is the compact replay artifact of one case, at most 256 KiB. It is decimated, not the raw state:

| Field | Decimation |
|---|---|
| Method history (metric series against iteration) | at most 200 points, uniform in the iteration index, first and last kept |
| Final per-trap intensities and metrics | all traps, relative to the mean trap (mean 1) |
| Reference method: quantized phase mask | `phase_u8`, the phase in 256 levels over $[0, 2\pi)$ on the SLM grid, base64 |
| Reference method: focal intensity | `intensity_db_u8`, dB relative to the mean trap, floor -40 dB mapped to 0 to 255, crop of at most 128 bins, blocks max-pooled so a peak is never lost |
| Axial cut (3D cases) | `xz_u8`, the same dB scale |
| Bead or atom trajectory | at most 4000 points; power spectrum at most 200 log-spaced bins |
| Rearrangement | at most 120 frames |

A trace that would exceed the byte gate is squeezed through a fixed list of five settings, the first being the full trace (fewer decimals, a shorter history, a smaller focal crop, no axial cut, a shorter trajectory); one that still does not fit raises
`TraceTooLarge`, so the bake fails and the lane gate never sees an oversized artifact. Its shape is mirrored by the generated types of the frontend (contract 2).

Training datasets and checkpoints stay in the data root, never in the repository; only the compact artifacts, the released models and their cards are committed and shipped.
