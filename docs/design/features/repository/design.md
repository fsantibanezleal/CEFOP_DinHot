# Sequenced local workflow

One standard-library helper implements the four numbered steps; thin parallel shell entrypoints dispatch to it from their own location. A small checked-in JSON configuration declares environments, API activation, required artifacts and actual producer commands. Existing flat commands remain compatible.

Prerequisite checks accept Python 3.12 or newer and Node satisfying the matching package/lock range ^22.12.0 || ^24.0.0 || >=26.0.0; explicit system installation uses a supported platform package manager and never replaces compatible installed software. Initialization copies nonsecret example settings without evaluating dotenv text, preserves an existing file, and fingerprints recursive requirements and the npm lock before successful environment-local installation.

Generation requires an external CAOS_TEMP_ROOT. Each run owns a fresh stage with data/derived, models and checkpoints. Every producer destination is explicit, including measured outputs and ONNX/checkpoint paths. A narrow bridge calls existing producer APIs when a CLI lacks an output option; scientific sources and fingerprint inputs remain unchanged. Source caches use the configured external CAOS_DATA_ROOT. The staged metadata view uses the real catalog/schemas and VERSION for existing artifact/document validators and readiness computation.

Default generation never promotes. If initialization finds missing shipped artifacts, it runs the complete sandbox generation path and then names the explicit release-promotion command required before dev can consume the new set. Shipped complete artifacts need no downloads, fitting or generation.

Explicit release mode validates versions, complete catalog/index coverage, readiness and existing semantic/schema gates before replacing anything. A receipt binds the source/configuration and all staged payload bytes. Prepared incoming directories and backups are confined to the declared canonical target parents; multi-directory replacement rolls back every old target on failure. Checkpoint caches never become release payloads.

Development validates initialized dependencies and free loopback ports, then supervises the frontend plus the API only when configured active. It waits for API health, returns child failures and stops only its own process trees. Tests use fixture subprocesses, never real installation, training or release promotion. Final real initialized app launch remains a separate integration check.

Receipts bind recursive -r/-c pins and the current catalog/schema/validator identity; staged admission metadata
must match the checkout. The template readiness self-row exclusion is explicit configuration; OreFlow has none.
Rollback tries every target and retains all backups with exact recovery paths on incomplete restoration.
Development verifies primary and active API recursive requirements stamps before any preparation. Declared runtime
directory aliases may resolve externally; payload and recursive deletion paths cannot use that exception.
Standard subprocess.Popen starts each service in its own Windows console group or POSIX session. Cleanup
always targets that recorded group after leader exit; Windows also attempts the tracked PID/tree with taskkill.
Existing app-execution-base venvs remain supported. The existing base-integrity CI guard enforces tracked shell
mode100755. Native stdout/stderr and exit codes retain the existing subprocess.Popen behavior.

The supported existing venv is tested with an HTTP descendant that outlives its launcher and an independent
control server. A taskkill-only red probe and console-group green probe document the bounded Windows behavior;
neither probe installs or migrates a runtime.

Authored stage_inputs are copied byte-for-byte, bound into source receipt identity and compared again before
admission. They are authored inputs only (source tables, configuration): a version-stamped document, a JSON file whose
top-level object carries engine_version or product_version (trained models' metrics, a manifest, readiness), is produced by the
generation and never carried, so `authored_inputs` refuses it by name before any stage or generation command exists (on
generation and on the --from-stage admission alike; RP-030). Without it a product finds the stale stamp only when
validate_stage ends a full bake (CAOS_ChancaDEM 0.13.000, 97 minutes, #120). The template declares only params-record=partial and api=missing as exceptions to available states,
and requires scripts/check_readiness.py to recompute the actual producer document. Both validate_stage and
check_shipped use that same state admission and the template's real validator plan. Only read-only inventory
validation may target the bridge's own checkout; write modes retain external-stage containment.

Staged `product_version` values always match `VERSION`. Staged `engine_version` values do too unless one exact promoted
JSON path is listed in `stage_engine_versions`; that mapping binds the field to the package's exact version, and the
declared file must carry that stamp. The package-specific contract validator remains responsible for its other fields.
The original four-row params CSV and its two deliberate rejected
IDs remain intact; the five engine cases remain registry-derived. Missing manifests, artifacts or models cannot
use those exceptions. OreFlow declares no stage_inputs/readiness exceptions and retains strict17-row admission.

After shipped-data validation, development creates a separate environment dictionary for frontend_prepare
and frontend_command, applying only the explicit frontend_environment mapping and existing substitutions.
The template maps the legacy copy-data consumer's CAOS_DATA_ROOT to the validated local data/derived tree.
API/generation and the caller retain the global raw/model/temp roots; no storage contract is renamed. With no
declaration the environment values stay identical. The regression executes the actual Node copy-data consumer
and compares frontend, real HTTP child and generation environments in external fixtures. Product adoption of
this template-only follow-up waits for the owner's active smoke gate; no product file is changed here.

When `readiness_provider` is declared, shipped and staged admission delegates the product-specific readiness shape to
the guarded `readiness_check` in the product checkout. The provider receives the checkout or external stage being
judged. Template-only manifest-index, `contracts` inventory and catalog-hash assumptions are skipped for that lane;
required-path, source-identity, payload-hash, contract-metadata and configured validator checks remain active. The
default template lane retains its strict manifest and contract inventory checks. RP-032 covers the integration.
