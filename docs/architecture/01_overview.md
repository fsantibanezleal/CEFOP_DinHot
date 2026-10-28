# Architecture, overview

This repository is an instance of the CAOS product archetype (ADR-0057): the science runs offline, its results are
committed, and a static web workbench replays them and re-runs what is light enough, live. The base (the layout,
the two contracts, the stage names, the lanes, the guards, the shared shell) is carried by the template and the
shell; a product reworks the core: the methods, the cases, the views and the content.

## The lanes

| Lane | Where | What runs |
|---|---|---|
| Offline | `data-pipeline/`, in `.venv-pipeline` | the staged pipeline; it bakes and checks every case |
| Replay | `data/derived/`, copied into the site | the committed artifacts, read as they are |
| Live | `frontend/src/engine/` | a TypeScript port of the engine, re-run with the reader's values, held to the baked traces by a parity test |
| API | `app/` | dormant; a read-only layer over `data/derived`, activated only when a product needs a server |

The [lane gate](03_the-gate.md) decides, by measurement, which cases are light enough to re-run live.

## The flow

Raw inputs, then [contract 1](08_data-contracts.md) (`io/contract.py`), then the named stages (preprocess,
feature extraction, train, infer, evaluate, export) with every result checked against its case's expected ranges,
then [contract 2](08_data-contracts.md) (index, manifests, traces) into `data/derived/`, committed. The web copies
exactly the declared artifacts, reads them as JSON, and re-runs the live engine on them.

## What holds it

The pipeline tests run in a sandbox that fails the session if a committed artifact changes. The web's contract
test reads every committed artifact against the web's declaration in both directions; the parity test holds the
live engine to the bakes; the measured gate walks the built site at five sizes, in both themes and both languages.
The design (`docs/design/SDD.md`) names the gate of every requirement, and `scripts/check_sdd.py` checks that each
named gate exists.
