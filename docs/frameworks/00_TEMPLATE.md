# Framework card, `<tool>` (TEMPLATE)

Copy to `docs/frameworks/<NN>_<tool>/<tool>.md` for **every** research-chosen engine/library. The deep research is
**binding**: each engine used by the pipeline gets a card here AND an exact pin in the matching requirements file
(`data-pipeline/requirements.txt`, `requirements-gpu.txt`, or `requirements-api.txt`). No toy substitute for a SOTA
engine the research prescribed.

## What & why
What it is; why it was chosen over the alternatives (cite the research).

## Install (exact, verified)
The exact version + install steps you verified; note OS constraints (e.g. Linux/WSL only). Pin it in the matching
`requirements-*.txt`.

## Usage
A minimal runnable snippet.

## Applying it here
Which module and stage use it, its inputs and outputs, and which contract it satisfies.

## Caveats / license
Numerical caveats, performance, and redistribution terms.
