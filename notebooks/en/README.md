# Notebooks, English

The index of the English tree: eight topics, from the forward model of a hologram to the learned methods. Topics run from simple to
complex; inside a topic the reading order is the notebook number and the level never goes down. The Spanish counterpart of every
notebook is at the same path under [`../es/`](../es/README.md). How to run them is in [`../README.md`](../README.md).

Levels: 1 fundamentals, 2 the method in practice, 3 comparison with published methods, 4 proposed methods.

Each notebook is a worked lesson on one question: it states the question in its first cell, runs the product's methods step by step
on the cases of `data/examples/cases.json`, shows what it finds in figures, and answers the question in its Results with numbers it
computed ([`docs/guides/08_notebooks.md`](../../docs/guides/08_notebooks.md)). DinHot publishes no package of its own: the notebooks
import its pipeline modules by path, and the reference implementation of the level 3 notebooks is slmsuite 0.5.0.

## How the notebooks cover the methods

Every method of the product's ladder is named in the notebooks by its name ([`docs/guides/09_method-tiers.md`](../../docs/guides/09_method-tiers.md)),
and the notebooks cover the methods like this:

- The baselines (plain Gerchberg-Saxton, the weighted loop) are taught in the level 1 and level 2 notebooks of topics 01 to 03 and in the baselines of the later topics.
- The published methods are the level 3 notebooks, a comparison with the method as published or as slmsuite implements it: each names the method it runs in its `caos.methods` metadata (phase-fixed weighted GS in
  03, MRAF and optimal-transport MRAF in 04, conjugate gradient and Wirtinger gradient with Adam in 05, device-aware CG in 06, closed-loop WGS and Hungarian rearrangement in 07, unsupervised CNN in 08).
- The proposed methods are the level 4 notebooks, each named by the claim it tests in `caos.beyond` (device-aware WGS in 03, efficiency-uniformity front
  in 05, aberration-robust hologram in 06, flicker-bounded sequence in 07, learned warm start in 08, a measured negative).

## Coverage of the whole tool

[`../coverage.json`](../coverage.json) maps every part of the tool to the notebooks that teach it: each method of the SDD's ladder
(covered only by a notebook of level 2 or above), each data contract of `docs/contracts/catalog.md`, each pipeline stage of
`data-pipeline/pipeline/stages/` and each method package (the product declares none). The paths are relative to a language tree and
exist in both. Every notebook of level 2 or above has a third-level section on where its method changes or breaks and one on using
it on your own data, and the notebooks of topics 01 and 02 also read the committed documents of the contracts they explain. The
check is `tools/notebooks/check_notebook_depth.py` of CAOS_MANAGE. Every method of the ladder, every contract and every stage has a notebook in the map; a part that
later has none would be listed by the check.

## Topics

A topic without a level 3 notebook says why on its row.

| Topic | Needs | Level 3 |
|---|---|---|
| [01-fourier-optics](01-fourier-optics/) | none, this is the entry topic | No level 3: the topic teaches the forward model and the metrics, which are the engine itself and have no published method of their own |
| [02-analytic-holograms](02-analytic-holograms/) | topic 01-fourier-optics | No level 3: the one-step holograms are the baselines, and the published loops start in topic 03 |
| [03-gerchberg-saxton](03-gerchberg-saxton/) | topic 02-analytic-holograms | [03-phase-fixed-wgs-against-slmsuite](03-gerchberg-saxton/03-phase-fixed-wgs-against-slmsuite.ipynb) |
| [04-shaped-potentials](04-shaped-potentials/) | topic 03-gerchberg-saxton | [03-mraf-and-the-signal-region](04-shaped-potentials/03-mraf-and-the-signal-region.ipynb) and [04-optimal-transport-start](04-shaped-potentials/04-optimal-transport-start.ipynb) |
| [05-optimization](05-optimization/) | topic 03-gerchberg-saxton | 03 and 04 |
| [06-device-and-aberrations](06-device-and-aberrations/) | topic 05-optimization | 03 |
| [07-feedback-and-dynamics](07-feedback-and-dynamics/) | topic 03-gerchberg-saxton | 03 and 04 |
| [08-learned-holography](08-learned-holography/) | topics 01-fourier-optics and 03-gerchberg-saxton | [03-a-network-start-for-volume-holograms](08-learned-holography/03-a-network-start-for-volume-holograms.ipynb) |

## Notebooks

| Notebook | Level | The question it answers |
|---|---|---|
| [01-fourier-optics/01-where-the-light-goes.ipynb](01-fourier-optics/01-where-the-light-goes.ipynb) | 1 | where a phase pattern sends the light: focal bin and window, replicas outside it, the pixel envelope, phase levels and the zero order (case C01) |
| [01-fourier-optics/02-reading-a-trap-array.ipynb](01-fourier-optics/02-reading-a-trap-array.ipynb) | 2 | what efficiency, uniformity, relative spread and the power budget of a 10 by 10 array say, where they disagree and why the budget needs its radius (case C12) |
| [01-fourier-optics/03-engine-reference-and-readiness.ipynb](01-fourier-optics/03-engine-reference-and-readiness.ipynb) | 2 | how the browser engine is held to the Python engine by the engine-reference documents, how to read the readiness document and the API contract, and how to write a reference for a function of your own |
| [02-analytic-holograms/01-superposition-and-random-mask.ipynb](02-analytic-holograms/01-superposition-and-random-mask.ipynb) | 1 | what the three one-step holograms (superposition, random superposition, random mask) give on C12 and what limits each |
| [02-analytic-holograms/02-the-ten-by-ten-benchmark.ipynb](02-analytic-holograms/02-the-ten-by-ten-benchmark.ipynb) | 2 | how the three baselines compare with the published 10 by 10 table on five SLM sizes |
| [02-analytic-holograms/03-laguerre-gaussian-vortex-traps.ipynb](02-analytic-holograms/03-laguerre-gaussian-vortex-traps.ipynb) | 2 | how one added term in the delay makes a ring with a dark centre: the winding of the phase, the radius of the ring, the angular momentum per photon, the array of case C06 and the charge at which the check of the product aliases |
| [03-gerchberg-saxton/01-the-gs-loop.ipynb](03-gerchberg-saxton/01-the-gs-loop.ipynb) | 1 | the two halves of a Gerchberg-Saxton iteration done by hand on nine traps (case C01), checked against Gerchberg-Saxton |
| [03-gerchberg-saxton/02-weights-for-uniformity.ipynb](03-gerchberg-saxton/02-weights-for-uniformity.ipynb) | 2 | what weighted and adaptive GS gain over plain GS on C12: the first weights, iterations to 5, 2 and 1 percent, the alpha sweep, seed dependence |
| [03-gerchberg-saxton/03-phase-fixed-wgs-against-slmsuite.ipynb](03-gerchberg-saxton/03-phase-fixed-wgs-against-slmsuite.ipynb) | 3 | how weighted GS and phase-fixed weighted GS compare with slmsuite 0.5.0 WGS-Leonardo and WGS-Kim on the 1024 traps of C03 under one set of metrics |
| [03-gerchberg-saxton/04-device-aware-wgs.ipynb](03-gerchberg-saxton/04-device-aware-wgs.ipynb) | 4 | whether device-aware WGS beats phase-fixed WGS and the crosstalk conjugate gradient on the device of case C08, and at which crosstalk strength |
| [04-shaped-potentials/01-what-a-shaped-potential-asks.ipynb](04-shaped-potentials/01-what-a-shaped-potential-asks.ipynb) | 1 | what a disc potential asks of the hologram that nine point traps do not, the error scored by hand, and where plain Gerchberg-Saxton stops on the disc of case C04 |
| [04-shaped-potentials/02-the-signal-and-the-noise-region.ipynb](04-shaped-potentials/02-the-signal-and-the-noise-region.ipynb) | 2 | how much of the focal plane a shaped hologram must give up to be accurate: hand-built signal regions, the power split, MRAF against plain Gerchberg-Saxton, the dark margin |
| [04-shaped-potentials/03-mraf-and-the-signal-region.ipynb](04-shaped-potentials/03-mraf-and-the-signal-region.ipynb) | 3 | how MRAF compares with GS on a disc and a ring, the mixing parameter, the start, and slmsuite's MRAF on the same targets |
| [04-shaped-potentials/04-optimal-transport-start.ipynb](04-shaped-potentials/04-optimal-transport-start.ipynb) | 3 | how optimal-transport MRAF compares with slmsuite's MRAF on the C04 disc, with the same mixing and start, and what the optimal-transport start adds |
| [05-optimization/01-the-cost-and-its-gradient.ipynb](05-optimization/01-the-cost-and-its-gradient.ipynb) | 1 | the explicit cost of a trap array and its checked gradient, and a first conjugate-gradient descent against weighted GS on C12 |
| [05-optimization/02-the-wirtinger-gradient-and-adams-step.ipynb](05-optimization/02-the-wirtinger-gradient-and-adams-step.ipynb) | 2 | the Wirtinger pull-back through the ideal and crosstalk models, what Adam does to a gradient of unknown scale, the learning-rate sweep |
| [05-optimization/03-conjugate-gradient-against-weighted-gs.ipynb](05-optimization/03-conjugate-gradient-against-weighted-gs.ipynb) | 3 | how conjugate gradient compares with the weighted GS loop: the refinement that lowers the cost and raises the spread, and the efficiency that conjugate gradient returns exactly |
| [05-optimization/04-wirtinger-adam-against-gerchberg-saxton.ipynb](05-optimization/04-wirtinger-adam-against-gerchberg-saxton.ipynb) | 3 | how Wirtinger gradient with Adam compares with plain and weighted GS at equal iterations on three seeds and at 100 iterations |
| [05-optimization/05-the-efficiency-uniformity-front.ipynb](05-optimization/05-the-efficiency-uniformity-front.ipynb) | 4 | the whole efficiency-uniformity front by continuation against six single-point methods on C12 |
| [06-device-and-aberrations/01-what-the-device-costs.ipynb](06-device-and-aberrations/01-what-the-device-costs.ipynb) | 1 | what the pixel aperture, quantization and crosstalk each cost the hologram of C08 |
| [06-device-and-aberrations/02-zernike-correction.ipynb](06-device-and-aberrations/02-zernike-correction.ipynb) | 2 | Zernike modes in Noll order, the Strehl estimate against the measured loss on C09, and the sensorless modal recovery of the Zernike correction |
| [06-device-and-aberrations/03-crosstalk-aware-cg-against-cg.ipynb](06-device-and-aberrations/03-crosstalk-aware-cg-against-cg.ipynb) | 3 | how device-aware CG compares with conjugate gradient on the C08 device, the early stop of the line search, and device-aware CG without a device |
| [06-device-and-aberrations/04-robust-holograms.ipynb](06-device-and-aberrations/04-robust-holograms.ipynb) | 4 | the aberration-robust hologram against phase-fixed WGS over 100 draws of residual aberration, and the measured negative on pointing errors |
| [07-feedback-and-dynamics/01-a-bead-in-the-computed-trap.ipynb](07-feedback-and-dynamics/01-a-bead-in-the-computed-trap.ipynb) | 1 | the focal intensity of C01 as a potential, a Langevin bead in it, its Lorentzian spectrum against the stiffness and its Boltzmann histogram |
| [07-feedback-and-dynamics/02-assigning-atoms-to-sites.ipynb](07-feedback-and-dynamics/02-assigning-atoms-to-sites.ipynb) | 2 | the Hungarian assignment of C10 for six exponents of the cost, crossings, and the plan that the Hungarian rearrangement method builds from it |
| [07-feedback-and-dynamics/03-closed-loop-feedback.ipynb](07-feedback-and-dynamics/03-closed-loop-feedback.ipynb) | 3 | how the Nogrette update of the closed-loop WGS method (DinHot's cumulative reading of its Eq. 3, with the literal rule run beside it) and the Kim update compare on the emulated camera of C02, against the open-loop phase-fixed weighted GS |
| [07-feedback-and-dynamics/04-moving-atoms-by-linear-phase-interpolation.ipynb](07-feedback-and-dynamics/04-moving-atoms-by-linear-phase-interpolation.ipynb) | 3 | how the sequence of holograms of the Hungarian rearrangement method on the sort of C10 compares with independent holograms and a finer step |
| [07-feedback-and-dynamics/05-flicker-bounded-moves.ipynb](07-feedback-and-dynamics/05-flicker-bounded-moves.ipynb) | 4 | the flicker-bounded sequence against LPI on its acceptance task, and the long moves of C10 where it needs the end phases |
| [08-learned-holography/01-what-a-network-sees-of-a-hologram.ipynb](08-learned-holography/01-what-a-network-sees-of-a-hologram.ipynb) | 1 | what goes into the released network and what comes out for one three-plane target, the accuracy it is scored by, and a flat and a random phase on the same scale (C05 optics) |
| [08-learned-holography/02-training-without-labels.ipynb](08-learned-holography/02-training-without-labels.ipynb) | 2 | how the network learns without example holograms: the loss by hand on fresh volumes, its smooth bowl around the network's phase, what it does not see on the traps, and the held-out record of 162 volumes |
| [08-learned-holography/03-a-network-start-for-volume-holograms.ipynb](08-learned-holography/03-a-network-start-for-volume-holograms.ipynb) | 3 | whether the released network beats the volumetric GS (Unsupervised CNN against multi-plane GS) on the accuracy of the volume (per plane and in the cosine form of the paper) and on the traps' own numbers |
| [08-learned-holography/04-is-a-learned-warm-start-worth-it.ipynb](08-learned-holography/04-is-a-learned-warm-start-worth-it.ipynb) | 4 | whether a network that predicts trap phases speeds phase-fixed WGS, or a freeze with no network explains the whole gain (a measured negative) |

## Proposed methods

Five claims of the product's SDD, each with a level 4 notebook in both languages: device-aware WGS (03-04), the flicker-bounded
sequence (07-05), the learned warm start, tested and refuted (08-04), the aberration-robust hologram (06-04) and the
efficiency-uniformity front (05-05). Two of them, the learned warm start and the pointing part of the aberration-robust hologram, are measured negatives and the notebooks say so.
