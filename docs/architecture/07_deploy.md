# Deploy

One deploy place per product, decided at instantiation and written in `deploy/TARGET`. DinHot's is **GitHub Pages** at `dinhot.fasl-work.com` (`frontend/public/CNAME`): a public repository, a static site, every artifact
committed, no secret and no server. ADR-0055 A55.1 names no VPS trigger: the compute is an FFT loop that the browser runs within the lane budget. `scripts/check_deploy_place.py` fails a product that carries the files of
two places. The deploy notes are [`deploy/pages.md`](../../deploy/pages.md).

Pages sends no cross-origin isolation headers (COOP and COEP), so the workers are single-threaded and `SharedArrayBuffer` is not used; the WebAssembly runtime of the learned models is self-hosted and runs one thread.

The previous service of DinHot (a FastAPI process on a VPS) is retired only after the Pages site answers over HTTPS and `scripts/check_live.py` is green against it; the old deploy script is never run after the new tree
reaches `main`. The DNS record is a CNAME from `dinhot` to the owner's `github.io` host, DNS only (not proxied), created by the owner.

## Before a deploy

Locally: the sandboxed pipeline tests, the canonical bake when the science changed, `npm run build`, `npm test` and `npm run gate`, which serves `dist/` as Pages would (no fallback) and walks every route, tab and case at
five sizes, in both themes and both languages. A person reads its captures (written under `frontend/`, in gate-output/shots): the gate measures, it does not judge content. The gate runs with Focus mode required (ADR-0070):
the workbench opens the open group of a case in the full viewport and returns to the same case, group and sub-view.

## The deploy

`.github/workflows/deploy-pages.yml` runs after CI succeeds on `main`, on that same commit. It checks the committed artifacts, builds the site with the right base path (`/` with a custom domain), deploys, and then runs
`scripts/check_live.py` against the live site: `build.json` names the pushed commit, every route answers with the app with and without its trailing slash, a missing file answers 404, and the artifact index answers JSON. It
never trains, rebakes or recomputes (ADR-0069, ADR-0074). The payload is at most 30 MB (the onnxruntime WebAssembly file is the largest), one Pages deploy in under 3 minutes.

After the deploy, run the gate against the deployed origin: `npm run gate -- --url https://dinhot.fasl-work.com`.

## CI

`.github/workflows/ci.yml`, on `develop` and `main`: lint, the workflow files parse, contract 2, the version, the SDD, the notebooks (static), the README areas, the deploy place and the technology matrix; a web job (install,
build, unit tests, the web baseline); and the guards (tracked secrets, venvs, binaries, raw data, machine paths, template residue, document paths, content standards, the CI budget). Every step runs under
`bash -eo pipefail`. No training, no bake and no pipeline test suite run in CI (ADR-0074): those run locally, and the plants of `tests/adversarial` also run in CI.
