# B3, Learned warm start for phase-fixed WGS (beyond the published state of the art)

| Item | Value |
|---|---|
| Family | beyond, learned |
| Lane | live inference in the browser (ONNX), then the live M07 run |
| Targets, dimensions | traps, 2D and 3D |
| Module | pending: the learned-methods package is in development and is not on this branch |
| Gap | no source initialises weighted GS with a network |
| Status | architecture and contract documented; measured values pending (see the end of this card) |

## Purpose

The random-phase start of weighted GS is already reliable, so the question is how many iterations a better start saves. A small permutation-invariant network predicts the initial phase of
every trap from the trap coordinates; the hologram is then initialised from those phases and phase-fixed WGS ([M07](M07_phase-fixed-wgs.md)) runs from there.

## The gap

Ren et al. 2024 (https://arxiv.org/abs/2401.06014 ) generate a full phase with a U-Net (0.16 s, about 10 percent site variation for about 20 traps); DeepCGH shows learned speedups for volumes
(https://doi.org/10.1364/OE.399624 ); a hologram network under 620 KB is possible (Shi et al. 2021, abstract only read). No source read uses a network to initialise WGS, and none compares with WGS.
A search found only GS-RNN style methods (a recurrent network inside the GS loop) for phase-only holograms.

## Method

A permutation-equivariant network (a set transformer or a small MLP over trap coordinates) predicts the $M$ initial trap phases $\theta_m$; the SLM phase is initialised as

$$\phi_j = \arg\sum_m e^{\,i(\Delta_j^m + \theta_m)}$$

(the SR form of [M02](M02_random-superposition.md) with learned $\theta_m$ instead of random ones), then phase-fixed WGS runs. Training is offline on random geometries, labelled by the converged
phase-fixed WGS trap phases (supervised, with a loss invariant to a global phase) or unsupervised through the point-trap model of [P01](P01_forward-models-and-metrics.md).

## DinHot's design (contract)

- Input: up to 1024 traps (x and y in focal bins over the half field, z in Rayleigh ranges, weight) with a mask; output: the trap phases in radians. Padded to 1024.
- Contract (catalog row `warmstart-model`, version 1.0.0): input `traps` float32 [1, 1024, 4] and `mask` float32 [1, 1024]; output `trap_phase` float32 [1, 1024] in radians; the baseline behind the slot
  is the random trap phases of the portable generator ([P07](P07_portable-rng.md)), the M02 start. At most 1 MB as an ONNX graph, operators supported by onnxruntime-web, single thread.
  See [the data contracts](../architecture/08_data-contracts.md).
- Evaluation on held-out geometries that the training never saw; the held-out set is written before training and its hash is recorded in the model card. Training is offline and local.

## Acceptance criterion and test

Median WGS iterations to a relative standard deviation of 1 percent at least two times below a random start on held-out geometries, final metrics equal within 1 percent, model at most 1 MB. The gate is the
test of the method ladder in the SDD (the file tests/methods/test_b3_warm_start.py in the ladder; it is created with the learned-methods package and does not exist on this branch yet). A model that does not meet
the criterion is not released.

## Measured values

Pending. The median iteration counts, the model size and the inference time are shown on the Benchmark page once the model is trained and released. No number is stated here before it is measured.

## Limits

- The random start is already reliable for WGS, so the gain may be small; the benchmark reports the measured result, positive or negative.
- Phase labels have a global phase and symmetries that the loss has to ignore.

## References

- Ren et al. 2024, https://arxiv.org/abs/2401.06014
- Eybposh et al. 2020, Opt. Express 28, 26636, https://doi.org/10.1364/OE.399624
- Kim et al. 2019, Opt. Lett. 44, 3178, https://doi.org/10.1364/OL.44.003178

## Pending

Training, export, held-out evaluation and the acceptance test of B3 (learned-methods work in progress); then this card and the Benchmark page take the measured values.
