# Deploy

One deploy place per product, decided at instantiation and written in `deploy/TARGET`; this template's is GitHub
Pages, a static site with no backend at request time (ADR-0055). `scripts/check_deploy_place.py` fails a product
that carries the files of two places.

## Before a deploy

Locally: the sandboxed pipeline tests, the canonical bake when the science changed, `npm run build`, `npm test`, and
`npm run gate`, which serves `dist/` as Pages would (no fallback) and walks every route, tab and case at five sizes,
in both themes and both languages. A person reads its captures (written under `frontend/`, in gate-output/shots): the gate measures,
it does not judge content.

## The deploy

`.github/workflows/deploy-pages.yml` runs after CI succeeds on `main`, on that same commit. It checks the committed
artifacts, builds the site with the right base path (`/` with a custom domain, `/<repository>/` without), deploys,
and then runs `scripts/check_live.py` against the live site: `build.json` names the pushed commit, every route
answers with the app with and without its trailing slash, a missing file answers 404, and the artifact index
answers JSON. It never trains, rebakes or recomputes (ADR-0069, ADR-0074).

After the deploy, run the gate against the deployed origin: `npm run gate -- --url https://<domain>`.

## CI

`.github/workflows/ci.yml`, on `develop` and `main`: lint, the workflow files parse, contract 2, the version, the
SDD, the deploy place; a web job (install, build, unit tests, the web baseline); and the guards (tracked secrets,
venvs, binaries, raw data, machine paths, template residue, document paths, content standards, the CI budget).
Every step runs under `bash -eo pipefail`.
