# The live lane

The live lane re-runs a case in the reader's browser with the reader's values: the parameters in the rail and the
chosen variant. It is a TypeScript port of the pipeline's engine, `frontend/src/engine/sir.ts`, written step for
step (the same scheme, the same step, the same order of operations, the same clamps).

## What holds it to the pipeline

`frontend/src/engine/sir.parity.test.ts` runs the live engine on the parameters of every baked case and compares it
with the committed trace at the trace's 200 points, to the trace's rounding (0.005 people), summary included (peak,
peak day, attack rate). A change to either engine that is not made to the other fails the web's tests. The same
file checks that the engine converges to the final-size relation at first order in the step, which is the scheme's
claim on the Methodology page.

## What runs where

- The live engine computes only what the reader changes: a case's trajectory with other rates, a variant (a share
  immunised at the start), a sweep over R0 for the final-size view. Everything baked stays baked.
- Every view shows its lane: live (computed in the browser) or replay (read from an artifact). A view still showing
  an earlier selection is overlaid as recomputing, through the selection key.
- A product whose engine cannot be ported keeps only the replay lane and declares its workbench `replayOnly`; the
  gate then does not expect controls to change the views.
