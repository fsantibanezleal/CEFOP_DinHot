# DinHot

[![CI](https://img.shields.io/github/actions/workflow/status/fsantibanezleal/CEFOP_DinHot/ci.yml?branch=main&label=CI)](https://github.com/fsantibanezleal/CEFOP_DinHot/actions)
[![License](https://img.shields.io/github/license/fsantibanezleal/CEFOP_DinHot)](LICENSE)
[![Version](https://img.shields.io/github/v/tag/fsantibanezleal/CEFOP_DinHot?label=version&sort=semver)](https://github.com/fsantibanezleal/CEFOP_DinHot/tags)
[![Live](https://img.shields.io/badge/site-live-2ea44f)](https://dinhot.fasl-work.com)

Holographic optical trap arrays computed, corrected and tested in the browser

*Arreglos de trampas opticas holograficas calculados, corregidos y probados en el navegador*

Live site: https://dinhot.fasl-work.com. DinHot is a holography studio for optical trap arrays and shaped light fields. A reader picks
one of thirteen cases (a trap geometry or a target potential, on a stated optical setup and phase-only SLM), computes the phase
hologram with any of 24 methods, and sees where the light goes, how uniform and efficient the traps are, what the device and the
aberrations cost, what a camera feedback loop recovers and what a trapped bead or atom does in the computed potential. It was born at
CEFOP (Universidad de Concepcion) as DinHotSys, a C++ desktop tool, and is rebuilt here on the CAOS product template and shell. The
design is [docs/design/SDD.md](docs/design/SDD.md).

## The three tiers of methods

Every method of the ladder belongs to one tier ([guide 09](docs/guides/09_method-tiers.md)), runs on the product's cases with the same
seeds and metrics, and is compared with the other tiers on the Benchmark page:

- **Classical**: the established methods, from the superposition of prisms and lenses to Gerchberg-Saxton, weighted GS and the
  volumetric 3D GS.
- **State of the art**: the current solutions, replicated or implemented here, among them phase-fixed weighted GS, MRAF, optimal-transport
  starts, conjugate gradient and Wirtinger-Adam descent with a device model, closed-loop feedback, atom rearrangement and the learned
  multi-plane network. The level 3 notebooks run them against slmsuite 0.5.0 or the classical method.
- **Beyond the state of the art**: six proposals of the product, BS-1 to BS-6, each tested and reported as it came out, including two
  measured negatives (BS-3, the learned warm start, refuted; BS-4, whose robustness to pointing errors does not follow). Each has a level 4
  notebook.

## Technical report and manuscripts

The detailed technical report and the manuscripts of the beyond-the-state-of-the-art methods are on Zenodo, each under its own concept
DOI, and are declared in `product.json` `manuscripts` once they are published ([guide 09](docs/guides/09_method-tiers.md)).

- Technical report (Zenodo, CC BY 4.0): concept DOI TO BE FILLED AT RELEASE by the main session.
- Manuscripts of the BS claims: concept DOIs TO BE FILLED AT RELEASE by the main session, one per manuscript.

## Areas

The repository by area: its folder, whether the area is active or dormant, and what it holds.

| Area | Folder | Status | What it holds |
|---|---|---|---|
| Web | [`frontend/`](frontend/) | active | The workbench (`/app`) and the five documentation routes (`/introduction`, `/methodology`, `/implementation`, `/experiments`, `/benchmark`) on the shared shell 0.19.6, with the engine ported to the browser. Build and test: `cd frontend && npm ci && npm run build && npm test`. |
| API | [`app/`](app/) | dormant: this solution does not require it at the moment | Ships dormant, the site is static; activation is [guide 04](docs/guides/04_run-the-api.md). |
| Core pipelines | [`data-pipeline/`](data-pipeline/) | active | The engine (`pipeline/model/holo/`: forward model, 24 methods in four families, the learned slots), the named stages (bake, evaluate, benchmark, train) and the canonical bake of the thirteen cases: `./scripts/precompute.sh`. See [data-pipeline/README.md](data-pipeline/README.md). |
| Packages | (PyPI) [numpy](https://pypi.org/project/numpy/) | active: consumes numpy, and in the notebooks matplotlib, scipy, [slmsuite](https://pypi.org/project/slmsuite/) 0.5.0 and [onnxruntime](https://pypi.org/project/onnxruntime/) 1.31.1 | DinHot publishes no package of its own; the methods live in the pipeline and are imported by path. |
| Notebooks | [`notebooks/`](notebooks/) | active | Eight topics of didactic notebooks in English and Spanish, from the Fourier optics of a hologram to the learned methods, with level 3 notebooks for the state-of-the-art methods and level 4 for the six claims beyond it. Run: `./scripts/setup.sh --notebooks`, then `python scripts/run_notebooks.py`. Index: [notebooks/README.md](notebooks/README.md); guide: [guide 08](docs/guides/08_notebooks.md). |
| Data | [`data/`](data/) | active | The thirteen cases (`data/examples/cases.json`), the committed derived artifacts of the bake and the evidence of the two learned models, with the sources and their licence classes in [data/README.md](data/README.md). |
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
