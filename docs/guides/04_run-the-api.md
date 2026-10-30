# Guide: run the API (dormant by default)

The `app/` FastAPI backend is **dormant**: DinHot is a static deterministic-replay product, and no ADR-0002 trigger applies (no server-side processing of uploaded data, no auth-gated data, no paid heavy compute).
It is a read-only layer over `data/derived`, kept so that the contract of the API is tested.

To run it locally:

1. Pin the dependencies in `requirements-api.txt` and run `scripts/setup.sh` (or `setup.ps1`), which then creates `.venv` with them.
2. `uvicorn app.main:app --reload` (or `scripts/dev.sh` / `scripts/dev.ps1`, which start it when `app/` is active).

Endpoints, all GET (the OpenAPI 3.1 document is `docs/contracts/api.openapi.json`):

| Route | Serves |
|---|---|
| `/health`, `/healthz` | liveness |
| `/api/cases` | the case index |
| `/api/cases/{case_id}/manifest` | one case manifest (404 for a case that is listed but has none, such as a refused case) |
| `/api/artifacts/{rel_path}` | a committed artifact (a trace) |
| `/api/benchmark` | the benchmark results |
| `/api/models/metrics` | the held-out metrics of the two model slots |
| `/api/readiness` | the readiness document, with the `api` row set to available |

A document that does not exist yet is a declared state: the answer is **503 with the state and the reason**, never an empty body that looks like data. The API serves the same committed documents read-only and unchanged,
a thin layer over `data/`, never a re-implementation of the engine. `DATA_DIR` can point it at the provider tree (`docs/contracts/fixtures/data/derived`) for a walking skeleton.

Keep the data-pipeline and contract discipline even with a backend: the API serves what the pipeline baked. Deploy through the dormant VPS templates in `deploy/` only if an ADR-0002 trigger ever applies.
