# U2b fragment (for the main session to merge into the SDD, ATTRIBUTION.md, package.json, the catalog and the changelog)

## ATTRIBUTION.md (new lines)

- Phase colormap: CET-C1 (`cyclic_mrybm_35_75_c68`) by Peter Kovesi, from `colorcet` 3.2.1, licence CC BY 4.0
  (https://creativecommons.org/licenses/by/4.0/); site https://colorcet.com ; paper: Kovesi, "Good Colour Maps: How to Design Them",
  arXiv:1509.03700. Used in `frontend/src/workbench/colormaps.ts` as a 256-entry 8-bit table. No change to the data.
- Intensity colormap: inferno by Nathaniel Smith and Stefan van der Walt (matplotlib 3.11.2, `_cm_listed.py`), licence CC0. Same file.

## package.json

No dependency added. The unit uses the ones already pinned: `onnxruntime-web` 1.31.1 (its WASM binary is bundled by Vite from the package,
`import 'onnxruntime-web/ort-wasm-simd-threaded.wasm?url'`, so it is the same release as the JavaScript and is served from the site, no CDN;
one thread, no proxy worker, because GitHub Pages sends no COOP or COEP), `three` 0.186.1 (lazy chunk, the 3D lobes only), `uplot` through the
shell's charts, `fft.js` (unused by this unit).

## SDD changes

- Section "App" (groups): five groups plus the Context write-up, six peers (the shell's maximum, `MAX_WORKBENCH_GROUPS`, counts the Context tab).
  The brief's sixth group, Aberrations (V8), is the third sub-view of Hologram. Hologram: Phase mask (V1), Device effects (V7), Aberrations (V8).
  Focal plane: Focal plane (V2, with the trap editor), Axial cut (V5), 3D lobes (V6, three-dimensional cases only). Traps: Per-trap intensity
  (V3), Depth (V13), Power budget (V14). Convergence: Metrics by iteration (V4), Pareto front (B5), Camera feedback (V9). Dynamics: Trapped
  particle (V10), Spectrum (V11), Rearrangement (V12).
- Section "Lanes": a method is live when the engine client's `liveMethods()` lists it, else replayed from the trace. The trace carries the
  hologram and focal maps of the reference method only; for another method the maps stay the reference's (the card says so) and the metrics,
  history and per-trap intensities are the selected method's. Trap edits and the device and iteration controls re-run live methods; without the
  engine they are held and the card says the result is the baked case.
- Section "Learned models": M17 (cgh-net) answers in the browser only on 128 x 128 cases with a released model; its phase is shown and its focal
  plane needs the engine. Without a model its baseline, GS (M04) at 30 iterations, answers. B3 (warmstart-model) hands M07 its trap phases
  (`trapPhases`); without a model the engine's own random start answers. The readiness document decides first: a slot it lists as training with
  the baseline is not fetched (no 404 in the console).
- Section "Views": V6 is a model of each trap's focus (Gaussian envelope: lateral FWHM 0.51 lambda / NA, axial FWHM two Rayleigh ranges
  n lambda / (pi NA^2), scaled by the trap's intensity), not the computed field; overlaps are counted at true size and the drawing may be magnified,
  which the card states. V5 shows the baked xz cut of one trap (the trace carries no yz cut); the lateral profiles in V2 stand in for it.
- Section "Device": the displayed phase is computed in the browser from the baked phase with the engine's own order and kernel (quantize,
  response curve, separable crosstalk blur at pixel centres, `decode.ts`); the closed forms of the device effects are sinc^2(1/N) (Moreno et al.
  Eq. 6), the fill factor squared (arXiv:1512.06241) and the pixel-aperture roll-off sinc^2(sqrt(f) / 2) (`device.py`).
- Test paths: `frontend/src/workbench/*.test.ts(x)`, `frontend/src/lib/{contract,api.contract,declared,ort}.test.ts`,
  `frontend/src/readiness/readiness.test.ts`.

## Catalog (docs/contracts, not in this unit's scope)

- Consumer tests: `frontend/src/lib/contract.test.ts` (case-index, case-manifest, trace, benchmark-results, model-metrics, cgh-net,
  warmstart-model, engine-reference, readiness), `frontend/src/readiness/readiness.test.ts`, `frontend/src/lib/api.contract.test.ts`. The bake
  root (`data/derived`) is checked when `manifests/index.json` exists and is a skipped suite until then; the provider tree carries the same
  assertions today.
- Open question for M1: the encodings of the two graphs are written from the catalog row (cgh-net: target amplitude sqrt(weight) at the trap pixels
  of the 128 crop, centre at index 64, unit energy; warmstart-model: x and y over the half field, z in Rayleigh ranges n lambda / (pi NA^2),
  weight, padded to 1024). The model cards of M1 must fix them; `ort.ts` `encodeCghTarget` and `encodeWarmstart` change with them.
- `readiness.schema.json` keeps the const `example.readiness/v1` (U3a open question 1); `SCHEMAS.readiness` follows it.

## Site files (frontend/scripts/copy-data.mjs)

`public/data/` now also carries `benchmark/results.json` and `models/metrics.json` (required, unless the readiness row is `missing`), and, when
`models/cgh-net.json` or `models/warmstart.json` exist at the repository root, the card and the graph it names (stopping the build when the graph
is absent or its size or sha256 is not the card's). `scripts/declared.mjs` reads the index's `path` and skips refused cases.

## Changelog

- App: the workbench of DinHot (five groups and Context, a trap editor, the live and replay lanes with their labels, Focus mode, the two learned
  models in the browser with their baselines), minimal pages for Experiments, Benchmark and Implementation that U6 to U8 fill, and the removal of
  the template's SIR example (`frontend/src/engine/sir.ts` and its parity test).
