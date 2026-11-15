# Local workflow

Run commands from any directory using the entrypoint's absolute path, or from the repository root as below.
The numbered steps share workflow.py and the declarative workflow.json. The flat setup/dev/precompute entrypoints forward to the same helper. Flat precompute now also stages externally; only --release/-Release requests local artifact replacement.

## 00: system prerequisites

PowerShell: ./scripts/local/00_install-prereqs.ps1

Bash: bash scripts/local/00_install-prereqs.sh

The default checks Python>=3.12, Node ^22.12.0 || ^24.0.0 || >=26.0.0 and git. Newer compatible installations are accepted.
Only -Install / --install requests installation of missing prerequisites, through winget on Windows or Homebrew
where available. Otherwise the command explains the manual repair. No global Python package is installed.
PYTHON can select an existing interpreter path, including one containing spaces.

## 01: initialize

PowerShell: ./scripts/local/01_init.ps1

Bash: bash scripts/local/01_init.sh

Initialization copies nonsecret .env.example defaults only if .env is absent. Existing .env bytes are preserved;
dotenv assignments are literal values, never shell commands. Exported process variables take precedence.
Set an absolute external CAOS_VENVS_ROOT in the process environment or an existing .env before initialization.
Declared runtimes are provisioned at CAOS_VENVS_ROOT/environment_namespace/runtime; instantiate writes the product slug
as the namespace. There is no repository or system-temp fallback. Missing, internal, redirected or non-directory
targets refuse before .env creation or dependency installation. Runtime lookup creates nothing. Existing repository
aliases are accepted only when they resolve to the exact declared external runtime. Historical internal environments
must be preserved separately; initialization never moves or overwrites them.

Declared external venvs and locked frontend dependencies are provisioned. Recursive requirements and package-lock
fingerprints are stamped only after a successful install; a matching installation is reused. A failed native
process is a failure, while successful native stderr warnings remain warnings.

Optional -Notebooks / --notebooks provisions the notebook environment. See the product notes below for the optional GPU lane.
Complete shipped artifacts avoid acquisition or generation. If required artifacts are genuinely absent, initialization
runs the complete external sandbox generation path and reports the explicit promotion command needed before dev.
It never silently replaces committed artifacts or starts a science bake as part of an ordinary complete checkout.

## 02: external data generation and explicit promotion

Configure CAOS_TEMP_ROOT as an external scratch root before generation. No system-temp or repository fallback is used.
PowerShell: ./scripts/local/02_generate-data.ps1

Bash: bash scripts/local/02_generate-data.sh

Each invocation creates a fresh external caos-local-* stage. All measured summaries, process records, exported models
and local checkpoints remain there. The complete real producer plan is in workflow.json; no stage inherits a
repository output default. Pinned source caches, when needed, use external CAOS_DATA_ROOT. This operation can be
expensive and may require source acquisition and generation dependencies; opening shipped artifacts does not.

After generation, the command prints the stage and next command. Promotion requires explicit intent:

PowerShell: ./scripts/local/02_generate-data.ps1 -Release -FromStage '<external stage>'

Bash: bash scripts/local/02_generate-data.sh --release --from-stage '<external stage>'

Without a supplied stage, explicit release mode first generates a fresh complete stage. It rechecks current source
and payload fingerprints, versions, whole catalog/readiness, and the existing semantic/schema validators before
replacement. Mixed, partial, changed or invalid candidates cannot replace old files. Prepared incoming trees and
backups support rollback if any artifact/model-directory promotion fails. Every recoverable target is attempted;
if restoration fails, the error names original and restoration failures and all retained recovery paths.
Preserve those paths until recovery is complete; never delete backups merely to silence an error. Checkpoints are never release payloads.
Here release means local artifact promotion; it creates no Git tag, software release, deployment or publication.

## 03: development services

PowerShell: ./scripts/local/03_dev.ps1

Bash: bash scripts/local/03_dev.sh

The helper verifies initialized dependencies, the frontend lock fingerprint, shipped artifacts and free loopback
ports. It runs the existing frontend predev copy, starts Vite directly, and supervises an active API where declared.
The API must answer health before the frontend starts. Child failure exits nonzero; Ctrl+C stops only this
workflow's process trees. It does not kill a pre-existing process or install dependencies during startup.

## Checks

Run the focused behavioral suite with the initialized pipeline interpreter:

python -m pytest tests/test_local_bootstrap.py tests/test_bootstrap_regressions.py tests/test_bootstrap_admission.py -q

The fixtures execute fake producers and local HTTP/frontend subprocesses in external temporary repositories,
not training or release promotion in this checkout. Use the existing smoke scripts for the full product gates.
Actual installed app launch, API operations, release publication and deployment require their own observed receipts.

## Template defaults

The API is dormant while requirements-api.txt contains only comments. The required .venv-pipeline holds
precompute/development pins; activating API requirements also provisions .venv and starts that runtime.
The frontend listens on5173 and an activated API defaults to8000. Generation uses the real example pipeline,
normalizes its nested sandbox models into the release model tree and checks the complete registry.


## Admission and runtime details

Receipts bind recursive requirement/constraint files, current contract catalog and schemas, producer code,
validator scripts and schema registry, plus every payload byte. Admission refuses a stale staged catalog
or a source change during generation. Readiness requires the exact producer inventory: the template excludes
its own readiness row (six rows); OreFlow includes it (17 rows). Shipped readiness must bind the current catalog.

Declared ignored venv directory aliases may point outside the checkout. Initialization and generation use
those aliases; missing interpreter errors retain the declared path and resolved cause. Artifact destinations,
stages and recursive cleanup retain their separate strict containment checks. Recursive cleanup refuses junctions
and symlinks before deletion.

Development compares current recursive Python requirement fingerprints for both the primary and active API
runtimes before frontend preparation. It never repairs dependencies implicitly. Windows service trees use
their own console process groups. Cleanup signals the recorded group even after its leader exits, and always
attempts taskkill on the tracked PID/tree. POSIX cleanup likewise addresses the owned process group after
leader exit. Existing venvs, including Windows app-execution base aliases, remain supported. No broad
process-name cleanup or environment migration is used.

The template's frontend_environment declaration selects the already-validated local data/derived tree for
the legacy copy-data consumer via a frontend-only CAOS_DATA_ROOT overlay. That consumer interprets the variable
as compact web data; the global storage contract still uses it for raw data. Only frontend preparation and
startup receive the overlay. API and generation retain the original global storage environment, including
CAOS_DATA_ROOT, CAOS_MODELS_ROOT and CAOS_TEMP_ROOT. The caller's environment is never mutated. Without an
explicit frontend_environment declaration, existing consumer/environment selection remains unchanged.

The existing CI base-integrity guard checks Git index mode100755 for every tracked .sh file, including old
and new entrypoints. File executable bits on a Windows filesystem do not replace this index check.

## Authored inputs and template readiness

The template stages the exact authored data/examples/params.csv as a source input. Its bytes join the source
receipt identity and must still match during admission. The table intentionally has four rows: two accepted
and two rejected by contract1. No rows are stripped or coerced. The five solved cases come from the registry;
the table is an input-admission teaching example, not the source of those five registry parameterizations.

Complete template generation requires all five registry cases, artifacts and the released model at the current
version. It preserves the distinct declared outcomes: params-record is partial with bad_i0_gt_N and bad_negbeta;
the static API row is missing with the producer's dormant-lane reason. Those two row-specific exceptions require
the existing check_readiness.py to recompute and compare the complete current document, including source facts,
reasons, rejected IDs, catalog identity and bytes. Admission never rewrites readiness. Shipped-data checks use
the same policy and the real registry/artifact/document validators. The bridge may inspect its own checkout
only in read-only template-validate mode; write-capable bridge modes still require an external stage.
Missing/partial derived outputs remain refused; OreFlow retains its strict17-row admission and
does not inherit either template exception. Stage inputs are not promoted over authored source files.
