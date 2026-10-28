"""GET-only endpoints serving the committed documents unchanged (read-only), as docs/contracts/api.openapi.json
declares. A document that does not exist yet, or exists but is not JSON, is a declared state: 503 with state missing
and its reason, never an empty body that looks like data and never a 500. No write paths."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ..services import content

router = APIRouter(prefix="/api")

NOT_BAKED = {"en": "The pipeline has not baked this build.", "es": "El pipeline no ha generado esta versión."}
NO_READINESS = {"en": "The readiness document is not in this build.",
                "es": "El documento de disponibilidad no está en esta versión."}


def _unavailable(reason: dict[str, str]) -> HTTPException:
    return HTTPException(status_code=503, detail={"state": "missing", "reason": reason})


def _unreadable(exc: content.Unreadable) -> HTTPException:
    return _unavailable({"en": f"The document {exc.rel} is unreadable.", "es": f"El documento {exc.rel} no se puede leer."})


@router.get("/cases")
def list_cases() -> Any:
    """The index (contract 2): every baked case and the path of its manifest."""
    try:
        index = content.load_index()
    except content.Unreadable as exc:
        raise _unreadable(exc) from exc
    if index is None:
        raise _unavailable(NOT_BAKED)
    return index


@router.get("/cases/{case_id}/manifest")
def get_manifest(case_id: str) -> Any:
    try:
        if content.load_index() is None:
            raise _unavailable(NOT_BAKED)
        m = content.load_manifest(case_id)
    except content.Unreadable as exc:
        raise _unreadable(exc) from exc
    if m is None:
        raise HTTPException(status_code=404, detail="unknown case")
    return m


@router.get("/artifacts/{rel_path:path}")
def get_artifact(rel_path: str) -> Any:
    """Any artifact a manifest names, by its path under data/derived (for example `<case>/<variant>.json`)."""
    try:
        art = content.load_artifact(rel_path)
    except content.Unreadable as exc:
        raise _unreadable(exc) from exc
    if art is None:
        raise HTTPException(status_code=404, detail="no such artifact")
    return art


@router.get("/readiness")
def get_readiness() -> Any:
    """What is real in this build: the committed readiness document, with the api row available."""
    try:
        doc = content.load_readiness()
    except content.Unreadable as exc:
        raise _unreadable(exc) from exc
    if doc is None:
        raise _unavailable(NO_READINESS)
    return doc
