# Software design document: SoftQP Studio

Design version 0.01.000. The solver contribution is a hypothesis subject to proof and comparative evaluation.

## Problem and non-goals

Control, robotics, building-energy, and optimization engineers encounter quadratic programs whose selected operational constraints may yield. Solver APIs often make the mathematical meaning of “soft” difficult to inspect: a quadratic violation cost, an exact linear penalty, a weighted two-sided penalty, a group penalty, and an infeasibility-repair objective can return different decisions even when attached to the same interval. Practitioners need to see what is softened, what remains hard, how lower and upper violations are priced, whether the returned point solves that declared objective, and how numerical behavior changes across methods.

SoftQP Studio is a research workbench that lets a reader select a fully specified case, edit supported cost and scenario parameters, solve and compare declared formulations, inspect side-specific violations and residuals, and export a provenance-bearing result. Its offline scientific pipeline is authoritative. The website replays checksummed results; any browser solver is a separately gated lane.

Non-goals:

- A certified controller, safety case, engineering approval, or production control loop.
- A claim that feasibility restoration, fixed elastic penalties, exact penalties, and infeasibility certificates have interchangeable semantics.
- A universal ranking of solvers or transfer of paper timing claims to this product's machine.
- A hosted solver API or collection of user scenarios on a server.
- Client-specific models, proprietary datasets, or unlicensed data redistribution.
- A claim that asymmetric costs, always-feasible optimization, or L1 exactness are new.
- Social-media publication. Required diffusion materials are private repository drafts only.

## Executive brief

Data file: content/executive.json

The sourced bilingual brief and three authored illustrations frame the engineering policy, affected roles, existing methods and acceptance actions.

## Research basis

Separate research manuscript on side-specific and directional peak updates, with both negative timing studies: https://doi.org/10.5281/zenodo.23875071 .

Research is documented in [the source review](../research.md). It reviews classical explicit lifting, OSQP, the 2025 quadratic-slack ADMM result, the 2026 generalized slack projection paper and its OSQPSlack implementation, DAQP, ElastiQP, PIQP, MPC soft constraints, benchmark protocols, and ICLR 2026 FlexQP/Deep FlexQP.

| Design decision | Research finding | Consequence |
|---|---|---|
| Keep explicit lifting as the classical baseline | It directly represents the declared penalty with variables and constraints and is an independent oracle path. | Run an actual QP implementation and recover/verify physical slacks. |
| Include generalized slack projection | The 2026 paper provides multiple convex penalty families without increasing the principal QP dimension under its assumptions. | Pin the authors' source revision and reproduce compatible penalties. |
| Compare side-specific penalties | DAQP already supports different lower/upper linear and quadratic weights. | Asymmetry alone cannot be presented as the proposed contribution. |
| Include exact restoration semantics | FlexQP is an always-feasible exact L1 elastic method; learned Deep FlexQP reports acceleration. | Treat it as a distinct restoration objective. The official ICLR paper entry inspected on 2026-10-31 exposed no code link; do not claim its results are reproduced. |
| Candidate contribution | Unconditional penalty assumptions in the generalized projection paper exclude non-even penalties. | Test an asymmetric separable convex penalty update in OSQP-style ADMM; novelty remains unproven until the primary-source search and method review are complete. |
| Static-first product | The primary outputs are finite, versioned, reproducible result documents. | GitHub Pages is a candidate only after payload, route, and browser measurements. |


Sources: https://arxiv.org/html/2512.01565v2 ; https://github.com/StanfordASL/elastiqp ; https://www.mathworks.com/help/mpc/ug/optimization-problem.html ; https://arxiv.org/abs/2610.35631 ; https://osqp.org/docs/solver/ ; https://darnstrom.github.io/daqp/start/advanced/soft ; https://openreview.net/pdf?id=HL3TvE4Afm .

UNVERIFIED: novelty, superiority, complete method coverage, field safety and deployment.

## Sizing and contracts

The current size estimate is a research-grade software package, not a small front-end. The product template provides the app, contract system, pipeline structure, guards, notebook and deployment scaffolding; it does not provide the scientific methods, adapters, fixtures, proofs, data, result matrix, bilingual lessons, manuscript, or UI interaction. Expected workload is XL across method engines and matrix, L across product/app/docs, and L for release evidence. A release is gated by the exact acceptance matrix, not an elapsed-time estimate.

Proposed units with disjoint write ownership after contract freeze:

| Unit | Boundary | Owns |
|---|---|---|
| U1: contracts and case pipeline | schemas and manifests | `data-pipeline/pipeline/io`, schemas and catalog rows, deterministic case registry, splits/seeds, run orchestration, output validation and replay index |
| U2: solver engines and adapters | method API/result | engine build and pinned source provenance, explicit lift, generalized projection, DAQP/FlexQP adapters, AAGSP only after proof gate |
| U3: web and content | static artifacts | six shell pages, app case interaction, comparison/inspection/export, English/Spanish content, accessibility and measured browser gate |
| U4: evidence and curriculum | experiment artifact/notebooks | held-out runner, stats and raw measurements, bilingual notebooks and docs, executive brief, manuscript/report and private post drafts |

The units define module ownership and stable contract seams.

Engine decision: The separate public repository `CAOS_SoftQP_Engine` owns distribution/import `softqp`. It vendors the reviewed C core and Python binding with Apache-2.0, MIT and BSD notices, pinned QDLDL and marked source changes. Linux and Windows tests and wheel builds passed on promoted source. The app consumes published distribution `softqp==0.1.0`; a fresh public-index Windows install passes all 94 native tests and license checks. The historical experiment remains tied to its exact source revision. CPU builtin backend is supported. The approved ownership decision is implemented.


## Technology and versions

This development correction adopts released template 0.14.005 (main be5eb2c8d0d6d1fa2100e0e8d0994d182329e076, exact-head CI41487592260) and published shared shell0.19.12. The external local workflow, admission correction and template/product test ownership were implemented and independently validated in the shared base before this adoption; full product foundation acceptance is a separate gate. Public SDK regression uses CPython 3.12.14 and the exact-source historical profile retains CPython 3.12.10; Node 24.14.1 was measured locally. Linux/Windows native source and wheels are verified. Current development and notebook requirements pin the published engine distribution; the separate historical campaign environment retains its exact Git revision. Public distribution and fresh consumer installation are verified. These direct dependencies match the actual requirements and committed npm lock.

| component | package | version | use | alternative considered |
|---|---|---|---|---|
| shell | @fasl-work/caos-app-shell | 0.19.12 | Shared workbench and measured gate | Custom shell duplication |
| tooling | @types/node | 24.19.1 | Locked direct dependency declared in frontend/package-lock.json | Separate custom implementation |
| tooling | @types/react | 19.3.0 | Locked direct dependency declared in frontend/package-lock.json | Separate custom implementation |
| tooling | @types/react-dom | 19.3.0 | Locked direct dependency declared in frontend/package-lock.json | Separate custom implementation |
| tooling | @vitejs/plugin-react | 6.1.1 | Locked direct dependency declared in frontend/package-lock.json | Separate custom implementation |
| browser validation | ajv | 8.20.0 | Scientific runtime schemas | Type assertions alone |
| active-set reference | daqp | 0.10.3 | Original-scale side costs | Hidden regularization |
| L1 active-set reference | elastiqp | 0.2.0 | Pure L1 soft inequalities and hard equalities | Unmatched softened hard inequalities |
| tooling | fastapi | 0.143.0 | Locked direct dependency declared in requirements-dev.txt | Separate custom implementation |
| tooling | httpx | 0.28.1 | Locked direct dependency declared in requirements-dev.txt | Separate custom implementation |
| notebook kernel | ipykernel | 7.4.0 | Pinned Python execution | Ambient kernel |
| schema validation | jsonschema | 4.26.0 | Standalone scientific boundaries | Duplicated assumptions |
| tooling | katex | 0.19.1 | Locked direct dependency declared in frontend/package-lock.json | Separate custom implementation |
| tooling | lucide-react | 1.52.0 | Locked direct dependency declared in frontend/package-lock.json | Separate custom implementation |
| scientific figures | matplotlib | 3.11.2 | Executed notebook plots | Baked screenshots |
| codegenerator compatibility | minimatch | 11.0.1 | Reviewed scoped override for the pinned OpenAPI generator | An incompatible Redocly major override |
| notebook runner | nbclient | 0.11.0 | Fresh-kernel execution | Unexecuted notebooks |
| notebook format | nbformat | 5.11.1 | Structured notebook files | Hand-edited output JSON |
| arrays | numpy | 2.5.4 | Original-space vector arithmetic | Scalar loops |
| tooling | openapi-spec-validator | 0.9.0 | Locked direct dependency declared in requirements-dev.txt | Separate custom implementation |
| tooling | openapi-typescript | 7.13.0 | Locked direct dependency declared in frontend/package-lock.json | Separate custom implementation |
| independent oracle | osqp | 1.1.3 | Stock explicit-lift reference | Same native fork as the only oracle |
| tooling | playwright | 1.63.0 | Locked direct dependency declared in frontend/package-lock.json | Separate custom implementation |
| tests | pytest | 9.2.0 | Native, contract and adversarial checks | Manual-only checks |
| manuscript PDF inspection | pypdf | 6.21.4 | Read PDF objects in the raster-refusal tests | Raster figures passing as vector assets |
| tooling | react | 19.3.0 | Locked direct dependency declared in frontend/package-lock.json | Separate custom implementation |
| tooling | react-dom | 19.3.0 | Locked direct dependency declared in frontend/package-lock.json | Separate custom implementation |
| tooling | react-router | 8.4.0 | Locked direct dependency declared in frontend/package-lock.json | Separate custom implementation |
| lint | ruff | 0.15.18 | Static Python source validation | Unpinned formatting |
| sparse matrices | scipy | 1.18.1 | CSC assembly and convexity checks | Dense-only storage |
| native engine | softqp | 0.1.0 | Pinned native generalized and asymmetric solver | Separate package over internal distribution |
| tooling | typescript | 5.9.3 | Locked direct dependency declared in frontend/package-lock.json | Separate custom implementation |
| tooling | uplot | 1.6.32 | Locked direct dependency declared in frontend/package-lock.json | Separate custom implementation |
| tooling | vite | 8.3.5 | Locked direct dependency declared in frontend/package-lock.json | Separate custom implementation |
| tooling | vitest | 5.0.3 | Locked direct dependency declared in frontend/package-lock.json | Separate custom implementation |
| tooling | zustand | 5.0.15 | Locked direct dependency declared in frontend/package-lock.json | Separate custom implementation |

## Resources

Design budgets, to be measured and enforced before release; no stage has yet been shown to meet the full-product budget. CPU-only.

| stage | memory | disk | time | where it runs |
|---|---|---|---|---|
| bake | 4 GiB | 2 GiB raw samples | 2 hours | bounded workstation job; reduce batches without discarding required cells |
| training | not applicable until a learned comparator is reproducibly available | no model currently produced | no training currently scheduled | baseline and candidate are deterministic solvers |
| tests | 4 GiB | 2 GiB temporary build | 15 minutes | build system time limit; analytic/lifted suite is a separate narrow measurement |
| build | 2 GiB | 1 GiB dependencies and outputs | 5 minutes | static-site build budget |
| deploy | browser budget 256 MiB | 20 MiB compressed artifacts | initial route 3 seconds under declared QA network | replay-first design acceptance budget |

## Lanes

Offline: native solver and independent lifting with full matrix, validation and checksummed export. Replay: committed artifact documents read by the browser. Live: disabled until native browser packaging, matched-result parity, resource and latency measurements pass; replay parameter selections must never be labeled as a newly solved scenario. No server lane is planned.

## Method ladder

Each promised method is a real executable vertical, not a citation. The final set and compatible cells are fixed in the machine-readable matrix before implementation.

| id | tier | method | acceptance criterion | gate |
|---|---|---|---|---|
| M-1 | classical | Explicitly lifted soft QP solved with pinned OSQP | Same canonical objective, recovered slack and objective agree with an independent high-accuracy oracle within the per-case tolerance; hard rows remain within tolerance. | Contract, oracle, and per-case tests |
| M-2 | sota | Authors' generalized slack projection OSQP implementation | Reproduce supported quadratic, L1, elastic-net and selected grouped cases at the exact source pin; objective, slack, and residual reports validated against lifting. | Provenance/source-pin and method-case matrix gate |
| M-3 | sota | DAQP side-specific weights | Lower/upper linear/quadratic semantics map exactly; only compatible convex cases are compared, and unsupported cases are marked incompatible with reason. | Adapter parity and case compatibility gate |
| M-4 | sota | FlexQP exact L1 feasibility restoration | Reconstruct from the paper only if its algorithm, assumptions and test oracle are independently reviewed; report as restoration, not a substitute for arbitrary fixed penalty objectives. | Mathematical implementation review and oracle gate |
| M-6 | sota | ElastiQP 0.2.0 dual active set | Pure L1 positive-definite side costs and hard equalities match independent lifting; hard inequalities and quadratic costs are refused. | Published adapter parity and original dual recovery tests |
| BS-1 | beyond | AAGSP side-specific generalized projection | Mathematical review passes; independent lifted oracle agrees on all supported cases; preregistered practitioner outcome improves on compatible matched cases without hard-constraint or accuracy regression. | Proof, novelty, adversarial tests, and held-out benchmark gates |
| BS-2 | beyond | Directional disjoint group-peak update preserving original interval rows | Fixed positive diagonal metric, alpha in(0,2), convex closed monotone scalar price, positive directional scales, nonempty soft box and an attained saddle point; original-space checks pass. Registered144-instance paired10% criterion is false; no novelty or timing superiority established. | `tests/coupled/test_coupled_correctness.py`, `tests/coupled/test_coupled_export.py`, `tests/test_coupled_lessons.py` |

Deep FlexQP remains a conditional unavailable comparator because trained code/weights/data were unavailable. Its former M-5 row is excluded from the executable ladder, rather than fabricating a learned-policy result. The fixed FlexQP reconstruction does not claim trained-policy reproduction.

Internal tier words and IDs remain in design/control records only. Product pages, README, notebooks, posts, and manuscripts use method names and the shared terminology rules.

## Cases

Minimum catalog: 12 deterministic, meaningfully distinct cases. All compatible method-by-case cells run and every incompatible cell records a reason. Initial matrix:

| ID | Case | Category | Main evidence |
|---|---|---|---|
| C01 | Single lower-bound undershoot | semantic oracle | lower-side penalty, signed slack, objective |
| C02 | Single upper-bound overshoot | semantic oracle | upper-side penalty, signed slack, objective |
| C03 | Competing lower and upper rows | semantic oracle | side asymmetry and active-set change |
| C04 | Mixed hard and soft rows | hard-row integrity | hard violations, soft trade-off |
| C05 | Grouped penalty case | penalty compatibility | group slack norm versus separable methods |
| C06 | Sparse scaling family, held-out seeds | numerical structure | n, m, nnz, setup/factorization/solve |
| C07 | Semidefinite Hessian with regularized and unregularized variants | numerical structure | assumptions, status, residuals |
| C08 | Ill-conditioned Hessian and row scales | numerical structure | accuracy, iterations, factorization stability |
| C09 | Feasible double-integrator MPC | repeated control | baseline equivalence and warm-start behavior |
| C10 | Disturbance-induced state conflict with hard dynamics/actuator bounds | repeated control | selected state violation, invariant hard constraints |
| C11 | Conflicting safety boundaries | control conflict | restoration versus declared user penalty semantics |
| C12 | Warm-started parameter stream | repeated control | update/factorization reuse, continuity, status |
| C13 | Reproduced two-zone/battery/grid energy case from OSQPSlack source | energy | source-faithful reproduction before variants |
| C14 | Energy comfort/import with distinct side costs | energy | product-specific asymmetric application |
| C15 | Mixed linear/quadratic side-specific penalty | energy/control | exact penalty semantics and solver coverage |

C13 includes the upstream model/data terms under compatible license and preserves attribution; otherwise a documented non-redistributable input reference and checksum is used, with a separately authored model only if the research question remains comparable. No synthetic case may be represented as field data.

## Oracles

Correctness is checked two ways: (1) independent explicit lifting solved to tighter tolerances, with recovered slacks and objective recomputed in original coordinates; (2) KKT/primal/dual residual checks and high-accuracy cross-checks on compatible cases. Hard/equality rows have separate tolerances and can never be counted as soft slack. Penalty decomposition is recomputed outside each solver. Infeasible restoration outputs are not compared by a fixed-penalty objective unless formulations match exactly.

Recorded metrics: objective components, objective gap, primal/dual/KKT residuals, side-specific and aggregate violation, hard-row violations, violated row IDs, status, setup/factorization/update/solve/end-to-end time, iterations, matrix dimensions/nonzeros, peak memory where measurable, warm/cold mode, timeouts/failures, machine/runtime/BLAS thread settings, package/source hashes, seed and tolerance configuration.

Protocol: paired generated problems and held-out seeds declared before final bake; repeated timing samples; pinned machine and dependency environment; thread limits; equivalent termination accuracy; medians and dispersion/uncertainty; preserve raw samples. Report incompatible or failed runs explicitly. No cross-paper timing is used as a product comparison. DAQP, FlexQP and Deep FlexQP are reported only for semantics/availability that can be supported fairly.

## Deploy driver

GitHub Pages is the leading static candidate because the reader replays committed case results and no user scenario needs a server. Selection is conditional on measured build size, route/deep-link behavior, browser memory and payload budgets. If client-side solving fails those budgets, ship replay only. Domain inventory/availability is not yet established; no custom domain is selected. CI runs inexpensive guards/builds; offline scientific matrix is a separately invoked reproducible gate, not run on every push. Deployment acceptance requires live URL checks for version, case/experiment routes, checksums and language/theme behavior.

## Risks and kill criteria

- AAGSP identity/prox/convergence proof fails or duplicates known published work: stop that method and revise the contribution before product creation.
- The required method does not beat relevant baselines: report negative evidence; do not claim beyond-current-method results or release a product claiming the contribution.
- OSQPSlack extension cannot be legally and technically isolated into a reproducible public engine package: stop before repo creation and redesign the ownership route.
- FlexQP reconstruction cannot be validated: mark method-cell unavailable with the exact reason; do not imply reproduced results. Deep FlexQP has the same rule plus model/data provenance.
- Third-party energy case cannot be licensed or reproduced: record exclusion and ensure the authored alternative tests the same declared question.
- App payload or browser computation exceeds measurements: retain offline methods and static replay, disable live execution.
- Solver defaults diverge in tolerance/status: exclude ranking unless matched accuracy is shown.
- Template residue, shallow bilingual material, missing matrix cells, or missing manuscript gates: release blocked.

## ADR fit

Adopt ADR-0057 (scientific app), ADR-0056 (wiki), ADR-0058 (architecture modal), ADR-0069 (full scientific repository), ADR-0070 (Focus workbench), ADR-0071 (viewport and UI), ADR-0074 (cheap CI), ADR-0075 (reviewed pre-code SDD), ADR-0078 (rules in shared template), ADR-0080 (contracts/readiness), ADR-0054 (replay discipline), ADR-0068 (versioning), ADR-0061 only for the separate engine package if confirmed, and applicable content, notebook, method-tier, manuscript, deploy, community and privacy rules. No exception is requested.

| ADR | Rule | Carried by |
|---|---|---|
| ADR-0070 | The App is a case workbench with Focus mode that retains case, method and unit selection. | `frontend/src/workbench/Workbench.tsx`, `npm run gate` |

## Proposed method and exact mathematical boundary

Let the hard QP be

`min_x 1/2 x^T Q x + q^T x` subject to `l <= A x <= u`,

where `Q` is symmetric positive semidefinite. A soft row introduces signed slack `xi` and penalty `Phi(xi)` under `l <= Ax + xi <= u`. For the proposed family, `Phi(xi) = sum_i phi_i(xi_i)`, where each `phi_i` is proper, closed, convex, has its minimum value zero at zero, and may have different positive- and negative-side slopes and curvature. The minimum-at-zero property implies each convex scalar penalty is nondecreasing moving away from zero on either ray.

For one interval `C=[l,u]` and residual `z=Ax`, minimize `phi(xi)` subject to `z+xi in C`. If `z` lies in `C`, `xi=0` is optimal. If `z>u`, feasible `xi` is negative and the optimum is the feasible value closest to zero, `xi=u-z`. If `z<l`, the optimum is `xi=l-z`. Therefore the eliminated cost is `g(z)=phi(Pi_C(z)-z)`, equivalently `phi(-R_C(z))` where `R_C(z)=z-Pi_C(z)`. This uses no evenness assumption; it is specific to coordinate-separable penalties and interval rows. The product must prove the vector value function is closed convex under the catalogued assumptions and check degenerate/infinite interval endpoints.

The generalized projection update candidate is `G(v)=Pi_C(v)+prox_{(phi composed with negation)/rho}(v-Pi_C(v))`, coordinatewise for separable penalties. For asymmetric piecewise elastic-net penalties, define

`phi(xi)=a_plus max(xi,0)+a_minus max(-xi,0)+0.5 b_plus max(xi,0)^2+0.5 b_minus max(-xi,0)^2`,

with all coefficients nonnegative. For `r=v-Pi_C(v)>0`, the returned offset is `max((rho*r-a_minus)/(rho+b_minus),0)`; this is the upper-bound violation branch because the original slack is negative. For `r<0`, it is `-max((rho*abs(r)-a_plus)/(rho+b_plus),0)`. Coefficients and sign conventions are fixed in one mathematical contract and independently tested against scalar minimization and explicit lifting before any engine code is accepted.

This is a derivation candidate, not a novelty result. A derivation sketch and source-level novelty search are recorded in the research dossier; a formal review must still establish the slack-elimination identity, convexity and closedness of the reduced term for all declared endpoints, proximal formula, ADMM assumptions and convergence, handling of hard/equality/fixed/free rows, numerical edge behavior, and prior-art boundary. If those fail, stop implementation of AAGSP and revise the proposed method before any product repository is created. Product release cannot list a protocol or benchmark as the beyond-current-method contribution. A method that fails to beat a relevant baseline remains reported as a negative result; a different method proposal would then be required before a qualified product release.

## Contracts and pipeline boundaries

The product's catalog will have one schema, example, producer check, consumer check, missing-data state, provider, and swap test per boundary. Candidate rows, versions initially `1.0.0`:

| Contract | Payload | Owner / validation |
|---|---|---|
| `case-spec` | Q, q, A, finite/infinite bounds, row kind, units, penalty family and coefficients, case metadata, provenance | case registry validates dimensions, convexity assumptions, finiteness and IDs; engine adapter independently validates accepted input |
| `run-request` | case ID plus typed parameter override, method ID and numerical settings | pipeline producer and method adapter validate against shared schema; reject unknown/NaN/out-of-range, never coerce |
| `run-manifest` | software/source pins, environment, seed/split, solver status, metrics, tolerances, compatibility, timing protocol, artifact hashes | bake validates all fields and artifact existence; reader verifies document and checksums |
| `solution-artifact` | primal/dual solution, signed and side-specific slacks, objective components, residuals, iteration/convergence trace summary | engine emits; independent checker recomputes original-space constraints/objective and validates same schema |
| `experiment-index` | named matrix rows, methods, case refs, status and excluded-cell reasons | experiment aggregator validates exact matrix coverage; web consumer rejects duplicate/missing required cells |
| `readiness` | row-wise state, provenance, missing/stale reasons | pipeline computes; frontend reads; absence never becomes zero or success |
| `export` | portable case, method result, provenance and checksum | export builder validates, schema test loads exported file from clean path |

States use the template vocabulary and explicitly distinguish `missing`, `partial`, `stale`, `provider`, `training` only if applicable, and `available`. A failed solver is a recorded result with failure status, not a missing row. An unsupported method-case pair has `incompatible` plus reason in the matrix, not an omitted cell. A stale artifact never silently renders as current. Schema changes require a version/history row and both producer/consumer tests.

Offline stages: ingest source/registry -> validate -> generate/pin seeds and splits -> solve each compatible method/case/settings -> independent oracle and residual checks -> aggregate held-out statistics -> export immutable artifacts -> validate inventory/checksums -> replay. Browser replay loads committed artifacts only. A browser live lane is optional and only admitted if complete solver code is bundleable, result parity is demonstrated, memory/payload limits pass, and per-case latency is within the measured product budget. No server lane is planned.

## Application, UI and deliverables

Instantiate current `CAOS_PRODUCT_TEMPLATE` exactly, use `@fasl-work/caos-app-shell` pinned exactly to the current adopted release, revalidated whenever the base changes, and follow the current template six-route contract: App, Introduction, Methodology, Implementation, Experiments, Benchmark. English and Spanish plus light and dark themes are release requirements. App opens on one selected case, provides real supported parameter edits, solve/compare, visible hard/soft row policy, side-specific violation chart, convergence/residual inspection and portable export. Cross-case selection and result matrices belong in Experiments/Benchmark. The page viewport is the app; keyboard access, focus behavior, empty/error/stale/incompatible states and responsive layouts are part of the measured gate.

Architecture modal: five bilingual, theme-aware tabs with complete product architecture and data-flow content. The `docs/` wiki is maintained in the same implementation units and contains method derivations, assumptions, API/contracts, reproducibility, licensing, data provenance, limitations, operations, and contribution guidance. Bilingual notebooks run from simple penalty semantics to published-method comparison and AAGSP falsification; numerical output is executed and checked, never placeholders. Final technical report is required. A separate proposed-method manuscript is prepared only if the method is correct, reproducible and scientifically interesting; otherwise the technical report records negative/inconclusive evidence. Manuscript authorship is reviewed explicitly before publication.

Six diffusion drafts are required by product coverage: executive problem context, two distinct notebook lessons, method/research story, and two further product areas. They remain unsubmitted files in the repository under the user's no-publication instruction.

## Requirements and release gates

Detailed EARS requirements and validation rows are created in the product repo from this accepted SDD before any feature code. Every requirement must point to an executable test/check or a named reproducible review artifact. Minimum feature groups and gates:

| Requirement group | Required proof |
|---|---|
| Problem context | executive schema, source/claim checks, EN/ES content and illustration audit |
| Case/penalty contract | adversarial schema and scalar/vector penalty oracle tests |
| Methods | each method acceptance gate and exact method-case coverage |
| Scientific pipeline | full offline ingest-to-export replay, checksums and fresh-environment run |
| Numerical correctness | independent objective/slack recomputation, KKT/hard-row checks, failure cases |
| Statistical evidence | preregistered held-out paired matrix, repeated runs and report completeness |
| Web app | shell gate, keyboard/focus/responsive/EN-ES/light-dark matrix and real interactions |
| Documentation/curriculum | notebook content audit and fresh-kernel execution in both languages, deep sourced wiki |
| Provenance/community | dependency/license notices, citations, data/license audit, template residue and content guards |
| Delivery | release manifest, artifact version/hash, deployment/live smoke and Zenodo report relation |

No requirement is accepted solely because it renders, builds, or returns HTTP 200. No full release is claimed until all method and case gates pass; no superiority claim until the held-out acceptance criterion passes.

## Beyond the state of the art

BS-1: AAGSP tests the hypothesis that a side-specific separable elastic penalty update can preserve OSQP's original KKT dimensions while improving setup/solve work against matched explicit lifting in a practitioner-relevant regime. The completed held-out comparison did not establish the registered timing improvement; BS-1 remains an unaccepted research hypothesis. The native implementation must include projection, objective, dual conjugate, scaling and recession behavior. An independent explicit-lift oracle, hard-row residual checks and paired measurements refute or support it. It cannot be described as novel or superior before the evidence and prior-art review justify that claim.

BS-2: The implemented SDK0.2 candidate prices disjoint directional group peaks while retaining original interval rows. The exact same objective already has a compact epigraph representation; linear shared prices also have an exact directional row-split generalized-projection reference. Row preservation is a representation property, not an expressibility or priority claim. Convexity, proximal slack elimination, fixed positive diagonal metric, relaxation alpha in(0,2), positive scales, nonempty closed soft boxes and an attained saddle point are the declared convergence scope. Hard rows remain separate. No variable metric or adaptive-relaxation theorem is asserted. Compatible epigraph stock-OSQP, directional row-split, direct/proximal DAQP variants and their limits are retained in the frozen protocol.

Primary sources: https://arxiv.org/abs/2610.35631 ; https://osqp.org/docs/solver/ ; https://darnstrom.github.io/daqp/start/advanced/soft ; https://openreview.net/pdf?id=HL3TvE4Afm .

UNVERIFIED: novelty, superiority, qualified product release, deployment and operational value; all require the declared gates. The complete catalog and registered experimental grid are executed and retained.

The Methodology page uses the documented `method-learned` floor waiver: the implemented method set is deterministic convex optimization and has no trained parameter policy. This does not waive any method implementation, comparison, mathematical-depth or executive-brief requirement. Deep FlexQP remains an availability-gated related method with distinct restoration semantics.

## Preregistered outcome and release stop

The complete experiment at app source `1a0c664` / engine `d0c69ed974d577ba02adbd4806332270d9425651` completed 456 instances with 11592 accepted measured observations, 7560 incompatible cells and no failed or accuracy-rejected observations. The primary endpoint had 168 accepted pairs over six evaluation seeds and no rejected pair. Median relative end-to-end reduction was 0.499839%, with 95% seed-cluster interval [-3.291967%, 3.944835%]. It did not meet the preregistered 10%/positive-interval criterion.

This is a negative comparative result. Preserve the exact protocol and complete raw observations under `data/derived/experiments/`. It does not establish timing superiority or global novelty. The approved strict stop/revise rule prevents promoting BS-1 as an accepted improved contribution or qualifying the product release on that hypothesis. Documentation, reproducible curriculum, package validation and the negative-result technical report continue; any different method proposal requires its own derivation, prior-art review and preregistered evaluation, rather than rewriting this endpoint.

The release requirements name published distribution `softqp==0.1.0`. The source archive and both wheels match tagged publishing workflow 41323753954. A fresh public-index Windows install passes all 94 native tests and license checks; all eight notebooks reproduce unchanged outputs using the public wheel and pass independent content review. The pipeline environment retains the historical engine source pin for the frozen experiment. These engineering gates do not change the rejected scientific endpoint.

## Independent coupled-study environment

The prospective coupled study uses a separate profile at `experiments/coupled-v1/requirements.txt`, governed by `docs/design/coupled-experiments-v1.json`. It consumes the public SoftQP 0.2.0 SDK. Product/runtime and reviewed legacy notebook requirements retain 0.1.0; historical executed outputs and the original pinned engine environment are preserved. The global technology table continues to govern the product environment. CI separately verifies every study pin against the protocol through `scripts/check_coupled_requirements.py`, and the study runtime verifies dependency versions plus exact public SDK Python/native identities. The separate environment is a scientific reproducibility boundary, not a second product package. Independent registration gates execution; complete independent artifact review establishes the integrity of the recorded result. Product qualification additionally requires the registered scientific criterion to pass.

The registered revision is complete: 48 development, 144 heldout and 18 robustness instances, retaining all 7770 observations and 210 canonical inputs. Independent replay checks 163390 returned candidate frames without a KKT rejection, while retaining backend iteration limits and supervised timeouts. The heldout paired reduction score is -212.449875%, with 95% seed-cluster interval [-225.336618%,-192.873759%] and nine failed pairs; the 10% criterion is not established. The [standalone coupled-study report](../../manuscripts/coupled-peak-study/README.md) records this negative result separately from the original study and app technical report. Evidence acceptance does not authorize qualified app promotion, deployment or a superiority claim.

## Directional coupled method scope



The registered primary has144heldoutinstances, sixseedclusters and ninefailedpairs. Its score−212.449874656751%,95%interval[−225.33661821558257%,−192.87375906532098%] fails the10%acceptance criterion. Both BS-1 and BS-2 remain unaccepted improvement hypotheses. The published negative manuscript covers BS-2 without declaring successful novelty, general superiority or a qualified product release. The additional EN/ES worked lesson executes the real public SDK2 through an explicit external process boundary, separated from the SDK1 kernel and frozen campaign. See coupled-lessons requirements and the coupled-study manuscript for derivations and honest evidence.

All 33 CAOS product requirements are traced to implemented specifications, real controls and explicit residuals in [the normative crosswalk](caos-requirements.md). This coverage map does not override either negative scientific outcome.
