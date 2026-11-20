# DinHot

[![CI](https://img.shields.io/github/actions/workflow/status/fsantibanezleal/CEFOP_DinHot/ci.yml?branch=main&label=CI)](https://github.com/fsantibanezleal/CEFOP_DinHot/actions)
[![License](https://img.shields.io/github/license/fsantibanezleal/CEFOP_DinHot)](LICENSE)
[![Version](https://img.shields.io/github/v/tag/fsantibanezleal/CEFOP_DinHot?label=version&sort=semver)](https://github.com/fsantibanezleal/CEFOP_DinHot/tags)
[![Live](https://img.shields.io/badge/site-live-2ea44f)](https://dinhot.fasl-work.com)

Holographic optical trap arrays computed, corrected and tested in the browser

*Arreglos de trampas opticas holograficas calculados, corregidos y probados en el navegador*

Live site: https://dinhot.fasl-work.com. DinHot is a holography studio for optical trap arrays and shaped light fields. A reader picks
one of fourteen cases (a trap geometry or a target potential, on a stated optical setup and phase-only SLM), computes the phase
hologram with any of 24 methods, and sees where the light goes, how uniform and efficient the traps are, what the device and the
aberrations cost, what a camera feedback loop recovers and what a trapped bead or atom does in the computed potential. It was born at
CEFOP (Universidad de Concepcion) as DinHotSys, a C++ desktop tool, and is rebuilt here on the CAOS product template and shell. The
design is [docs/design/SDD.md](docs/design/SDD.md).

## The methods

Every method runs on the product's cases with the same seeds and metrics, and is compared with the others on the Benchmark page:

- **Published methods** (19), replicated or implemented here: the superposition of prisms and lenses, Gerchberg-Saxton, weighted GS,
  the volumetric 3D GS, phase-fixed weighted GS, MRAF, optimal-transport starts, conjugate gradient and Wirtinger-Adam descent with a
  device model, closed-loop feedback, atom rearrangement and the learned multi-plane network. The level 3 notebooks run them against
  slmsuite 0.5.0 or against each other.
- **Proposed methods** (5): device-aware conjugate-gradient refinement, flicker-bounded phase-continuous sequences, a learned warm start, an
  aberration-robust hologram and an efficiency-uniformity continuation, each tested and reported as it came out, with its mixed and negative
  results. Each has a level 4 notebook. What the 0.02.004 data measured (the files are named in each item):
  - Device-aware conjugate-gradient refinement runs without the weight update by default, because on the acceptance task the update makes the
    spread about 7 times worse (`manuscripts/device-aware-refinement/data/beyond_numbers.tex`, `ablBWeightsRatio`). Its hypothesis H3 is
    refuted: on the benchmark device it keeps both thresholds (a spread at least 2 times below phase-fixed WGS at at least 0.9 of its
    efficiency) on 4 of the 6 geometries (the ring, the random set and the two large arrays) and fails on the 10 x 10 lattice (factor 1.90) and on
    the quasi-periodic set (factor 1.05) (`.../data/tab_bench.tex`). At equal wall clock of 1 s the benchmark reads it as the proposed method on 3
    of 6 geometries and a tie on the other 3 (`benchOneDevTimeProposed`, `benchOneDevTimeTie`). The normalized-error loss of Schroff et al. 2023,
    through the same warm start, device model, conjugate gradient and safeguard, gives the same spread within the seed ranges (0.031 percent
    against 0.030 on the crosstalk device, 5 seeds, `.../data/tab_schroff.tex`), so the gain over phase-fixed WGS comes from the device model in
    the loop and the conjugate-gradient steps, not from the loss.
  - The efficiency-uniformity continuation has a mixed result (`manuscripts/efficiency-uniformity-front/data/b5_numbers.tex`). Its hypervolume
    exceeds the union of the five published points by 0.0119 (interval 0.0097 to 0.0141, 8 of 8 seeds, `hvFiveDiff`) on the 10 x 10 lattice, and
    by only 0.0015 at the reference (0, 0.9) (`hvRefFiveUNineDiff`), because the gain lies on the efficient side where the uniformity is far
    below one. It adds no better uniform end. 4 to 7 of its 20 points are dominated by iterates of the published methods (`frontDomMin`,
    `frontDomMax`), so the curve it draws is not the Pareto front of the problem. The benchmark gives it no win: it stores one seed per geometry,
    so all 7 cells at 30 iterations and all 7 at 100 are ties, and its margin is not negative on 5 of 7 geometries at 30 iterations and on 3 of 7 at
    100 (`benchTieThirty`, `benchTieHundred`, `benchPassThirty`, `benchPassHundred`).
  - The flicker-bounded sequence has a paper of its own and a measured scope. On the acceptance task the per-frame GS with phase induction of Kim et
    al. 2019 reaches a higher transient minimum intensity (0.953 against 0.923) with phase steps about five times larger (0.408 rad against 0.077
    rad); the sequence beats linear phase interpolation (0.648), and the sequence holds for short steps per frame (on long moves linear phase
    interpolation leads at equal frames) (`manuscripts/flicker-bounded-sequences/data/flicker_numbers.tex`, `accKimFiveTransMed`, `accBTransMed`,
    `accKimFiveStepMax`, `accBStepMax`, `accLpiTransMed`).
  - Two measured negatives remain: the learned warm start is refuted, and the aberration-robust hologram gives no robustness to pointing errors
    at its acceptance budget (it reaches 1.48 times only with a displacement prior optimized alone at five times that budget).

## Technical report and manuscripts

The detailed technical report and the manuscripts of the proposed methods are on Zenodo, each under its own concept DOI, and are
declared in `product.json` `manuscripts`.

- Technical report (Zenodo, CC BY 4.0), the product, its 24 methods, fourteen cases and the benchmark:
  [10.5281/zenodo.23788731](https://doi.org/10.5281/zenodo.23788731) (concept DOI, always the latest version).
- Manuscript on device-aware conjugate-gradient refinement (Zenodo, CC BY 4.0; the concept DOI of the manuscript that first treated it together
  with the flicker-bounded sequence): [10.5281/zenodo.23788733](https://doi.org/10.5281/zenodo.23788733) (concept DOI).
- Manuscript on flicker-bounded phase-continuous sequences: in preparation (a paper of its own, no DOI yet).
- Manuscript on the weighted-cost continuation of the efficiency-uniformity trade-off (Zenodo, CC BY 4.0):
  [10.5281/zenodo.24022462](https://doi.org/10.5281/zenodo.24022462) (concept DOI).
- Manuscript on aberration-robust holograms by expected-cost optimization (Zenodo, CC BY 4.0):
  [10.5281/zenodo.24022464](https://doi.org/10.5281/zenodo.24022464) (concept DOI).
- Manuscript on a learned warm start for phase-fixed weighted GS, a measured negative result (Zenodo, CC BY 4.0):
  [10.5281/zenodo.24022470](https://doi.org/10.5281/zenodo.24022470) (concept DOI).

## Areas

The repository by area: its folder, whether the area is active or dormant, and what it holds.

| Area | Folder | Status | What it holds |
|---|---|---|---|
| Web | [`frontend/`](frontend/) | active | The workbench (`/app`) and the five documentation routes (`/introduction`, `/methodology`, `/implementation`, `/experiments`, `/benchmark`) on the shared shell 0.26.2, with the engine ported to the browser. Build and test: `cd frontend && npm ci && npm run build && npm test`. |
| API | [`app/`](app/) | dormant: this solution does not require it at the moment | Ships dormant, the site is static; activation is [guide 04](docs/guides/04_run-the-api.md). |
| Core pipelines | [`data-pipeline/`](data-pipeline/) | active | The engine (`pipeline/model/holo/`: forward model, 24 methods in four families, the learned slots), the named stages (bake, evaluate, benchmark, train) and the canonical bake of the fourteen cases: `./scripts/precompute.sh`. See [data-pipeline/README.md](data-pipeline/README.md). |
| Packages | (PyPI) [numpy](https://pypi.org/project/numpy/) | active: consumes numpy, and in the notebooks matplotlib, scipy, [slmsuite](https://pypi.org/project/slmsuite/) 0.5.0 and [onnxruntime](https://pypi.org/project/onnxruntime/) 1.31.1 | DinHot publishes no package of its own; the methods live in the pipeline and are imported by path. |
| Notebooks | [`notebooks/`](notebooks/) | active | Eight topics of didactic notebooks in English and Spanish, from the Fourier optics of a hologram to the learned methods, with level 3 notebooks for the comparison with published methods and level 4 for the five proposed methods. Run: `./scripts/setup.sh --notebooks`, then `python scripts/run_notebooks.py`. Index: [notebooks/README.md](notebooks/README.md); guide: [guide 08](docs/guides/08_notebooks.md). |
| Data | [`data/`](data/) | active | The fourteen cases (`data/examples/cases.json`), the committed derived artifacts of the bake and the evidence of the two learned models, with the sources and their licence classes in [data/README.md](data/README.md). |
| Contracts | [`docs/contracts/`](docs/contracts/) | active | The contract catalog, the JSON schemas (params record, trace, manifest, model card and metrics) and the OpenAPI document. |
| Documentation | [`docs/`](docs/) | active | The SDD ([docs/design/SDD.md](docs/design/SDD.md)), the [guides](docs/guides.md), the [case pages](docs/cases.md) and the [framework cards](docs/frameworks.md) of every method. |
| Tests and gates | [`tests/`](tests/), [`scripts/`](scripts/) | active | `python -m pytest` for the engine, the methods, the contracts and the notebooks' row tests, and the checks (`scripts/check_*.py`, `run_notebooks.py`). See [scripts/README.md](scripts/README.md). |
| Deploy | [`deploy/`](deploy/) | active: deployed to pages | A static site on GitHub Pages, built by `.github/workflows/deploy-pages.yml`; never credentials. |

## Run it

```bash
./scripts/setup.sh                     # the pipeline environment (.venv-pipeline); setup.ps1 on Windows
./scripts/precompute.sh                # the canonical bake into data/derived (a release operation)
.venv-pipeline/bin/python -m pytest    # the pipeline tests, sandboxed
./scripts/setup.sh --notebooks         # the notebook environment (.venv-notebooks); setup.ps1 -Notebooks on Windows
python scripts/run_notebooks.py --check --tmp <temp root>   # every notebook runs top to bottom (a local release gate, never CI)
cd frontend && npm ci && npm run build && npm test && npm run gate
```

## Documentation

- [docs/design/SDD.md](docs/design/SDD.md): the design, every requirement with its gate.
- [docs/](docs/README.md): architecture, guides, cases and frameworks.

Licensed under the Apache License 2.0 (see [LICENSE](LICENSE)). Deployed to pages at https://dinhot.fasl-work.com.
