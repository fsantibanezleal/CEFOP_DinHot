# U2b fragment, what is left for the main session (the SDD sections and the changelog line are merged)

## ATTRIBUTION.md (new lines; the file is outside the write scope of the unit that merged the SDD)

- Phase colormap: CET-C1 (`cyclic_mrybm_35_75_c68`) by Peter Kovesi, from `colorcet` 3.2.1, licence CC BY 4.0
  (https://creativecommons.org/licenses/by/4.0/); site https://colorcet.com ; paper: Kovesi, "Good Colour Maps: How to Design Them",
  arXiv:1509.03700. Used in `frontend/src/workbench/colormaps.ts` as a 256-entry 8-bit table. No change to the data.
- Intensity colormap: inferno by Nathaniel Smith and Stefan van der Walt (matplotlib 3.11.2, `_cm_listed.py`), licence CC0. Same file.

## Catalog (docs/contracts)

- Consumer tests: `frontend/src/lib/contract.test.ts` (case-index, case-manifest, trace, benchmark-results, model-metrics, cgh-net, warmstart-model,
  engine-reference, readiness), `frontend/src/readiness/readiness.test.ts`, `frontend/src/lib/api.contract.test.ts`. The bake root (`data/derived`)
  is checked when `manifests/index.json` exists.
- `readiness.schema.json` keeps the const `example.readiness/v1` (U3a open question 1); `SCHEMAS.readiness` follows it.
