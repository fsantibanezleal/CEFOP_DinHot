"""Catalog row api 1.0.0: the dormant FastAPI app serves every committed document as docs/contracts/api.openapi.json declares,
answers 503 with the declared state when a document is absent or unreadable, 404 for an unknown case or artifact, and never leaves
the derived root. DATA_DIR selects the tree (the swap test runs the same assertions on the provider fixture tree and on a bake)."""
from __future__ import annotations

import shutil
import sys

import pytest
from contract_schemas import DERIVED_ROOTS, OPENAPI, ROOT, load_json, response_errors

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

sys.path.insert(0, str(ROOT))

NOT_BAKED = {"en": "The pipeline has not baked this build.", "es": "El pipeline no ha generado esta versión."}
NO_READINESS = {"en": "The readiness document is not in this build.", "es": "El documento de disponibilidad no está en esta versión."}
NO_BENCHMARK = {"en": "The benchmark has not run for this build.", "es": "El benchmark no se ha ejecutado para esta versión."}
NO_METRICS = {"en": "The model metrics have not been computed for this build.",
              "es": "Las métricas de los modelos no se han calculado para esta versión."}


def client(monkeypatch: pytest.MonkeyPatch, data_dir) -> TestClient:
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    from app.main import create_app

    return TestClient(create_app())


def get_checked(c: TestClient, path: str, template: str, expect: int):
    """GET ``path``, require ``expect`` and the body the OpenAPI document declares for ``template``."""
    r = c.get(path)
    assert r.status_code == expect, f"{path}: {r.status_code} {r.text[:200]}"
    body = r.json()
    assert response_errors(template, "get", expect, body) == [], path
    return body


def route_sets(app, document: dict) -> tuple[set, set]:
    app.openapi_schema = None
    served = {(p, m.upper()) for p, ops in app.openapi()["paths"].items() for m in ops}
    declared = {(p, m.upper()) for p, ops in document["paths"].items() for m in ops}
    return served, declared


def test_routes_match_the_openapi_document(monkeypatch, tmp_path):
    served, declared = route_sets(client(monkeypatch, tmp_path).app, load_json(OPENAPI))
    assert served == declared and ("/api/benchmark", "GET") in served and ("/api/models/metrics", "GET") in served


def test_adversarial_an_undeclared_route_and_a_missing_route_fail_the_comparison(monkeypatch, tmp_path):
    document = load_json(OPENAPI)
    app = client(monkeypatch, tmp_path).app

    @app.get("/api/planted")
    def planted() -> dict:
        return {}

    served, declared = route_sets(app, document)
    assert served - declared == {("/api/planted", "GET")}
    app = client(monkeypatch, tmp_path).app
    shorter = {**document, "paths": {p: ops for p, ops in document["paths"].items() if p != "/api/benchmark"}}
    served, declared = route_sets(app, shorter)
    assert {p for p, _ in served - declared} == {"/api/benchmark"}


def assert_serves_everything(c: TestClient, benchmark: int, metrics: int) -> int:
    assert get_checked(c, "/health", "/health", 200) == {"status": "ok"}
    get_checked(c, "/healthz", "/healthz", 200)
    index = get_checked(c, "/api/cases", "/api/cases", 200)
    assert index["cases"]
    n_artifacts = 0
    for e in index["cases"]:
        if e["status"] == "refused":
            get_checked(c, f"/api/cases/{e['case_id']}/manifest", "/api/cases/{case_id}/manifest", 404)
            continue
        m = get_checked(c, f"/api/cases/{e['case_id']}/manifest", "/api/cases/{case_id}/manifest", 200)
        get_checked(c, f"/api/artifacts/{m['artifact']['path']}", "/api/artifacts/{rel_path}", 200)
        n_artifacts += 1
    get_checked(c, "/api/benchmark", "/api/benchmark", benchmark)
    get_checked(c, "/api/models/metrics", "/api/models/metrics", metrics)
    ready = get_checked(c, "/api/readiness", "/api/readiness", 200)
    api = next(e for e in ready["contracts"] if e["id"] == "api")
    assert (api["state"], api["provenance"], api["reason"]) == ("available", "real", None)
    return n_artifacts


def test_responses_match_the_openapi_document(monkeypatch, sandbox_bake):
    assert assert_serves_everything(client(monkeypatch, sandbox_bake[0]), benchmark=503, metrics=503) == 3


def test_swap_fixture_tree_and_bake(monkeypatch, sandbox_bake):
    assert assert_serves_everything(client(monkeypatch, DERIVED_ROOTS["fixture"]), 200, 200) >= 1
    assert assert_serves_everything(client(monkeypatch, sandbox_bake[0]), 503, 503) >= 1
    if (DERIVED_ROOTS["bake"] / "manifests" / "index.json").is_file():
        has_b = (DERIVED_ROOTS["bake"] / "benchmark" / "results.json").is_file()
        has_m = (DERIVED_ROOTS["bake"] / "models" / "metrics.json").is_file()
        assert assert_serves_everything(client(monkeypatch, DERIVED_ROOTS["bake"]), 200 if has_b else 503, 200 if has_m else 503) >= 1


def test_adversarial_503_when_documents_are_absent(monkeypatch, tmp_path):
    c = client(monkeypatch, tmp_path)
    for path, template, reason in (("/api/cases", "/api/cases", NOT_BAKED),
                                   ("/api/cases/C01_square_grid/manifest", "/api/cases/{case_id}/manifest", NOT_BAKED),
                                   ("/api/benchmark", "/api/benchmark", NO_BENCHMARK),
                                   ("/api/models/metrics", "/api/models/metrics", NO_METRICS),
                                   ("/api/readiness", "/api/readiness", NO_READINESS)):
        body = get_checked(c, path, template, 503)
        assert body == {"detail": {"state": "missing", "reason": reason}}, path
    assert "cases" not in c.get("/api/cases").json()


def test_adversarial_404_bodies_and_nothing_outside_the_root(monkeypatch, sandbox_bake):
    c = client(monkeypatch, sandbox_bake[0])
    assert get_checked(c, "/api/cases/NOPE/manifest", "/api/cases/{case_id}/manifest", 404) == {"detail": "unknown case"}
    for bad in ("..%5Cindex", ".hidden", "..", "%2e%2e"):
        r = c.get(f"/api/cases/{bad}/manifest")
        assert r.status_code == 404 and response_errors("/api/cases/{case_id}/manifest", "get", 404, r.json()) == [], bad
    for rel in ("C91_mini/nope.json", "../../VERSION", "..%2F..%2FVERSION", "%2e%2e/%2e%2e/package.json",
                "..%5C..%5CVERSION", "manifests/..%2F..%2F..%2FVERSION", "manifests", "C91_mini", "readiness.json.txt"):
        r = c.get(f"/api/artifacts/{rel}")
        assert r.status_code == 404, rel
    assert c.get("/api/artifacts/C91_mini/trace.json").status_code == 200


def test_get_only(monkeypatch, sandbox_bake):
    c = client(monkeypatch, sandbox_bake[0])
    for method in ("post", "put", "patch", "delete"):
        assert getattr(c, method)("/api/cases").status_code == 405, method


def test_adversarial_only_indexed_documents_are_served(monkeypatch, sandbox_bake):
    """Only traces are artifacts and only manifests are manifests: the readiness, the index, a manifest read as an artifact, the
    index read as a case, and a refused case are 404."""
    c = client(monkeypatch, sandbox_bake[0])
    for rel in ("readiness.json", "manifests/index.json", "manifests/C91_mini.json"):
        assert get_checked(c, f"/api/artifacts/{rel}", "/api/artifacts/{rel_path}", 404) == {"detail": "no such artifact"}, rel
    assert get_checked(c, "/api/cases/index/manifest", "/api/cases/{case_id}/manifest", 404) == {"detail": "unknown case"}
    assert get_checked(c, "/api/cases/C94_far/manifest", "/api/cases/{case_id}/manifest", 404) == {"detail": "unknown case"}


def corrupt_copy(tmp_path, source, rel: str):
    root = tmp_path / "derived"
    shutil.copytree(source, root)
    (root / rel).write_text("{not json", encoding="utf-8")
    return root


def unreadable(rel: str) -> dict:
    return {"detail": {"state": "missing", "reason": {"en": f"The document {rel} is unreadable.",
                                                      "es": f"El documento {rel} no se puede leer."}}}


def test_adversarial_unreadable_documents_are_a_503(monkeypatch, tmp_path, sandbox_bake):
    src = sandbox_bake[0]
    cases = (("manifests/index.json", "/api/cases", "/api/cases"),
             ("manifests/C91_mini.json", "/api/cases/C91_mini/manifest", "/api/cases/{case_id}/manifest"),
             ("C91_mini/trace.json", "/api/artifacts/C91_mini/trace.json", "/api/artifacts/{rel_path}"),
             ("readiness.json", "/api/readiness", "/api/readiness"))
    for i, (rel, path, template) in enumerate(cases):
        c = client(monkeypatch, corrupt_copy(tmp_path / str(i), src, rel))
        assert get_checked(c, path, template, 503) == unreadable(rel), rel
    c = client(monkeypatch, corrupt_copy(tmp_path / "m", src, "manifests/C91_mini.json"))
    assert c.get("/api/cases/C92_disc/manifest").status_code == 200       # the other cases work
