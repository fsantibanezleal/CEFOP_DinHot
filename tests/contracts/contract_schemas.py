"""Schema access for the contract tests (docs/contracts/catalog.md): every catalog schema file and the OpenAPI
document, validated with jsonschema (Draft 2020-12) through one referencing registry, so an OpenAPI component that
points at a schema file resolves to that same file. The schema files are the single source of every contract; no
test re-declares a shape."""
from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "docs" / "contracts"
SCHEMAS = CONTRACTS / "schemas"
OPENAPI = CONTRACTS / "api.openapi.json"
# the provider tree mirrors the repository layout: <root>/data/derived and <root>/data/examples
FIXTURE_ROOT = CONTRACTS / "fixtures"
DERIVED_ROOTS = {"bake": ROOT / "data" / "derived", "fixture": FIXTURE_ROOT / "data" / "derived"}

BASE = "https://contracts.invalid/"  # a base URI only; nothing is fetched


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def registry() -> Registry:
    """Every schema file at BASE/schemas/<file> and the OpenAPI document at BASE/api.openapi.json."""
    resources = [(f"{BASE}schemas/{f.name}", Resource.from_contents(load_json(f), default_specification=DRAFT202012))
                 for f in sorted(SCHEMAS.glob("*.schema.json"))]
    resources.append((f"{BASE}api.openapi.json", Resource.from_contents(load_json(OPENAPI), default_specification=DRAFT202012)))
    return Registry().with_resources(resources)


def _validator_for(ref: str) -> Draft202012Validator:
    return Draft202012Validator({"$schema": "https://json-schema.org/draft/2020-12/schema", "$ref": ref},
                                registry=registry())


@lru_cache(maxsize=None)
def validator(name: str) -> Draft202012Validator:
    """The validator of docs/contracts/schemas/<name>.schema.json (the schema itself is checked first)."""
    path = SCHEMAS / f"{name}.schema.json"
    Draft202012Validator.check_schema(load_json(path))
    return _validator_for(f"{BASE}schemas/{path.name}")


def errors(name: str, instance: Any) -> list[str]:
    """Every way ``instance`` departs from schema ``name``, as ``path: message``; empty when it conforms."""
    return _messages(validator(name), instance)


def _messages(v: Draft202012Validator, instance: Any) -> list[str]:
    found = sorted(v.iter_errors(instance), key=lambda e: [str(p) for p in e.absolute_path])
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '$'}: {e.message}" for e in found]


def component_errors(name: str, instance: Any) -> list[str]:
    """Every way ``instance`` departs from the OpenAPI component ``name`` (for example UnavailableBody)."""
    return _messages(_validator_for(f"{BASE}api.openapi.json#/components/schemas/{name}"), instance)


def _escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


@lru_cache(maxsize=None)
def response_validator(path: str, method: str, status: int) -> Draft202012Validator:
    """The validator of the JSON body the OpenAPI document declares for ``method path`` answering ``status``.

    A response given as ``{"$ref": "#/components/responses/X"}`` is followed; the body schema's own references
    (components, schema files) resolve through the registry."""
    doc = load_json(OPENAPI)
    response = doc["paths"][path][method.lower()]["responses"][str(status)]
    pointer = "/" + "/".join(_escape(t) for t in ("paths", path, method.lower(), "responses", str(status)))
    if "$ref" in response:
        ref = response["$ref"]
        if not ref.startswith("#/"):
            raise ValueError(f"{method} {path} {status}: only local response references are supported, got {ref}")
        pointer = ref[1:]
    return _validator_for(f"{BASE}api.openapi.json#{pointer}/content/application~1json/schema")


def response_errors(path: str, method: str, status: int, body: Any) -> list[str]:
    """Every way ``body`` departs from the response the OpenAPI document declares; empty when it conforms."""
    return _messages(response_validator(path, method, status), body)


def edit(path: Path, change) -> None:
    """Load a committed JSON document, change it, write it back compact (the plant of the document-guard tests)."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    change(doc)
    path.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")


NO_NUMPY = ("import sys, runpy; sys.modules['numpy'] = None; path = sys.argv[1]; sys.argv = sys.argv[1:]; "
            "runpy.run_path(path, run_name='__main__')")


def run_readiness_guard(root: Path | None = None, *, no_numpy: bool = False) -> subprocess.CompletedProcess:
    """Run the readiness guard as CI does, on the repository or on a copy; ``no_numpy`` makes ``import numpy`` fail first."""
    script = str(ROOT / "scripts" / "check_readiness.py")
    args = [str(root)] if root else []
    cmd = [sys.executable, "-c", NO_NUMPY, script, *args] if no_numpy else [sys.executable, script, *args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
