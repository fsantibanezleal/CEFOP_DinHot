# Software design document: the template's example product

This is the SDD of the example the template ships (ADR-0075): an SIR epidemic model, replayed and re-run live.
It exists so the structure, the contracts, the lanes and the gates are exercised by something real on the first
day. A product writes its own SDD here, after its research and its plan and before it instantiates, and the
guard `scripts/check_sdd.py` holds every requirement to a gate that exists.

## Problem and non-goals

Problem: show, end to end, how a CAOS product turns cases into committed artifacts, replays them, re-runs them
live, and proves each step: a pipeline that bakes and checks cases, a web workbench that reads and recomputes
them, documentation transcribed from sources, and gates that fail when any of it breaks.

Non-goals, each something a reader could reasonably assume:

- Epidemiology. The SIR model is a placeholder with textbook assumptions (closed, homogeneous, deterministic);
  it is not a forecasting tool and carries no real data.
- A choice of integrator. Forward Euler at a quarter-day step is enough to show parity and convergence; a
  product picks its scheme from its own error budget.
- A backend. `app/` is a dormant read-only API; the example is a static site.
- A learned model of record. The surrogate exists to show where a trained model sits in the pipeline and how its
  held-out error is reported.

## Executive brief

The executive view of the Introduction is data, kept apart from this document: one file frames the problem space for a
decision maker (a landing block, five sub-tabs, three illustrations and a linked source for every figure), in English
and Spanish. It is written from the research before any development, is valid against the shell's `executive.schema.json`
2.0.0, and is rendered by the shell as the first view of the Introduction, where the product lands (the header order stays App, Introduction,
Methodology, Implementation, Experiments, Benchmark: the landing never moves the tabs). The standard is
[`docs/guides/06_executive-brief.md`](../guides/06_executive-brief.md). The example's file frames the example's own
problem space and is replaced by every product.

Data file: content/executive.json

## Research basis

Done before the plan, and kept here so a reader can re-check it (ADR-0075; rule 11 section 12). The example is a
placeholder model, so the research is short; a product's is the persisted dossier summarised claim by claim, each
with its source. The list shows what was decided and from what; every DOI below was resolved against the Crossref
record on 2026-10-11 (HTTP 200 each; the two of Dormand and Prince and of Virtanen et al. on 2026-10-26, HTTP 200 each).

| decision | what the research found | source |
|---|---|---|
| The model is the closed SIR system, dS/dt = -beta S I / N, dI/dt = beta S I / N - gamma I, dR/dt = gamma I | The threshold and the whole course follow from R0 = beta / gamma | Kermack and McKendrick 1927, https://doi.org/10.1098/rspa.1927.0118 |
| The model family and its textbook assumptions (closed, homogeneous, deterministic) | The survey states the assumptions the non-goals list | Hethcote 2000, https://doi.org/10.1137/S0036144500371907 |
| R0 as the threshold, and the herd threshold 1 - 1/R0 | The definition of the basic reproduction ratio and its computation | Diekmann, Heesterbeek and Metz 1990, https://doi.org/10.1007/BF00178324 |
| The same threshold for compartmental models | R0 < 1 is the stability condition of the disease-free state | van den Driessche and Watmough 2002, https://doi.org/10.1016/S0025-5564(02)00108-6 |
| The final-size relation z = 1 - exp(-R0 z) is the oracle independent of the time course | A closed derivation of the final size | Miller 2012, https://doi.org/10.1007/s11538-012-9749-6 |
| Forward Euler at a quarter-day step, converging at first order | The scheme's global error is first order in the step | Hairer, Norsett and Wanner 1993, https://doi.org/10.1007/978-3-540-78862-1 |
| A higher-order reference for the engine's integrator: the embedded pair RK45 | A fifth-order formula with a fourth-order error estimate that chooses the step, six evaluations per step | Dormand and Prince 1980, https://doi.org/10.1016/0771-050X(80)90013-3 |
| The implementation of that pair that the level 3 notebook runs as the reference | `scipy.integrate.solve_ivp` offers RK45 and the eighth-order DOP853 | Virtanen et al. 2020, https://doi.org/10.1038/s41592-019-0686-2 |
| Requirements are written in EARS form, each with its gate | The five EARS patterns used in the requirements files | Mavin et al. 2009, https://doi.org/10.1109/RE.2009.9 |

Choices with no source because the example does not need one: the surrogate's four-term basis (a placeholder that
shows where a trained model sits) and the 1500 ms run budget (the template's lane gate, measured in the Lanes
section below).

UNVERIFIED: what each work says beyond its title, scope and DOI record (kept in `frontend/src/content/citations.ts`):
the page text of the works was not re-read for this release, only their Crossref records, so the "what the research
found" cells restate the reason the example cites each work, not a quotation.

## Sizing and contracts

The design rests on two artifacts of contract-first parallel delivery (ADR-0080): the sizing, kept with the
coordination records outside the product (for this release: the repositories, components, modules with their owner
units, the seven boundaries, the technology versions verified on primary sources, the machine limits and three
parallel units with disjoint write scopes), and the contract catalog, kept here,
[`docs/contracts/catalog.md`](../contracts/catalog.md). Every boundary below is a catalog row with one schema file,
an example, a test on each side, its missing-data behavior, a provider and a swap test; the units of a feature are
the sizing's parallel units, built at once against the fixed rows.

- Ingestion (params-record, contract 1, `data-pipeline/pipeline/io/contract.py`): each case's parameters are
  validated before a run. A missing, non-numeric, NaN or out-of-range value is rejected with its reason, never
  coerced; an unusual value (R0 above 20) is accepted and flagged into the manifest.
- Artifacts (case-index, case-manifest, trace, contract 2): `data/derived/manifests/index.json`
  (`example.index/v2`: cases with bilingual titles and categories, the default case), one manifest per case
  (`example.manifest/v4`: parameters, seed, engine and version, artifact, lane verdict, metrics and the model behind them, expected ranges,
  bilingual expected band) and one trace per case (`example.trace/v1`: at most 200 points, summary). The web's
  types are generated from the schema files (`frontend/src/lib/contract.gen.ts`), and
  `frontend/src/lib/contract.test.ts` reads every committed document and the provider tree against them in both
  directions.
- The model slot (surrogate-model): r0 to the peak infected fraction; the analytic baseline answers while no
  trained bundle is released, behind the same contract.
- Readiness: `data/derived/readiness.json`, what is real in this build, row by row, in one of six declared states;
  the site labels what a provider, a stale bake or the baseline serves, and shows not available yet for what is
  missing.
- The dormant API (api, `docs/contracts/api.openapi.json`): GET only; 503 with the declared state when a document
  is absent.

## Technology and versions

Every pinned dependency of `requirements-precompute.txt` (through `data-pipeline/requirements.txt`),
`requirements-dev.txt` and `frontend/package.json`, with the version actually installed; `scripts/check_tech_matrix.py`
fails when a pin and this table disagree. A package.json range is recorded at the version `frontend/package-lock.json`
resolves it to. The runtimes are Python 3.12 (CI; the device's venv may be newer) and Node 22 (CI).

| component | package | version | use | alternative considered |
|---|---|---|---|---|
| engine | numpy | 2.4.6 | the SIR engine and the surrogate's least squares (numpy only, so the template installs with no native build); the same pin in `notebooks/requirements.txt` | scipy.integrate, rejected: a second heavy dependency for a one-line integrator |
| notebooks | matplotlib | 3.11.2 | the figures of the notebooks (`notebooks/requirements.txt`); https://pypi.org/pypi/matplotlib/json read on 2026-10-19, released 2026-09-11 | none: the figures of the notebooks need a plotting library, and the web's uplot runs in the browser only |
| notebooks | scipy | 1.18.1 | the pinned reference implementation of the level 3 example notebook (`scipy.integrate.solve_ivp`, RK45 and DOP853; `notebooks/requirements.txt`); https://pypi.org/pypi/scipy/json read on 2026-10-26, released 2026-08-21 | none: it is the state-of-the-art solver the level 3 notebook compares the engine with; the engine itself stays numpy only |
| notebooks | nbclient | 0.11.0 | executes a notebook top to bottom in a fresh kernel (`scripts/run_notebooks.py`); https://pypi.org/pypi/nbclient/json read on 2026-10-19, released 2026-06-05 | nbconvert --execute, rejected: a heavier install for the same execution |
| notebooks | nbformat | 5.11.1 | reads and writes the notebook format (`scripts/run_notebooks.py`); https://pypi.org/pypi/nbformat/json read on 2026-10-19, released 2026-08-17 | none: the format's own library |
| notebooks | ipykernel | 7.4.0 | the Python kernel the notebooks run in; https://pypi.org/pypi/ipykernel/json read on 2026-10-19, released 2026-09-29 | none: nbclient needs a kernel |
| tests | pytest | 9.1.1 | the pipeline, contract, guard and adversarial tests | unittest, rejected: no parametrisation or fixtures |
| lint | ruff | 0.15.18 | lint of data-pipeline, tests, scripts and app | flake8 plus isort, rejected: two tools for one |
| contracts | jsonschema | 4.26.0 | validates every document against its schema file | fastjsonschema, rejected: no support for the draft the schemas declare |
| contracts | openapi-spec-validator | 0.9.0 | validates `docs/contracts/api.openapi.json` | none: the only maintained validator for the OpenAPI 3.1 document |
| API | fastapi | 0.143.0 | the dormant `app/`, run by the API contract tests | flask, rejected: no response models to compare with the OpenAPI document |
| API | httpx | 0.28.1 | the test client of the dormant `app/` | requests, rejected: FastAPI's test client needs httpx |
| shell | @fasl-work/caos-app-shell | 0.19.1 | the shared app shell (pinned exactly, ADR-0078) | a hand-rolled shell, forbidden by ADR-0078 |
| web | react | 19.3.0 | the UI | none: the shell requires it |
| web | react-dom | 19.3.0 | the UI renderer | none: the shell requires it |
| web | react-router | 8.4.0 | the routes | none: the shell requires it |
| web | zustand | 5.0.15 | the workbench selection store | redux, rejected: one store of a few keys |
| web | katex | 0.19.1 | typeset equations on the pages | MathJax, rejected: heavier and slower to render |
| web | lucide-react | 1.52.0 | icons | the shell's own set where it has one |
| web | uplot | 1.6.32 | the interactive curves (`UPlotChart`) | a static SVG, rejected: no hover or zoom |
| build | vite | 8.3.5 | bundler and dev server | webpack, rejected: slower and needs more configuration |
| build | @vitejs/plugin-react | 6.1.1 | the React transform for vite | none |
| build | typescript | 5.9.3 | type check of the web and the generated contract types | none |
| build | openapi-typescript | 7.13.0 | generates `contract.gen.ts` from the OpenAPI document | hand-written types, rejected: they drift (the build checks them) |
| build | @types/node | 24.19.1 | types of the build scripts | none |
| build | @types/react | 19.3.0 | types of React | none |
| build | @types/react-dom | 19.3.0 | types of React DOM | none |
| tests | vitest | 5.0.3 | the web unit tests | jest, rejected: needs a transform for the vite config |
| gate | playwright | 1.63.0 | the measured UI gate (`npm run gate`), local only | cypress, rejected: heavier install |

## Resources

What each stage needs on the development workstation (Windows 11, 2026-10-11; peak is the largest working set of the
stage's processes, polled every 20 ms; the commands and outputs of the bake, the live engine and the site are in
[`measured-resources.md`](measured-resources.md)). No stage uses a GPU or a
network after the install. Bounds are stated where a figure depends on the product: a product measures its own and
replaces this table.

| stage | memory | disk | time | where it runs |
|---|---|---|---|---|
| bake (`data-pipeline/run.py`, five cases, the released surrogate) | 33 MB peak | 35 KB of artifacts in `data/derived/` (35,145 bytes) | 0.1 s | workstation, never CI |
| training (the surrogate, folded into a bake with no released bundle, five cases) | 33 MB peak | 1 KB (`models/surrogate.json`) | 0.3 s | workstation, never CI |
| tests (pytest, the whole suite, 599 tests of which 3 skip without node: 117 s in one run on 2026-10-12, behind the workstation's shared heavy-job lock) | 107 MB peak per process, 3.1 GB summed over the 253 processes the first suite started (not re-measured for the larger suite) | temporary copies of the few files each guard reads, under a MB each | 117 s | workstation (the plants alone, `tests/adversarial`, also run in CI; the first CI time is recorded in the release notes) |
| install (`npm ci`) | 240 MB peak | 181 MB in `node_modules` | 123 s with a cold cache | workstation and CI web job |
| build (`npm run build`) | 340 MB peak | 1.9 MB in `frontend/dist` (1,917,973 bytes; 2.2 MB allocated on disk) | 5 s | workstation and CI web job |
| web unit tests (`npm test`, 55 tests) | 110 MB peak | none | 1 s | workstation and CI web job |
| deploy payload (GitHub Pages) | none | 1.9 MB uploaded | one Pages deploy, under 2 min | CI after main |

## Lanes

- Offline: `data-pipeline/run.py` bakes every case (about a millisecond each) and checks it against its expected
  ranges; it runs on a workstation, never in CI and never in the browser.
- Replay: the committed artifacts, copied into the site by `frontend/scripts/copy-data.mjs` (exactly the declared
  files) and fetched with the version in the address.
- Live: `frontend/src/engine/sir.ts`, a step-for-step port of the Python engine. The basis for putting it in the
  browser is measured, not assumed: the lane gate (`data-pipeline/pipeline/core/gate.py`) gives each case a run
  budget of 1500 ms and a trace budget of 256 KiB, and the Benchmark page measures the live engine against that
  budget in the reader's browser (a median of 0.006 to 0.010 ms per case under Node 24 on the development workstation, 2026-10-12,
  [`measured-resources.md`](measured-resources.md)).

## Method ladder

One method, the example engine, with one acceptance criterion: the live engine reproduces every baked trace to
the trace rounding (0.005 people), and both converge to the final-size relation at first order in the step.
Gates: `frontend/src/engine/sir.parity.test.ts`. A product's ladder (classical, state of the art, learned,
frontier) gets one criterion per method here, each with its gate, per ADR-0069.

## Cases

Five cases in two categories. Outbreak regimes: sub-critical (R0 0.72, no outbreak), epidemic (R0 2.75), fast burn
(R0 6), slow spread (R0 1.2, still running when the horizon ends). Controls: no initial infection (R0 2, nothing
happens). Each exists to test a different part of the engine and the views: the threshold, a full epidemic, a
sharp early peak, a horizon that cuts the run, and the degenerate start. Every case states numeric expected
ranges, enforced by `data-pipeline/pipeline/core/expect.py`. Variants: immunisation of 0%, 30% and 60% at the
start, computed live.

## Oracles

- The final-size relation z = 1 - exp(-R0 z) (Kermack and McKendrick 1927; Miller 2012), independent of the time
  course: a run that ends inside its horizon must reach it, to first order in the step.
- The threshold R0 = 1 and the herd threshold 1 - 1/R0 (Diekmann, Heesterbeek and Metz 1990): a sub-critical case
  must not grow, and an immunisation above the threshold must prevent the outbreak.
- Parity: the Python engine is the reference for the live engine, to the trace rounding.
None of these is a model judging a model.

## Beyond the state of the art

None claimed. The example is a teaching model: its engine is the textbook SIR system integrated by Forward Euler, and
the state of the art it is compared with (a higher-order Runge-Kutta solver, SciPy's RK45) is in the level 3 notebook
of `notebooks/`. A product that goes further lists each component here under an identifier of the form
BS-<n>, with its evidence and its source, and covers each with a level 4 notebook in each language
([`docs/guides/08_notebooks.md`](../guides/08_notebooks.md)).

## Deploy driver

GitHub Pages: a static site with every artifact committed, no secret and no server. The measurement behind it is
the lane gate above (every case is live-eligible) and the site size (1.88 MB of site files, most of it KaTeX
fonts, and 35 KB of artifacts, 1.9 MB in all, measured on the 2026-10-12 build, [`measured-resources.md`](measured-resources.md)). The target is written in `deploy/TARGET` and checked by `scripts/check_deploy_place.py`.

## Risks and kill criteria

- Risk: an instantiated product keeps pieces of the example. Kill: `scripts/check_template_residue.py` fails.
- Risk: the two engines drift. Kill: the parity test fails.
- Risk: a test rewrites the committed artifacts. Kill: the session guard in `tests/conftest.py` fails the run.
- Risk: the site looks right and is not (a blank drawing, a dead control, a broken deep link). Kill: the measured
  gate (`npm run gate`) fails before a deploy.
- Risk: a contract changes on one side only. Kill: the generated types fail the web build when they are not
  current, and the contract tests of both sides read the same schema files.
- Risk: a provider ships as if it were the product. Kill: the readiness document labels it on every view, and
  `scripts/check_skeleton.py` lists every row still on a provider.

## ADR fit

How the example meets the ADRs it is bound by, and where the base carries the rule (ADR-0078):

| ADR | Rule | Carried by |
|---|---|---|
| ADR-0057 | two contracts, named stages, lanes | `data-pipeline/`, `docs/contracts/catalog.md` (the two contracts are its rows) |
| ADR-0058 | architecture modal, five themed bilingual tabs | `frontend/src/architecture/`, validated by the shell on mount |
| ADR-0069 | method vertical with its acceptance criterion | this SDD, the parity and convergence tests |
| ADR-0070 | Focus mode for the App: a workbench opens the open group of a case in the full viewport, a surface opens each view with a stage; `?focus=1`, Escape or the exit button returns to the same case or view, group and sub-view | `frontend/src/workbench/Workbench.tsx` (`focus`), `npm run gate` with `--require-focus` (G18); the App's kind is `product.json` `app` (this example is a workbench), and only a surface App without simulation waives Focus, with its reason here as "not applicable: <reason>" |
| ADR-0071 | the page is the viewport; one tab row; drawing at least half the viewport | the shell's `CaseWorkbench`; the gate (G5, G6) |
| ADR-0074 | CI runs cheap checks only | `.github/workflows/ci.yml`, `scripts/check_ci_budget.py` |
| ADR-0075 | every requirement names its gate | `docs/design/features/`, `scripts/check_sdd.py` |
| ADR-0078 | rules live in the base | shell 0.19.1 (pinned exactly) and this template; no product re-implements them |
| ADR-0080 | contract-first parallel delivery: catalog, one schema per boundary, providers, declared states, readiness | `docs/contracts/`, `tests/contracts/`, `frontend/src/readiness/`, `scripts/check_contracts.py`, `scripts/check_readiness.py` |
