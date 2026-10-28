# M17, Unsupervised CNN hologram (DeepCGH-style)

| Item | Value |
|---|---|
| Family | learned |
| Lane | baked training, live inference in the browser (ONNX, WebAssembly, one thread) |
| Targets, dimensions | shaped and point targets on a focal crop, 2D |
| Module | pending: the learned-methods package is in development and is not on this branch |
| Anchor | Eybposh et al., Opt. Express 28, 26636 (2020) |
| Status | architecture and contract documented; measured values pending (see the end of this card) |

## Purpose

Replace the iteration by one forward pass: a small convolutional network maps a target amplitude to a phase hologram. After training,
a hologram costs one inference instead of tens of iterations, which is what matters when a target changes at interaction rate.

## Source method

DeepCGH (Eybposh et al. 2020, https://doi.org/10.1364/OE.399624 ): a CNN (a U-Net with 5 convolution blocks, image-plane holography
followed by propagation to the SLM), trained unsupervised with Adam, whose loss is a differentiable accuracy through the propagation model. Their 3D targets are $m\times m$ pixels with $p$ planes,
with a separate model per resolution and plane set; at 1035 nm, $f$ = 200 mm and a pixel of 9.2 um they report at least 10 times faster than GS and 9 to 43 percent more accurate than
GS (up to 3500 iterations for each iterative method, 1000 test samples). The paper reports the comparison on volume targets; no source read compares a learned method against WGS on the
uniformity of hundreds of point traps. A supervised variant for tweezers (Ren et al. 2024, https://arxiv.org/abs/2401.06014 ) reports 0.16 s per hologram against about 6 s for GS and about
10 percent trap-depth variation on about 20 sites, far from the 1 to 4 percent of WGS with feedback.

## DinHot's design (contract and training protocol)

- Input: the target amplitude on a $128\times128$ focal crop, normalised to unit energy; output: the phase on the SLM grid of 128 pixels at training time, in radians.
- Loss: unsupervised, a normalised intensity error (or the negative accuracy) through a differentiable Fourier model in the training framework. That forward model is re-implemented
  there and checked against the numpy engine of [P01](P01_forward-models-and-metrics.md) in a test.
- Training targets: random point-trap sets and shaped targets from a seeded generator. Held-out: geometries drawn with a different seed, and the benchmark geometries at that size; the held-out set
  is written before training and its hash is recorded in the model card.
- Network: a small U-Net sized for at most 5 MB as an ONNX graph, using only operators the WebAssembly provider of onnxruntime-web supports; inference in the browser with a single thread
  (GitHub Pages sends no cross-origin isolation headers, so no shared memory).
- Training runs locally on the GPU, never in CI, never in the browser (ADR-0069, ADR-0074). The released files are the model and its card; datasets and checkpoints stay in the data root.
- Contract (catalog row `cgh-net`, version 1.0.0): input `target` float32 of shape [1, 1, 128, 128]; output `phase` float32 of shape [1, 1, 128, 128] in radians; the baseline behind
  the slot is GS ([M04](M04_gerchberg-saxton.md)) at 30 iterations. If no valid released model exists, the baseline answers and the views label the result with the model that produced it.
  See [the data contracts](../architecture/08_data-contracts.md).

## Equations

The loss is the intensity error of the Fourier model of [P01](P01_forward-models-and-metrics.md), written for the phase output $\phi$:

$$\mathcal{L}(\phi) = \frac{\sum_{nm}\big(T_{nm} - |\mathcal{F}[A\,e^{i\phi}]_{nm}|^2\big)^2}{\sum_{nm}T_{nm}^2}$$

with $T$ the normalised target intensity. This is the general form of the unsupervised objective of the source; the exact accuracy metric of the paper is not reproduced here.

## Acceptance criterion and test

On held-out targets, accuracy above GS at the same wall-clock budget. The gate is a test of the learned methods named in the method ladder of the SDD (the file
tests/methods/test_m17_cgh_net.py in the ladder; it is created with the learned-methods package and does not exist on this branch yet). A model that does not meet the criterion is not released: the baseline answers, readiness says
training, and the measured values are reported as they are.

## Measured values

Pending. The measured values of the released model on the held-out set (accuracy against GS at equal wall clock, model size, inference time) are shown on the Benchmark page once the model is
trained and released. No number is stated here before it is measured.

## Limits

- DeepCGH trains a separate model per resolution and target set; the released model is specific to its crop size.
- No published controlled comparison against WGS on trap-array uniformity exists; the benchmark protocol is DinHot's own.

## References

- Eybposh et al. 2020, Opt. Express 28, 26636, https://doi.org/10.1364/OE.399624
- Ren et al. 2024, https://arxiv.org/abs/2401.06014
- Shi et al. 2021, Nature 591, https://doi.org/10.1038/s41586-020-03152-0 (the size of a hologram network; abstract only read)

## Pending

Training, export, held-out evaluation and the acceptance test of M17 (learned-methods work in progress); then this card and the Benchmark page take the measured values.
