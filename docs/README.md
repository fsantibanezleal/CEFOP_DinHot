# Docs, the DinHot wiki

The product wiki (ADR-0056), written as the product is built, unit by unit, never at the end. DinHot is a holography studio for optical trap arrays and shaped light fields: twelve cases, 24 methods from the classical
baselines through the published state of the art to methods beyond it, a device model, a camera feedback emulator, trapped-particle dynamics, and a static web workbench that runs in the browser. The pipeline, its
validation and these documents are the product; the web app is its companion workbench. The design, with every requirement and its gate, is [design/SDD.md](design/SDD.md).

DinHot began as DinHotSys, a C++ desktop tool of CEFOP at the Universidad de Concepcion (2010), was rewritten in Python and FastAPI, and is rebuilt here on the CAOS product template and shell. The provenance and the third-party
licences are in [ATTRIBUTION.md](../ATTRIBUTION.md).

## Map

- **[architecture/](architecture.md)**: how the repository works: the overview and the lanes, determinism and the trace, the gates, the live lane, the staged pipeline, model evaluation and the benchmark protocol, deploy, the
  data contracts, the method interface and registry.
- **[frameworks/](frameworks.md)**: one card per method of the ladder (M01 to M19, B1 to B5) and per physics component (P01 to P07): equations with their sources, implementation and defaults, acceptance criterion and test,
  measured values with their conditions, limits and references. The deep research, made binding.
- **[cases/](cases.md)**: the coverage matrix of the twelve cases (C01 to C12), their categories and one card per case.
- **[guides/](guides.md)**: runnable how-tos: run the precompute pipeline, bring your own case, the GPU lane, run the API, the architecture modal, the executive view, the documentation pages, the notebooks.
- **[design/](design/README.md)**: the software design document, its features and requirements, and the measured resources.
- **[contracts/](contracts/catalog.md)**: the contract catalog, the schemas, the examples and the provider tree.

## Where to start

| You want to | Read |
|---|---|
| Know what the product is and is not | [architecture overview](architecture/01_overview.md) |
| Understand a method | its card in [frameworks](frameworks.md), then the Methodology page of the site |
| Reproduce a published result | [C12, calibration](cases/arrays/C12_calibration.md) and the cards of M01 to M06 |
| See how a number is produced | [model evaluation](architecture/06_model-evaluation.md) and the card's measured-values section |
| Run it | [guide 01](guides/01_precompute-pipeline.md) |
| Run it on your own task | [guide 02](guides/02_bring-your-own-data.md) |

## Honesty and data policy

- Numbers come from the engine and the committed artifacts, never from a claim. A number on a card is either a published result, labelled with its source and conditions, or a DinHot measurement, labelled with its seeds, grid
  and date. Where DinHot does not reproduce a published number, the card says so; where a source could not be read, the card says UNVERIFIED and what was tried.
- All twelve cases are synthetic: parameters are stated, absolute numbers are those of the stated model, not of a measured instrument. The product does not drive hardware.
- Public derived artifacts are committed (`data/derived/`); raw and private sources stay out of git (`data/raw/`) per ADR-0055. The two data contracts ([architecture/08_data-contracts.md](architecture/08_data-contracts.md))
  govern the cases in and the artifacts out.
- The canonical bake of the twelve cases and the full benchmark are not committed yet. The case cards state their expected ranges and say which are provisional; the learned methods (M17, B3) state their contract and say that
  their measurements are pending.
