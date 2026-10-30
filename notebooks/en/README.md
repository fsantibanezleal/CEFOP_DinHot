# Notebooks, English

The index of the English tree: eight topics, from the forward model of a hologram to the learned methods. Topics run from simple to
complex; inside a topic the reading order is the notebook number and the level never goes down. The Spanish counterpart of every
notebook is at the same path under [`../es/`](../es/README.md). How to run them is in [`../README.md`](../README.md).

Levels: 1 fundamentals, 2 the method in practice, 3 state of the art, 4 beyond the state of the art.

Each notebook is a worked lesson on one question: it states the question in its first cell, runs the product's methods step by step
on the cases of `data/examples/cases.json`, shows what it finds in figures, and answers the question in its Results with numbers it
computed ([`docs/guides/08_notebooks.md`](../../docs/guides/08_notebooks.md)). DinHot publishes no package of its own: the notebooks
import its pipeline modules by path, and the reference implementation of the level 3 notebooks is slmsuite 0.5.0.

## The three tiers in the notebooks

Every method of the product's ladder belongs to one tier ([`docs/guides/09_method-tiers.md`](../../docs/guides/09_method-tiers.md)),
and the notebooks cover the tiers like this:

- **Classical** methods are taught in the level 1 and level 2 notebooks of topics 01 to 03 and in the baselines of the later topics.
- **State of the art** methods are the level 3 notebooks: each names the ladder row it runs in its `caos.methods` metadata (M07 in
  03, M08 and M18 in 04, M10 and M11 in 05, M13 in 06, M12 and M16 in 07, M17 in 08).
- **Beyond the state of the art** are the level 4 notebooks, each named by the `BS-` claim it tests in `caos.beyond` (BS-1 in 03, BS-5
  in 05, BS-4 in 06, BS-2 in 07, BS-3 in 08, a measured negative).

## Topics

A topic without a level 3 notebook says why on its row.

| Topic | Needs | Level 3 |
|---|---|---|
| [01-fourier-optics](01-fourier-optics/) | none, this is the entry topic | No level 3: the topic teaches the forward model and the metrics, which are the engine itself and have no state-of-the-art method of their own |
| [02-analytic-holograms](02-analytic-holograms/) | topic 01-fourier-optics | No level 3: the one-step holograms are the classical baselines, and the state-of-the-art loops start in topic 03 |
| [03-gerchberg-saxton](03-gerchberg-saxton/) | topic 02-analytic-holograms | [03-phase-fixed-wgs-against-slmsuite](03-gerchberg-saxton/03-phase-fixed-wgs-against-slmsuite.ipynb) (M07) |
| [04-shaped-potentials](04-shaped-potentials/) | topic 03-gerchberg-saxton | [03-mraf-and-the-signal-region](04-shaped-potentials/03-mraf-and-the-signal-region.ipynb) (M08) and [04-optimal-transport-start](04-shaped-potentials/04-optimal-transport-start.ipynb) (M18) |
| [05-optimization](05-optimization/) | topic 03-gerchberg-saxton | 03 (M10) and 04 (M11) |
| [06-device-and-aberrations](06-device-and-aberrations/) | topic 05-optimization | 03 (M13) |
| [07-feedback-and-dynamics](07-feedback-and-dynamics/) | topic 03-gerchberg-saxton | 03 (M12) and 04 (M16) |
| [08-learned-holography](08-learned-holography/) | topics 01-fourier-optics and 03-gerchberg-saxton | [03-a-network-start-for-volume-holograms](08-learned-holography/03-a-network-start-for-volume-holograms.ipynb) (M17) |

## Notebooks

| Notebook | Level | The question it answers |
|---|---|---|
| [01-fourier-optics/01-where-the-light-goes.ipynb](01-fourier-optics/01-where-the-light-goes.ipynb) | 1 | where a phase pattern sends the light: focal bin and window, replicas outside it, the pixel envelope, phase levels and the zero order (case C01) |
| [01-fourier-optics/02-reading-a-trap-array.ipynb](01-fourier-optics/02-reading-a-trap-array.ipynb) | 2 | what efficiency, uniformity, relative spread and the power budget of a 10 by 10 array say, where they disagree and why the budget needs its radius (case C12) |
| [02-analytic-holograms/01-superposition-and-random-mask.ipynb](02-analytic-holograms/01-superposition-and-random-mask.ipynb) | 1 | what the three one-step holograms (superposition, random superposition, random mask) give on C12 and what limits each |
| [02-analytic-holograms/02-the-ten-by-ten-benchmark.ipynb](02-analytic-holograms/02-the-ten-by-ten-benchmark.ipynb) | 2 | how the three baselines compare with the published 10 by 10 table on five SLM sizes |
| [03-gerchberg-saxton/01-the-gs-loop.ipynb](03-gerchberg-saxton/01-the-gs-loop.ipynb) | 1 | the two halves of a Gerchberg-Saxton iteration done by hand on nine traps (case C01), checked against M04 |
| [03-gerchberg-saxton/02-weights-for-uniformity.ipynb](03-gerchberg-saxton/02-weights-for-uniformity.ipynb) | 2 | what weighted and adaptive GS gain over plain GS on C12: the first weights, iterations to 5, 2 and 1 percent, the alpha sweep, seed dependence |
| [03-gerchberg-saxton/03-phase-fixed-wgs-against-slmsuite.ipynb](03-gerchberg-saxton/03-phase-fixed-wgs-against-slmsuite.ipynb) | 3 | how M06 and M07 compare with slmsuite 0.5.0 WGS-Leonardo and WGS-Kim on the 1024 traps of C03 under one set of metrics |
| [03-gerchberg-saxton/04-device-aware-wgs.ipynb](03-gerchberg-saxton/04-device-aware-wgs.ipynb) | 4 | BS-1: whether device-aware WGS (B1) beats phase-fixed WGS and the crosstalk conjugate gradient on the device of case C08, and at which crosstalk strength |
| [04-shaped-potentials/01-what-a-shaped-potential-asks.ipynb](04-shaped-potentials/01-what-a-shaped-potential-asks.ipynb) | 1 | what a disc potential asks of the hologram that nine point traps do not, the error scored by hand, and where plain Gerchberg-Saxton stops on the disc of case C04 |
| [04-shaped-potentials/02-the-signal-and-the-noise-region.ipynb](04-shaped-potentials/02-the-signal-and-the-noise-region.ipynb) | 2 | how much of the focal plane a shaped hologram must give up to be accurate: hand-built signal regions, the power split, MRAF against plain Gerchberg-Saxton, the dark margin |
| [04-shaped-potentials/03-mraf-and-the-signal-region.ipynb](04-shaped-potentials/03-mraf-and-the-signal-region.ipynb) | 3 | how MRAF compares with GS on a disc and a ring, the mixing parameter, the start, and slmsuite's MRAF on the same targets |
| [04-shaped-potentials/04-optimal-transport-start.ipynb](04-shaped-potentials/04-optimal-transport-start.ipynb) | 3 | how M18 compares with slmsuite's MRAF on the C04 disc, with the same mixing and start, and what the optimal-transport start adds |
| [05-optimization/01-the-cost-and-its-gradient.ipynb](05-optimization/01-the-cost-and-its-gradient.ipynb) | 1 | the explicit cost of a trap array and its checked gradient, and a first conjugate-gradient descent against weighted GS on C12 |
| [05-optimization/02-the-wirtinger-gradient-and-adams-step.ipynb](05-optimization/02-the-wirtinger-gradient-and-adams-step.ipynb) | 2 | the Wirtinger pull-back through the ideal and crosstalk models, what Adam does to a gradient of unknown scale, the learning-rate sweep |
| [05-optimization/03-conjugate-gradient-against-weighted-gs.ipynb](05-optimization/03-conjugate-gradient-against-weighted-gs.ipynb) | 3 | how M10 compares with the classical loop M06: the refinement that lowers the cost and raises the spread, and the efficiency M10 returns exactly |
| [05-optimization/04-wirtinger-adam-against-gerchberg-saxton.ipynb](05-optimization/04-wirtinger-adam-against-gerchberg-saxton.ipynb) | 3 | how M11 compares with plain and weighted GS at equal iterations on three seeds and at 100 iterations |
| [05-optimization/05-the-efficiency-uniformity-front.ipynb](05-optimization/05-the-efficiency-uniformity-front.ipynb) | 4 | BS-5: the whole efficiency-uniformity front by continuation (B5) against six single-point methods on C12 |
| [06-device-and-aberrations/01-what-the-device-costs.ipynb](06-device-and-aberrations/01-what-the-device-costs.ipynb) | 1 | what the pixel aperture, quantization and crosstalk each cost the hologram of C08 |
| [06-device-and-aberrations/02-zernike-correction.ipynb](06-device-and-aberrations/02-zernike-correction.ipynb) | 2 | Zernike modes in Noll order, the Strehl estimate against the measured loss on C09, and the sensorless modal recovery of M14 |
| [06-device-and-aberrations/03-crosstalk-aware-cg-against-cg.ipynb](06-device-and-aberrations/03-crosstalk-aware-cg-against-cg.ipynb) | 3 | how M13 compares with M10 on the C08 device, the early stop of the line search, and M13 without a device |
| [06-device-and-aberrations/04-robust-holograms.ipynb](06-device-and-aberrations/04-robust-holograms.ipynb) | 4 | BS-4: B4 against phase-fixed WGS over 100 draws of residual aberration, and the measured negative on pointing errors |
| [07-feedback-and-dynamics/01-a-bead-in-the-computed-trap.ipynb](07-feedback-and-dynamics/01-a-bead-in-the-computed-trap.ipynb) | 1 | the focal intensity of C01 as a potential, a Langevin bead in it, its Lorentzian spectrum against the stiffness and its Boltzmann histogram |
| [07-feedback-and-dynamics/02-assigning-atoms-to-sites.ipynb](07-feedback-and-dynamics/02-assigning-atoms-to-sites.ipynb) | 2 | the Hungarian assignment of C10 for six exponents of the cost, crossings, and the plan M16 builds from it |
| [07-feedback-and-dynamics/03-closed-loop-feedback.ipynb](07-feedback-and-dynamics/03-closed-loop-feedback.ipynb) | 3 | how the Nogrette and Kim updates of M12 compare on the emulated camera of C02, against the open-loop M07 |
| [07-feedback-and-dynamics/04-moving-atoms-by-linear-phase-interpolation.ipynb](07-feedback-and-dynamics/04-moving-atoms-by-linear-phase-interpolation.ipynb) | 3 | how the sequence of holograms of M16 on the sort of C10 compares with independent holograms and a finer step |
| [07-feedback-and-dynamics/05-flicker-bounded-moves.ipynb](07-feedback-and-dynamics/05-flicker-bounded-moves.ipynb) | 4 | BS-2: B2 against LPI on its acceptance task, and the long moves of C10 where B2 needs the end phases |
| [08-learned-holography/01-what-a-network-sees-of-a-hologram.ipynb](08-learned-holography/01-what-a-network-sees-of-a-hologram.ipynb) | 1 | what goes into the released network and what comes out for one three-plane target, the accuracy it is scored by, and a flat and a random phase on the same scale (C05 optics) |
| [08-learned-holography/02-training-without-labels.ipynb](08-learned-holography/02-training-without-labels.ipynb) | 2 | how the network learns without example holograms: the loss by hand on fresh volumes, its smooth bowl around the network's phase, what it does not see on the traps, and the held-out record of 162 volumes |
| [08-learned-holography/03-a-network-start-for-volume-holograms.ipynb](08-learned-holography/03-a-network-start-for-volume-holograms.ipynb) | 3 | whether the released network beats the classical volumetric GS (M17 against M19) on the accuracy of the volume and on the traps' own numbers |
| [08-learned-holography/04-is-a-learned-warm-start-worth-it.ipynb](08-learned-holography/04-is-a-learned-warm-start-worth-it.ipynb) | 4 | BS-3: whether a network that predicts trap phases speeds phase-fixed WGS, or a freeze with no network explains the whole gain (a measured negative) |

## Beyond the state of the art

Five claims of the product's SDD, each with a level 4 notebook in both languages: BS-1 device-aware WGS (03-04), BS-2 flicker-bounded
sequences (07-05), BS-3 the learned warm start, tested and refuted (08-04), BS-4 the robust hologram (06-04) and BS-5 the
efficiency-uniformity front (05-05). Two of them, BS-3 and the pointing part of BS-4, are measured negatives and the notebooks say so.
