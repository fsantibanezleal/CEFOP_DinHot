"""Read the committed documents (index, manifests, artifacts, readiness) as they are. Read-only, path-traversal guarded.

Only what the index lists is served: a manifest of an indexed case, an artifact an indexed manifest names (never the
index, the readiness or a manifest as an "artifact"), so no route answers with a body its OpenAPI response does not
declare. A document that exists but is not JSON raises ``Unreadable``, which the router answers as a declared 503.

Nothing here knows a product's manifest shape beyond contract 2's two forms: one artifact (`artifact: {path}` at the
manifest's top level) or several (`artifacts: [{path, ...}]`, one per variant). The documents are served unchanged;
their shapes are checked by scripts/check_artifacts.py and the web's contract test, never re-declared here.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import REPO_ROOT, Settings


class Unreadable(Exception):
    """A committed document exists but cannot be read as JSON; ``rel`` is its path under the derived root."""

    def __init__(self, rel: str) -> None:
        super().__init__(rel)
        self.rel = rel


def _derived() -> Path:
    return (REPO_ROOT / Settings().data_dir).resolve()


def _read(rel: str) -> Any | None:
    """A committed JSON document under the derived root, or None (missing, or outside the root). Raises ``Unreadable``
    when the file is there but is not valid JSON."""
    root = _derived()
    p = (root / rel).resolve()
    if p.suffix != ".json" or (p != root and root not in p.parents) or not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:  # ValueError covers a JSON syntax error and bytes that are not UTF-8
        raise Unreadable(rel) from exc


def load_index() -> dict | None:
    """The case index, or None when the pipeline has not baked this build (never a stand-in body)."""
    return _read("manifests/index.json")


def load_readiness() -> dict | None:
    """The committed readiness document with the api row set to available (the API answering is the evidence), or
    None when the document is absent. The row's status becomes real too: the schema forbids provenance real under
    status active, and the app answering is the real producer of the api row."""
    doc = _read("readiness.json")
    if doc is None:
        return None
    for entry in doc.get("contracts", []):
        if entry.get("id") == "api":
            entry.update(status="real", state="available", provenance="real", reason=None, missing=[])
    return doc


def _entries() -> list[dict]:
    index = load_index()
    cases = index.get("cases", []) if isinstance(index, dict) else []
    return [e for e in cases if isinstance(e, dict) and isinstance(e.get("manifest_path"), str)]


def load_manifest(case_id: str) -> dict | None:
    """The manifest of an indexed case, or None for any other id (the index itself, a path, a case not baked)."""
    for entry in _entries():
        if entry.get("case_id") == case_id:
            return _read(entry["manifest_path"])
    return None


def artifact_paths(manifest: dict) -> list[str]:
    """The artifact paths a manifest names, in either form of contract 2."""
    if isinstance(manifest.get("artifacts"), list):
        return [a["path"] for a in manifest["artifacts"] if isinstance(a, dict) and "path" in a]
    single = manifest.get("artifact")
    return [single["path"]] if isinstance(single, dict) and "path" in single else []


def load_artifact(rel: str) -> Any | None:
    """An artifact some indexed manifest names, by exactly that path, or None. A manifest that cannot be read names
    nothing here (it is reported on its own route)."""
    for entry in _entries():
        try:
            manifest = _read(entry["manifest_path"])
        except Unreadable:
            continue
        if isinstance(manifest, dict) and rel in artifact_paths(manifest):
            return _read(rel)
    return None
