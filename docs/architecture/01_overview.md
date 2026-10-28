# Architecture, overview

DinHot is a holography studio for optical trap arrays and shaped light fields that runs in the browser. A reader picks a case (a trap geometry or a target potential on a stated optical setup and a
stated phase-only SLM), computes the phase hologram with any of 24 methods, and sees where the light goes, how uniform and efficient the traps are, what the device and the aberrations cost, what a camera
feedback loop recovers and what a trapped bead or atom does in the computed potential. The design, with every requirement and its gate, is [`design/SDD.md`](../design/SDD.md).

The repository is an instance of the CAOS product archetype (ADR-0057): the science runs offline, its results are committed, and a static web workbench replays them and re-runs what is light enough, live.
The base (the layout, the contracts, the stage names, the lanes, the guards and the shared shell) is carried by the template and the shell; the core is DinHot's: the engine, the methods, the cases and the views.

## What DinHot is, and what it is not

| It is | It is not |
|---|---|
| A simulator and evaluator of phase holograms for trap arrays and shaped potentials, with 24 methods run side by side on the same task, seeds and metrics | A driver for hardware: it never talks to an SLM or a camera |
| A scalar Fourier-optics engine (Fraunhofer and angular spectrum) with a device model | A vectorial high-NA focusing model; the high-NA case carries a validity flag |
| A camera-in-the-loop emulator whose errors are stated parameters | A calibrated digital twin of one laboratory; absolute numbers are those of the stated model |
| A static site: every computation runs in the browser or was baked offline and is replayed | A server: no backend at request time |
| A trap-array and trapping-potential tool | A display-holography tool (near-eye or 3D displays) |

## The lanes

| Lane | Where | What runs |
|---|---|---|
| Offline | `data-pipeline/`, in `.venv-pipeline` | the staged pipeline bakes and checks the twelve cases and runs the benchmark protocol; training of the two learned models runs locally on the GPU, never in CI |
| Replay | `data/derived/`, copied into the site | the committed artifacts (index, manifests, traces, benchmark results, model cards and metrics), read as they are |
| Live | the TypeScript engine of the frontend | the live methods re-run with the reader's values in a Web Worker, held to the Python engine by parity tests |
| API | `app/` | dormant: a read-only layer over `data/derived`, answering 503 with the declared state while nothing is baked |

<p align="center"><img src="../assets/lanes.svg" alt="The offline, replay and live lanes and the dormant API" width="760"></p>

The [lane gate](03_the-gate.md) decides, by measurement, which cases and methods are light enough to re-run live.

## The physics chain

Every method works inside the same chain. A method produces a phase mask; the device model turns it into the phase the SLM really shows; the lens (a Fourier transform) gives the focal field; the metrics score the
traps; the trap physics and the particle dynamics turn the intensity into stiffness and motion. The components are the framework cards P01 to P06 of [frameworks](../frameworks.md).

<p align="center"><img src="../assets/forward-model.svg" alt="Phase mask, device, lens, metrics, particle" width="760"></p>

## The flow

Source cases (`data/examples/cases.json`, written from the case library) enter through [contract 1](08_data-contracts.md), the params-record gate in `data-pipeline/pipeline/io/contract.py`. The named stages then run
([the staged pipeline](05_precompute-pipeline.md)): preprocess, feature extraction, train, infer, evaluate and export, with every result checked against its case's expected ranges, the lane gate and the units gate.
[Contract 2](08_data-contracts.md) (index, manifests, traces) lands in `data/derived/`, committed. The web copies exactly the declared artifacts, reads them as JSON and re-runs the live engine on them.

## The method interface

A method is a module with a `SPEC` and a `run` function; the registry discovers it. The same interface serves the bake, the benchmark and the TypeScript port
([method interface and registry](09_method-interface-and-registry.md)).

## What holds it

The pipeline tests run in a sandbox that fails the session if a committed artifact changes. The web's contract test reads every committed artifact against the web's declaration in both directions; the parity
test holds the live engine to fixtures that the Python engine writes; the measured gate walks the built site at five sizes, in both themes and both languages. The design names the gate of every requirement,
and `scripts/check_sdd.py` checks that each named gate exists. The oracles (Parseval, the FFT and point-trap agreement, the published rows of the calibration case, the physics limits, the Lorentzian corner
frequency of a simulated bead) are independent of the engine; none is a model judging a model.
