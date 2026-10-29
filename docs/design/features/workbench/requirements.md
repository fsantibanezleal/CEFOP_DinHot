# Requirements: the App workbench: groups, lanes, the trap editor and Focus

EARS (Mavin et al., RE'09, doi:10.1109/RE.2009.9). Every requirement names the gate that fails when it is violated.
The App route is a case workbench on the shared shell (`CaseWorkbench`): five groups (Hologram, Focal plane, Traps, Convergence, Dynamics) and the
Context write-up, six peers, each group with sub-views V1 to V14 (`frontend/src/workbench/`). A reader picks a case and a method; every map shown carries its
lane, live (the TypeScript engine computed it in this browser) or replayed (the committed bake), and never the one for the other. The trap editor
(add, drag, delete) changes the case's target and re-runs the live methods; without the engine the edits are held and the card says the result is the baked
case. Focus mode (ADR-0070) opens the open group in the full viewport. The measured gate (`npm run gate`, local) holds the half-viewport rule (G6), the selection
key (G9) and Focus (G18). The shell's frame rules (the routes, the full width) are the feature `web`.

| ID | Requirement | Gate |
|---|---|---|
| WK-001 | IF an added or moved trap lies at or beyond the half field lambda f / (2 p) on either axis, THEN THE trap editor SHALL refuse it with the engine's message in both languages and leave the list unchanged. | `frontend/src/workbench/traps.test.ts::accepts a trap strictly inside and names the bound for one at or beyond it, in both languages` |
| WK-002 | THE trap editor SHALL never delete the last trap, because a target needs at least one. | `frontend/src/workbench/traps.test.ts::deletes a trap but never the last one (a target needs at least one trap)` |
| WK-003 | THE trap editor SHALL refuse a list longer than the 4096 traps the params record allows. | `frontend/src/workbench/traps.test.ts::refuses a list longer than the contract allows` |
| WK-004 | THE device view SHALL show the closed forms of the source: sinc^2(1/N) for the phase levels, the fill factor squared for the diffracted power and sinc^2(sqrt(f) / 2) for the aperture roll-off. | `frontend/src/workbench/decode.test.ts::the closed forms match the sources: sinc^2(1/N) gives 0.405 for N = 2 and 0.684 for N = 3, f^2 for the fill factor` |
| WK-005 | THE displayed phase of the Device effects view SHALL be the phase quantized to the nearest of 2^b levels, computed in the browser with the engine's order. | `frontend/src/workbench/decode.test.ts::quantizes to the nearest of 2^b levels and reports the level` |
| WK-006 | IF the run-length mask of a trace does not cover the focal crop, THEN THE decoder SHALL refuse it, never draw a shifted shape. | `frontend/src/workbench/decode.test.ts::expands a run-length mask, false first, and refuses a mask that does not cover the crop` |
| WK-007 | A result SHALL be labelled live only when the engine produced it and replay when the bake did. | `frontend/src/workbench/engine.test.ts::labels a result live only when the engine produced it, replay when the bake did` |
| WK-008 | A replayed map SHALL be labelled replayed from the bake, SHALL name the reference method whose maps they are, and SHALL never be labelled live. | `frontend/src/workbench/views.test.tsx::replayed maps are labelled replayed from the bake and name the reference method; they are never labelled live` |
| WK-009 | WHILE the live engine is not on the build, THE workbench SHALL hold trap edits and say the result is the baked case. | `frontend/src/workbench/views.test.tsx::trap edits without the live engine are held back and the result is said to be the baked case` |
| WK-010 | IF the index lists a case as refused, THEN every view SHALL show its reason, never an empty chart or a spinner. | `frontend/src/workbench/views.test.tsx::a refused case shows its reason in every view, never an empty chart` |
