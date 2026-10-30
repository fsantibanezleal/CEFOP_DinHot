"""A small JSON Schema (draft 2020-12) validator on the standard library, for the one place that cannot import
``jsonschema``: contract 1 and the model-card check run inside ``core/readiness.py``, which CI executes with nothing
installed (``scripts/check_readiness.py``, ADR-0074). The schema files in ``docs/contracts/schemas/`` stay the single
source of every shape; this module only reads them. It implements the keywords those files use and raises on any other
keyword that would change the verdict, so a schema edit that outgrows it fails loudly instead of validating nothing.

``tests/contracts/`` holds the check that this validator and ``jsonschema`` agree on the committed documents and on
adversarial records.
"""
from __future__ import annotations

import math
import re
from typing import Any

# keywords with no effect on validity (annotations)
_ANNOTATIONS = {"$schema", "$id", "title", "description", "$defs", "examples", "default", "$comment"}
_KNOWN = _ANNOTATIONS | {
    "type", "enum", "const", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minLength", "pattern",
    "required", "properties", "additionalProperties", "propertyNames", "items", "prefixItems", "minItems", "maxItems",
    "uniqueItems", "oneOf", "anyOf", "allOf", "not", "if", "then", "else", "$ref",
}


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _is_integer(v: Any) -> bool:
    return (isinstance(v, int) and not isinstance(v, bool)) or (isinstance(v, float) and math.isfinite(v) and v.is_integer())


def _type_ok(name: str, v: Any) -> bool:
    if name == "number":
        return _is_number(v)
    if name == "integer":
        return _is_integer(v)
    if name == "string":
        return isinstance(v, str)
    if name == "boolean":
        return isinstance(v, bool)
    if name == "null":
        return v is None
    if name == "object":
        return isinstance(v, dict)
    if name == "array":
        return isinstance(v, list)
    raise ValueError(f"unsupported schema type {name!r}")


def _equal(a: Any, b: Any) -> bool:
    """JSON equality: booleans are not numbers, 1 equals 1.0."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_equal(a[k], b[k]) for k in a)
    return type(a) is type(b) and a == b


def _resolve(root: dict, ref: str) -> dict:
    if not ref.startswith("#"):
        raise ValueError(f"only local references are supported, got {ref!r}")
    node: Any = root
    for part in [p for p in ref[1:].split("/") if p]:
        node = node[part.replace("~1", "/").replace("~0", "~")]
    return node


def errors(schema: dict, instance: Any, root: dict | None = None, path: str = "$") -> list[str]:
    """Every way ``instance`` departs from ``schema``, as ``path: message``; empty when it conforms."""
    root = schema if root is None else root
    out: list[str] = []
    unknown = set(schema) - _KNOWN
    if unknown:
        raise ValueError(f"schema keyword(s) not supported by jsonschema_lite: {sorted(unknown)}")
    if "$ref" in schema:
        out += errors(_resolve(root, schema["$ref"]), instance, root, path)
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_ok(t, instance) for t in types):
            return out + [f"{path}: {_describe(instance)} is not of type {' or '.join(types)}"]
    if "const" in schema and not _equal(instance, schema["const"]):
        out.append(f"{path}: {_short(instance)} is not the constant {_short(schema['const'])}")
    if "enum" in schema and not any(_equal(instance, e) for e in schema["enum"]):
        out.append(f"{path}: {_short(instance)} is not one of {schema['enum']}")
    if _is_number(instance):
        out += _number(schema, instance, path)
    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            out.append(f"{path}: string is shorter than {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            out.append(f"{path}: {_short(instance)} does not match {schema['pattern']}")
    if isinstance(instance, dict):
        out += _object(schema, instance, root, path)
    if isinstance(instance, list):
        out += _array(schema, instance, root, path)
    out += _combinators(schema, instance, root, path)
    return out


def _number(schema: dict, v: float, path: str) -> list[str]:
    out = []
    if "minimum" in schema and v < schema["minimum"]:
        out.append(f"{path}: {v:g} is below the minimum {schema['minimum']:g}")
    if "maximum" in schema and v > schema["maximum"]:
        out.append(f"{path}: {v:g} is above the maximum {schema['maximum']:g}")
    if "exclusiveMinimum" in schema and v <= schema["exclusiveMinimum"]:
        out.append(f"{path}: {v:g} is not above {schema['exclusiveMinimum']:g}")
    if "exclusiveMaximum" in schema and v >= schema["exclusiveMaximum"]:
        out.append(f"{path}: {v:g} is not below {schema['exclusiveMaximum']:g}")
    return out


def _object(schema: dict, obj: dict, root: dict, path: str) -> list[str]:
    out = [f"{path}: '{k}' is a required property" for k in schema.get("required", []) if k not in obj]
    props = schema.get("properties", {})
    for k, sub in props.items():
        if k in obj:
            out += errors(sub, obj[k], root, f"{path}.{k}")
    extra = schema.get("additionalProperties", True)
    for k in obj:
        if k in props:
            continue
        if extra is False:
            out.append(f"{path}: '{k}' was unexpected")
        elif isinstance(extra, dict):
            out += errors(extra, obj[k], root, f"{path}.{k}")
    if "propertyNames" in schema:
        for k in obj:
            out += [e.replace(path, f"{path}.{k} (name)", 1) for e in errors(schema["propertyNames"], k, root, path)]
    return out


def _array(schema: dict, arr: list, root: dict, path: str) -> list[str]:
    out = []
    if len(arr) < schema.get("minItems", 0):
        out.append(f"{path}: fewer than {schema['minItems']} items")
    if "maxItems" in schema and len(arr) > schema["maxItems"]:
        out.append(f"{path}: more than {schema['maxItems']} items")
    if schema.get("uniqueItems") and any(_equal(arr[i], arr[j]) for i in range(len(arr)) for j in range(i)):
        out.append(f"{path}: items are not unique")
    prefix = schema.get("prefixItems", [])
    for i, sub in enumerate(prefix):
        if i < len(arr):
            out += errors(sub, arr[i], root, f"{path}[{i}]")
    if "items" in schema:
        for i in range(len(prefix), len(arr)):
            out += errors(schema["items"], arr[i], root, f"{path}[{i}]")
    return out


def _combinators(schema: dict, instance: Any, root: dict, path: str) -> list[str]:
    out = []
    for sub in schema.get("allOf", []):
        out += errors(sub, instance, root, path)
    if "anyOf" in schema and not any(not errors(s, instance, root, path) for s in schema["anyOf"]):
        out.append(f"{path}: matches none of the allowed shapes")
    if "oneOf" in schema:
        results = [errors(s, instance, root, path) for s in schema["oneOf"]]
        ok = [r for r in results if not r]
        if len(ok) != 1:
            if not ok:
                # report the alternative that came closest (fewest errors), the others are noise
                best = min(results, key=len)
                out += best if best else [f"{path}: matches none of the allowed shapes"]
            else:
                out.append(f"{path}: matches more than one of the allowed shapes")
    if "not" in schema and not errors(schema["not"], instance, root, path):
        out.append(f"{path}: matches a shape that is not allowed")
    if "if" in schema:
        branch = "then" if not errors(schema["if"], instance, root, path) else "else"
        if branch in schema:
            out += errors(schema[branch], instance, root, path)
    return out


def _short(v: Any) -> str:
    s = repr(v)
    return s if len(s) <= 60 else s[:57] + "..."


def _describe(v: Any) -> str:
    if isinstance(v, float) and not math.isfinite(v):
        return "a non-finite number"
    return _short(v)
