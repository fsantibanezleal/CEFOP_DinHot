"""Catalog row api 1.0.0: the dormant FastAPI app serves every committed document as docs/contracts/api.openapi.json
declares, answers 503 with the declared state when a document is absent, 404 for an unknown case or artifact, and never
leaves the derived root. DATA_DIR selects the tree (the swap test runs the same assertions on the provider fixture tree
and on the bake)."""
from __future__ import annotations

import sys

import pytest
from contract_schemas import DERIVED_ROOTS, OPENAPI, ROOT, load_json, response_errors

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

sys.path.insert(0, str(ROOT))

UNAVAILABLE_INDEX = {"en": "The pipeline has not baked this build.", "es": "El pipeline no ha generado esta versión."}
UNAVAILABLE_READINESS = {"en": "The readiness document is not in this build.",
                         "es": "El documento de disponibilidad no está en esta versión."}


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
    """(routes the app serves, routes the OpenAPI ``document`` declares), each as (path, METHOD). The app's own generated
    schema lists every route the app serves (included routers are wrapped in fastapi 0.143); it is cached, so a route
    mounted after the first call needs the cache dropped."""
    app.openapi_schema = None
    served = {(p, m.upper()) for p, ops in app.openapi()["paths"].items() for m in ops}
    declared = {(p, m.upper()) for p, ops in document["paths"].items() for m in ops}
    return served, declared


def test_routes_match_the_openapi_document(monkeypatch, tmp_path):
    served, declared = route_sets(client(monkeypatch, tmp_path).app, load_json(OPENAPI))
    assert served == declared


def test_adversarial_an_undeclared_route_and_a_missing_route_fail_the_comparison(monkeypatch, tmp_path):
    document = load_json(OPENAPI)
    # a route the app serves and the document does not declare
    app = client(monkeypatch, tmp_path).app

    @app.get("/api/planted")
    def planted() -> dict:
        return {}

    served, declared = route_sets(app, document)
    assert served != declared and served - declared == {("/api/planted", "GET")}, (served - declared, declared - served)
    # a route the document declares and the app does not serve: a path removed from a copy of the document...
    app = client(monkeypatch, tmp_path).app
    path = "/api/cases"
    assert path in document["paths"], "the plant would remove nothing"
    shorter = {**document, "paths": {p: ops for p, ops in document["paths"].items() if p != path}}
    served, declared = route_sets(app, shorter)
    assert served != declared and {p for p, _ in served - declared} == {path}, (served - declared, declared - served)
    # ...and a path declared that the app never mounts
    longer = {**document, "paths": {**document["paths"], "/api/never-mounted": {"get": {}}}}
    served, declared = route_sets(app, longer)
    assert declared - served == {("/api/never-mounted", "GET")}, (served - declared, declared - served)


def assert_serves_everything(c: TestClient) -> int:
    assert get_checked(c, "/health", "/health", 200) == {"status": "ok"}
    get_checked(c, "/healthz", "/healthz", 200)
    index = get_checked(c, "/api/cases", "/api/cases", 200)
    assert index["cases"]
    n_artifacts = 0
    for e in index["cases"]:
        m = get_checked(c, f"/api/cases/{e['case_id']}/manifest", "/api/cases/{case_id}/manifest", 200)
        paths = [m["artifact"]["path"]] if "artifact" in m else [a["path"] for a in m["artifacts"]]
        for rel in paths:
            get_checked(c, f"/api/artifacts/{rel}", "/api/artifacts/{rel_path}", 200)
            n_artifacts += 1
    ready = get_checked(c, "/api/readiness", "/api/readiness", 200)
    api = next(e for e in ready["contracts"] if e["id"] == "api")
    assert (api["state"], api["provenance"], api["reason"]) == ("available", "real", None)
    return n_artifacts


def test_responses_match_the_openapi_document(monkeypatch):
    assert assert_serves_everything(client(monkeypatch, DERIVED_ROOTS["bake"])) >= 5


def test_swap_fixture_tree_and_bake(monkeypatch):
    for which in ("fixture", "bake"):
        assert assert_serves_everything(client(monkeypatch, DERIVED_ROOTS[which])) >= 1, which


def test_adversarial_503_when_documents_are_absent(monkeypatch, tmp_path):
    c = client(monkeypatch, tmp_path)
    for path, template, reason in (("/api/cases", "/api/cases", UNAVAILABLE_INDEX),
                                   ("/api/cases/EX01_subcritical/manifest", "/api/cases/{case_id}/manifest",
                                    UNAVAILABLE_INDEX),
                                   ("/api/readiness", "/api/readiness", UNAVAILABLE_READINESS)):
        body = get_checked(c, path, template, 503)
        assert body == {"detail": {"state": "missing", "reason": reason}}, path
    assert "cases" not in c.get("/api/cases").json()  # never the old empty-index body


def test_adversarial_404_bodies_and_nothing_outside_the_root(monkeypatch):
    c = client(monkeypatch, DERIVED_ROOTS["bake"])
    assert get_checked(c, "/api/cases/NOPE/manifest", "/api/cases/{case_id}/manifest", 404) == {"detail": "unknown case"}
    for bad in ("..%5Cindex", ".hidden", "..", "%2e%2e"):
        r = c.get(f"/api/cases/{bad}/manifest")
        assert r.status_code == 404 and response_errors("/api/cases/{case_id}/manifest", "get", 404, r.json()) == [], bad
    for rel in ("EX01_subcritical/nope.json", "../../VERSION", "..%2F..%2FVERSION", "%2e%2e/%2e%2e/package.json",
                "..%5C..%5CVERSION", "manifests/..%2F..%2F..%2FVERSION", "manifests/.gitkeep", "manifests",
                "EX01_subcritical", "readiness.json.txt"):
        r = c.get(f"/api/artifacts/{rel}")
        assert r.status_code == 404, rel
        assert r.json() == {"detail": "no such artifact"} or response_errors(
            "/api/artifacts/{rel_path}", "get", 404, r.json()) == [], rel
    assert c.get("/api/artifacts/EX01_subcritical/trace.json").status_code == 200


def test_get_only(monkeypatch):
    c = client(monkeypatch, DERIVED_ROOTS["bake"])
    for method in ("post", "put", "patch", "delete"):
        assert getattr(c, method)("/api/cases").status_code == 405, method


def test_adversarial_only_indexed_documents_are_served(monkeypatch):
    """The declared bodies of /api/artifacts are traces and of /api/cases/{id}/manifest manifests: a document that is
    neither (the readiness, the index, a manifest read as an artifact, the index read as a case) is a 404."""
    c = client(monkeypatch, DERIVED_ROOTS["bake"])
    for rel in ("readiness.json", "manifests/index.json", "manifests/EX02_epidemic.json"):
        body = get_checked(c, f"/api/artifacts/{rel}", "/api/artifacts/{rel_path}", 404)
        assert body == {"detail": "no such artifact"}, rel
    body = get_checked(c, "/api/cases/index/manifest", "/api/cases/{case_id}/manifest", 404)
    assert body == {"detail": "unknown case"}


def test_every_document_under_the_root_is_served_as_declared_or_404(monkeypatch):
    """No path under data/derived answers 200 with a body that fails the OpenAPI response schema."""
    c = client(monkeypatch, DERIVED_ROOTS["bake"])
    for p in sorted(DERIVED_ROOTS["bake"].rglob("*.json")):
        rel = p.relative_to(DERIVED_ROOTS["bake"]).as_posix()
        r = c.get(f"/api/artifacts/{rel}")
        assert r.status_code in (200, 404), rel
        assert response_errors("/api/artifacts/{rel_path}", "get", r.status_code, r.json()) == [], rel
        stem = p.stem
        r = c.get(f"/api/cases/{stem}/manifest")
        assert r.status_code in (200, 404), stem
        assert response_errors("/api/cases/{case_id}/manifest", "get", r.status_code, r.json()) == [], stem


def corrupt_copy(tmp_path, rel: str):
    """A copy of the bake with the document ``rel`` replaced by text that is not JSON."""
    import shutil

    root = tmp_path / "derived"
    shutil.copytree(DERIVED_ROOTS["bake"], root)
    (root / rel).write_text("{not json", encoding="utf-8")
    return root


def unreadable(rel: str) -> dict:
    return {"detail": {"state": "missing", "reason": {"en": f"The document {rel} is unreadable.",
                                                      "es": f"El documento {rel} no se puede leer."}}}


def test_adversarial_an_unreadable_index_is_a_503(monkeypatch, tmp_path):
    c = client(monkeypatch, corrupt_copy(tmp_path, "manifests/index.json"))
    for path, template in (("/api/cases", "/api/cases"), ("/api/cases/EX01_subcritical/manifest", "/api/cases/{case_id}/manifest"),
                           ("/api/artifacts/EX01_subcritical/trace.json", "/api/cases")):  # see the note below
        assert get_checked(c, path, template, 503) == unreadable("manifests/index.json"), path


def test_an_unreadable_manifest_is_a_503(monkeypatch, tmp_path):
    c = client(monkeypatch, corrupt_copy(tmp_path, "manifests/EX01_subcritical.json"))
    body = get_checked(c, "/api/cases/EX01_subcritical/manifest", "/api/cases/{case_id}/manifest", 503)
    assert body == unreadable("manifests/EX01_subcritical.json")
    assert c.get("/api/cases/EX02_epidemic/manifest").status_code == 200  # the other cases work


def test_an_unreadable_artifact_is_a_503(monkeypatch, tmp_path):
    c = client(monkeypatch, corrupt_copy(tmp_path, "EX01_subcritical/trace.json"))
    # api.openapi.json declares no 503 for /api/artifacts/{rel_path} (a docs gap reported to the main session): the
    # body is held to the Unavailable response every other route declares
    body = get_checked(c, "/api/artifacts/EX01_subcritical/trace.json", "/api/cases", 503)
    assert body == unreadable("EX01_subcritical/trace.json")


def test_an_unreadable_readiness_is_a_503(monkeypatch, tmp_path):
    c = client(monkeypatch, corrupt_copy(tmp_path, "readiness.json"))
    body = get_checked(c, "/api/readiness", "/api/readiness", 503)
    assert body == unreadable("readiness.json")
