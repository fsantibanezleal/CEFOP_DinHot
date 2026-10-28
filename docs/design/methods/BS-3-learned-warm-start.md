# BS-3: Learned warm start for phase-fixed WGS (engine id B3), refuted

| Item | Value |
|---|---|
| Ladder row | BS-3, tier beyond (SDD, Method ladder and Beyond the state of the art) |
| Family, lane | beyond, learned; `SPEC.lane` is `baked` (the warm start is refuted and no model is released) |
| Targets, dimensions | traps, 2D and 3D |
| Module | `data-pipeline/pipeline/model/holo/methods/learned/b3_warm_start.py` (`N_FIX` line 28, `SPEC` line 29, `predict_phases` line 33, `start_hologram` line 39, `run` line 43); network and training in `data-pipeline/pipeline/model/holo/learned/` (`nets.py`, `training.py`, `torch_forward.py`, `evaluation.py`, `heldout.py`) |
| Gate | `tests/learned/test_b3_warm_start.py` |
| Record of the refusal | `data/derived/models/warmstart-model-rejected.json` (no ONNX file is committed: `models/` holds only `cgh-net`) |
| Live port | the inference helper `predictWarmstart` in `frontend/src/lib/ort.ts` and the `trapPhases` option of the M07 run exist; no model is released, so the random start answers |
| Card | [B3](../../frameworks/B3_learned-warm-start.md) (written before the model; it still says "pending") |
| Outcome | hypothesis refuted: iterations ratio 1.75 against 2 required, final efficiency 4.2 percent apart against 1 percent, and a control without the network gains as much; the model is not released |

## Tier and role

Beyond the state of the art: DinHot's own proposal, tested and refuted. A negative result is a result (CAOS rule on the method tiers) and is kept.

**Hypothesis.** A small permutation-equivariant network over the trap list, predicting the initial trap phases $\theta_m$ of phase-fixed WGS (M07), lets M07 reach a relative standard deviation of
1 percent in at least two times fewer iterations (median) than from a random start on held-out geometries, with the final efficiency and uniformity equal within 1 percent, a model of at most 1 MB.

**The gap.** Ren et al. 2024 (https://arxiv.org/abs/2401.06014) generate a full phase with a U-Net (0.16 s, about 10 percent site variation for about 20 traps); DeepCGH shows learned speedups for volumes
(https://doi.org/10.1364/OE.399624); a hologram network under 620 KB is possible (Shi et al. 2021, https://doi.org/10.1038/s41586-020-03152-0, abstract only read). No source read uses a network to
initialize WGS and none compares with WGS; the search found only GS-RNN style methods (algorithms dossier D5.1 B3). The risk named before the work: the random-phase start is already reliable for WGS, so
the gain may be small.

## Problem it answers

Fewer iterations of M07 for a new trap geometry (the start decides how soon the weights converge).

## Inputs and outputs

- Inputs: `setup`, a `Target` of kind `traps` (a shaped field raises a `ValueError` naming `traps`), `budget`, `rng`, optional `init` (a starting hologram, overrides the model), `n_fix`, `form`
  (default `point`, line 43, because the 3D traps need it), `models_dir`. Vortex traps and more than 1024 traps raise a `ValueError` (`learned/convert.py`, `traps_to_input`).
- Network contract (catalog row `warmstart-model`): inputs `traps` float32 `[1, 1024, 4]` (x and y in focal bins, z in SLM-limited Rayleigh ranges, weight) and `mask` float32 `[1, 1024]`; output
  `trap_phase` float32 `[1, 1024]` in radians.
- Output: the `Result` of M07 started from the model's hologram, with `meta['provenance']` equal to `real`, `baseline` or `given`. With no released model the answer is M07 from its own random start (the
  M02 start from the same random stream), provenance `baseline`.

## The method

The SLM start is the superposition hologram with the learned trap phases,

$$\phi^{(0)}_j = \arg\sum_m \sqrt{w_m}\,e^{\,i(\Delta_j^m + \theta_m)}$$

(the form of M02 with learned instead of random $\theta_m$; `start_hologram`, line 39), and M07 runs from it. The network `SetNet` (`learned/nets.py` line 50) is a permutation-equivariant set transformer: Fourier
features of the trap coordinates, an embedding, two attention blocks of width 64 with 4 heads and feed-forward width 128, a head for the phase and a set-dependent chirp coefficient (a quadratic phase law);
80.8 thousand parameters, 338 987 bytes as ONNX (M1 report; the rejected record).

Training is unsupervised and has no labels: the loss is the mean of $\log(\sigma^2 + 0.01)$ of the trap-intensity relative standard deviation along 10 unrolled M07 iterations with the freeze at `n_fix = 3`
(`learned/torch_forward.py` `unrolled_wgs`, a differentiable copy of the rule, checked against M07 in `tests/learned/test_torch_forward.py`), so the network learns a start from which M07 converges sooner. It is not a
regression onto converged phases, which are not unique (the global phase and the many WGS fixed points would make labels ambiguous). The global-phase invariance is automatic: the loss reads intensities only.
Configuration (record): 6000 steps, batch 8, learning rate 0.0008, data seed 20261101, initialization seed 7, d = 64, 2 layers, 4 heads, feed-forward 128. The trap-set generators: lattices, hexagonal, rings, random sets with
a minimum spacing and 3D stacks; there is no quasi-periodic family, so the benchmark geometry G4 is unseen. One earlier exploratory run with `n_fix = 12` and an unroll of 14 reached about the random level and was discarded,
as was a first version without the chirp.

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| `n_fix` of the module | 12 | `b3_warm_start.py` line 28 | M07's (Kim); freezing at 3 was measured with the trained candidate and did not help (comment, line 28) |
| `n_fix` of the model arm in training and in the evaluation | 3 | the rejected record, `n_fix_of_the_model_arm` | the freeze that shortened the unrolled run; the random arm used 12 |
| `form` | `point` | line 43 | the 3D traps need it |
| unroll | 10 iterations | the rejected record | DinHot's choice |

## Complexity and lane

Inference is $O(M)$ in the number of traps (up to 1024 padded); training is offline, local, never in CI. The module's `SPEC.lane` is `baked` because the warm start is refuted and no model is released.

## Acceptance criterion and gate

Ladder row: a measured negative; the criterion that was set, the median iterations to 1 percent at least two times below the random start with the final metrics within 1 percent and the model at most 1 MB, is not met, and
the claim is reported as refuted. Gate `tests/learned/test_b3_warm_start.py::test_measured_negative_the_two_times_criterion_is_not_met` (it runs while the slot is unreleased): it reads the rejected record and asserts that
the ratio of the medians of the iterations to 1 percent, random over model, matches the stored ratio and lies in $(1.5, 2.0)$; that the final efficiency differs by more than 1 percent; that the control without the network
supports the explanation (the random start with the same early freeze, `n_fix = 3`, needs at most the random start with `n_fix = 12` divided by 1.4, and the model arm with `n_fix = 3` needs at least as many as the random arm
with `n_fix = 3`); and that no `warmstart` model file exists in `models/`. `::test_released_model_meets_the_criterion` holds a released model to the original criterion if one is ever released.

## Evaluation that confirms or refutes it

The test that would have confirmed the hypothesis: a held-out set written before training, the median iterations to 1 percent with the model at most half of the random start's, the final efficiency and uniformity within
1 percent, a model of at most 1 MB and inference under 10 ms in the browser (the research record). It refutes it: the first two clauses fail, and the control shows the early phase freeze explains the gain.

## Measured result

Committed record `data/derived/models/warmstart-model-rejected.json` (M1 report, D3). Conditions: held-out file sha256 `bff5bee5cf62a827cf1d55bc87e4caf56117c35224e435152110b2b508079412` (in the data root, not in the repository), 66
geometries (60 generated demanding ones, with at least 40 traps and a random-start M07 needing more than 3 iterations on a selection seed of its own, and the benchmark geometries G1 to G6), seeds 301 to 303, iteration budget 60,
256-pixel grid for the oracle bound.

| Quantity | Model (`n_fix = 3`) | Random start (`n_fix = 12`) |
|---|---|---|
| Median iterations to 1 percent [q1, q3] | 8 [5, 61] | 14 [13, 15] |
| Ratio random over model | 1.75 (required 2) | |
| Final relative standard deviation, median (percent) | 0.294 | 0.0149 |
| Final efficiency, relative difference of the medians | 4.2 percent (required 1) | |
| Final uniformity, relative difference of the medians | 0.7 percent | |

Control without the network (30 of the geometries, seeds 301 to 303): median iterations [q3] random `n_fix = 12` 14 [15]; random `n_fix = 3` 9 [61]; model `n_fix = 3` 16.5 [61]. Share never reaching 1 percent: 6.7, 40 and 46.7
percent. The shorter freeze gives the fewer iterations where it converges, and the network adds nothing over a random start with the same `n_fix`.

Oracle bound (10 geometries, seed 301, 256 pixels): starting from the trap phases of a converged random-start M07 solution, `n_fix = 12` still needs 13 to 16 iterations on dense lattices; with `n_fix` 2 to 4 it needs 5 to 7 where the
random start needs 13 to 16. Parity of the ONNX graph with torch: maximum wrapped difference 9.8e-4 (the chirp argument is hundreds of radians in float32), not 1e-5.

The committed canonical bake has no B3 rows: its manifests flag "methods not registered in this build: B3" (for example `data/derived/manifests/C02_grid_feedback.json`), because that bake (I1 report) was run before the learned package was registered.

## Limits and failure modes

- Refuted as designed: the structure of M07 with `n_fix = 12` makes 1 percent arrive at about iteration 13 to 16 for dense arrays even from the phases of a converged solution (oracle bound), the freeze at `n_fix = 3` is what
  shortens the run, and the network does not learn start phases better than random in 6000 steps.
- The idea would need a start near a converged solution, which the trap list alone does not determine. A label-based model (regressing converged phases on lattices only) or a change of the M07 freeze rule would be a new design
  question, not tuning (M1 report). That is the proposal that remains open, and it is not claimed here.
- The framework card [B3](../../frameworks/B3_learned-warm-start.md) predates the model and says "pending".
- The metrics schema has no optional field for a rejected slot (`additionalProperties: false`), so the values live in the record only.

## References

- Ren et al. 2024, https://arxiv.org/abs/2401.06014
- Eybposh et al. 2020, Opt. Express 28, 26636, https://doi.org/10.1364/OE.399624
- Shi et al. 2021, Nature 591, https://doi.org/10.1038/s41586-020-03152-0 (abstract only read)
- Kim, Kim, Lee and Ahn 2019, Opt. Lett. 44, 3178, https://doi.org/10.1364/OL.44.003178
