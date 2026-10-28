# app/, DORMANT FastAPI backend

**This solution does not require a request-time backend at the moment.** The product is static
deterministic-replay (ADR-0054): the frontend loads the committed artifacts in `data/derived/` directly.

Activate this lane ONLY on an ADR-0002 trigger (server-side processing of uploaded data, auth-gated private data,
paid heavy compute). To activate: pin `requirements-api.txt`, install it, run `uvicorn app.main:app`. The
endpoints serve the SAME committed documents read-only and unchanged, a thin layer over `data/`, never a
re-implementation of the engine: `GET /api/cases` (the index), `GET /api/cases/{case_id}/manifest`,
`GET /api/artifacts/{path}` (any artifact a manifest names, by its path under `data/derived`), `GET /health`. They
read either form of contract 2 (one `artifact` or a list of `artifacts`) and nothing outside `data/derived`
(`tests/test_dormant_api.py`).
