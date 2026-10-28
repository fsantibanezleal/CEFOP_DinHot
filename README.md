# DinHot

[![CI](https://img.shields.io/github/actions/workflow/status/fsantibanezleal/CEFOP_DinHot/ci.yml?branch=main&label=CI)](https://github.com/fsantibanezleal/CEFOP_DinHot/actions)
[![License](https://img.shields.io/github/license/fsantibanezleal/CEFOP_DinHot)](LICENSE)
[![Version](https://img.shields.io/github/v/tag/fsantibanezleal/CEFOP_DinHot?label=version&sort=semver)](https://github.com/fsantibanezleal/CEFOP_DinHot/tags)
[![Live](https://img.shields.io/badge/site-live-2ea44f)](https://dinhot.fasl-work.com)

Holographic optical trap arrays computed, corrected and tested in the browser

*Arreglos de trampas opticas holograficas calculados, corregidos y probados en el navegador*

## Areas

The repository by area: its folder, whether the area is active or dormant, and what it holds.

| Area | Folder | Status | What it holds |
|---|---|---|---|
| Web | [`frontend/`](frontend/) | active | The workbench and the documentation routes on the shared shell. Build and test: `cd frontend && npm ci && npm run build && npm test`. |
| API | [`app/`](app/) | dormant: this solution does not require it at the moment | Ships dormant; activation is [guide 04](docs/guides/04_run-the-api.md). |
| Core pipelines | [`data-pipeline/`](data-pipeline/) | active | The named pipeline stages and the bake: `./scripts/precompute.sh`. See [data-pipeline/README.md](data-pipeline/README.md). |
| Packages | (PyPI) [numpy](https://pypi.org/project/numpy/) | active: consumes numpy | Each package the product publishes or consumes for its methods, with its version and its PyPI and repository links. |
| Notebooks | [`notebooks/`](notebooks/) | active | The didactic notebooks in English and Spanish, by topic and level. Run: `./scripts/setup.sh --notebooks`, then `python scripts/run_notebooks.py`. Guide: [guide 08](docs/guides/08_notebooks.md). |
| Data | [`data/`](data/) | active | The committed derived artifacts and the sources with their licence classes. |
| Contracts | [`docs/contracts/`](docs/contracts/) | active | The contract catalog and the schemas. |
| Documentation | [`docs/`](docs/) | active | The SDD ([docs/design/SDD.md](docs/design/SDD.md)), the [guides](docs/guides.md) and the case pages. |
| Tests and gates | [`tests/`](tests/), [`scripts/`](scripts/) | active | `python -m pytest` and the checks (`scripts/check_*.py`). See [scripts/README.md](scripts/README.md). |
| Deploy | [`deploy/`](deploy/) | active: deployed to pages | Where it is deployed and how, never credentials. |

## Run it

```bash
./scripts/setup.sh                     # the pipeline environment (.venv-pipeline); setup.ps1 on Windows
./scripts/precompute.sh                # the canonical bake into data/derived (a release operation)
.venv-pipeline/bin/python -m pytest    # the pipeline tests, sandboxed
./scripts/setup.sh --notebooks         # the notebook environment (.venv-notebooks); setup.ps1 -Notebooks on Windows
python scripts/run_notebooks.py --check # every notebook runs top to bottom (a local release gate, never CI)
cd frontend && npm ci && npm run build && npm test && npm run gate
```

## Documentation

- [docs/design/SDD.md](docs/design/SDD.md): the design, every requirement with its gate.
- [docs/](docs/README.md): architecture, guides, cases and frameworks.

Licensed under the Apache License 2.0 (see [LICENSE](LICENSE)). Deployed to pages at https://dinhot.fasl-work.com.
