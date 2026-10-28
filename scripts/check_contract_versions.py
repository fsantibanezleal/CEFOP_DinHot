#!/usr/bin/env python3
"""Contract versions are a gate, not a habit (ADR-0080, rule 11 section 12): a schema cannot change without its
catalog version moving, a breaking change moves it by a major step, and every version has a history entry.

``docs/contracts/versions.lock.json`` records, for every catalog row with a schema file,
``{"version", "schema", "sha256"}``, the digest taken over the schema with line endings normalised to LF (a Windows
checkout hashes as a Linux one). The offline check (no ``--base``) fails when

- the lock is absent (run ``--update``) or lacks a catalog row that has a schema file, or lists a row the catalog no
  longer has (a removed contract is a deliberate major step: ``--update``);
- a schema's digest differs from the lock while the catalog version equals the lock's (a change without a bump);
- the catalog version differs from the lock's (a bump not recorded: ``--update``), or is lower than it (a version
  never goes down);
- a catalog row has no entry for its current version in ``## History`` of the catalog
  (``| contract | version | date | change | kind |``, kind one of initial, major, minor, patch), or the table is empty;
- the History of a contract does not read as semver: its first row is not ``initial``, or a later row's kind is not the
  step from the contract's previous row (``1.0.0`` to ``1.1.0`` is minor, to ``2.0.0`` major, to ``1.0.1`` patch).

The lock is only as honest as the commit that edits it: a schema change with the lock digest edited by hand passes the
offline check. ``--base REF`` closes that (CI passes the push's ``before`` SHA, or ``origin/develop``, with
``fetch-depth: 0``). Against the schemas and the catalog at REF it fails when

- a contract's schema differs from REF's (LF-normalised) and its version is not above REF's (a change without a bump,
  whatever the lock says), or its version is below REF's;
- the change is **breaking by the mechanical floor** and the version did not take a major step. The floor is a minimal
  JSON Schema diff: a removed property or definition, a property newly required, a removed enum value or a changed
  const, a narrowed type, an added or tightened bound (``maxLength``, ``minimum``, ``maxItems`` ...), ``pattern``,
  ``format``, ``multipleOf`` or ``uniqueItems``, ``additionalProperties`` turned false or constrained, an added
  constraint on ``items``, ``not`` or ``$ref``, a removed ``anyOf``/``oneOf`` alternative, an added ``allOf`` member, and
  for an OpenAPI file a removed path, operation, response or component. It is a floor, not the judgement: a reviewer
  still decides the semantic breaks it cannot see (a changed meaning, a unit, a default);
- a contract that had a schema at REF has none now (its schema cell is ``-`` or its row is gone) and its History has no
  row of kind ``major``, with a version above REF's, that records the removal.

A contract with no row at REF is a first release (any version, an ``initial`` History row); a REF with no catalog makes
every contract a first release. A REF that cannot be resolved (a shallow clone) is a finding that names
``fetch-depth: 0``; it never passes silently.

``--update`` rewrites the lock from the catalog and the schemas after a deliberate bump and prints what changed; it
refuses (exit 1) when a version went down or a schema changed under the same version. A catalog row without a
schema file is skipped by the lock. Standard library only (git for ``--base``).

Usage: ``python scripts/check_contract_versions.py [--repo-root DIR] [--base REF] [--update]``. Exit 0 sound, 1 on any finding.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_contracts import parse_catalog  # noqa: E402  (vendored; the catalog table is parsed the one way)

KINDS = {"initial", "major", "minor", "patch"}
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
HISTORY_HEAD = ["contract", "version", "date", "change", "kind"]
NONE = {"", "-", "n/a", "na", "none", "no"}


def semver(text: str) -> tuple[int, int, int] | None:
    m = SEMVER.match(text.strip())
    return (int(m[1]), int(m[2]), int(m[3])) if m else None


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def history_rows(text: str) -> list[list[str]] | None:
    """Rows of the History table under ``## History``; None when the section or its table is absent."""
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if re.match(r"^##\s+History\s*$", ln)), None)
    if start is None:
        return None
    rows: list[list[str]] | None = None
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        if not line.strip().startswith("|"):
            if rows is not None:
                break
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if rows is None:
            if [c.lower() for c in cells] == HISTORY_HEAD:
                rows = []
        elif not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            rows.append(cells)
    return rows


def catalog_rows(root: Path) -> tuple[list[dict[str, str]], str]:
    path = root / "docs" / "contracts" / "catalog.md"
    text = path.read_text(encoding="utf-8")
    parsed = parse_catalog(text)
    if parsed is None:
        raise SystemExit(f"{path.relative_to(root).as_posix()}: no contract catalog table found")
    return parsed[1], text


def build_lock(root: Path, rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    lock: dict[str, dict[str, str]] = {}
    for row in rows:
        schema = row.get("schema file", "").strip()
        if schema.lower() in NONE:
            continue
        path = root / schema
        lock[row["id"]] = {"version": row["version"].strip(), "schema": schema,
                           "sha256": digest(path) if path.is_file() else ""}
    return lock


def findings_for(root: Path, rows: list[dict[str, str]], text: str, lock: dict | None, base: str | None = None) -> list[str]:
    out: list[str] = []
    fresh = build_lock(root, rows)
    for cid, entry in sorted(fresh.items()):
        if not entry["sha256"]:
            out.append(f"{cid}: the schema file {entry['schema']} does not exist")
        if semver(entry["version"]) is None:
            out.append(f"{cid}: version {entry['version']!r} is not x.y.z")
    if lock is None:
        out.append("docs/contracts/versions.lock.json is missing; run: python scripts/check_contract_versions.py --update")
    else:
        for cid, entry in sorted(fresh.items()):
            old = lock.get(cid)
            if old is None:
                out.append(f"{cid}: a catalog row with a schema file, not in the lock; run --update")
                continue
            new_v, old_v = semver(entry["version"]), semver(old.get("version", ""))
            if new_v and old_v and new_v < old_v:
                out.append(f"{cid}: the version goes down, {old['version']} in the lock to {entry['version']} in the catalog")
            elif entry["version"] != old.get("version"):
                out.append(f"{cid}: the catalog says {entry['version']}, the lock {old.get('version')}; run --update after the bump")
            elif entry["sha256"] and entry["sha256"] != old.get("sha256"):
                out.append(f"{cid}: the schema {entry['schema']} changed without a version bump (still {entry['version']}); "
                           "bump the catalog version and add its History row, then --update")
            elif entry["schema"] != old.get("schema"):
                out.append(f"{cid}: the schema path is {entry['schema']}, the lock says {old.get('schema')}; run --update")
        for cid in sorted(set(lock) - set(fresh)):
            out.append(f"{cid}: in the lock but not a catalog row with a schema file; run --update (a removed contract is a major step)")
    hist = history_rows(text)
    if not hist:
        out.append("docs/contracts/catalog.md has no History table with rows (## History: contract | version | date | change | kind)")
    else:
        have: set[tuple[str, str]] = set()
        for cells in hist:
            if len(cells) != 5 or any(not c for c in cells):
                out.append(f"History row {cells[0] if cells else '(blank)'}: an empty cell")
                continue
            if cells[4].lower() not in KINDS:
                out.append(f"History {cells[0]} {cells[1]}: kind {cells[4]!r} is not one of {', '.join(sorted(KINDS))}")
            have.add((cells[0], cells[1]))
        for row in rows:
            if (row["id"], row["version"].strip()) not in have:
                out.append(f"{row['id']}: no History entry for its current version {row['version'].strip()}")
        out += history_findings(hist)
    if base:
        out += base_findings(root, base, rows, text)
    return out


def step(old: tuple[int, int, int], new: tuple[int, int, int]) -> str:
    """The semver step from ``old`` to a higher ``new``: major, minor or patch."""
    return "major" if new[0] > old[0] else "minor" if new[1] > old[1] else "patch"


def history_findings(hist: list[list[str]]) -> list[str]:
    """Per contract, sorted by version: the first row is ``initial`` and every later kind is the step from the row before."""
    by_contract: dict[str, list[tuple[tuple[int, int, int], str]]] = {}
    out: list[str] = []
    for cells in hist:
        if len(cells) != 5 or any(not c for c in cells):
            continue  # reported by findings_for
        v = semver(cells[1])
        if v is None:
            out.append(f"History {cells[0]} {cells[1]}: the version is not x.y.z")
            continue
        by_contract.setdefault(cells[0], []).append((v, cells[4].lower()))
    for cid, rows in sorted(by_contract.items()):
        rows.sort()
        if len({v for v, _ in rows}) != len(rows):
            out.append(f"History {cid}: a version is listed more than once")
        if rows[0][1] != "initial":
            out.append(f"History {cid}: the first row (version {'.'.join(map(str, rows[0][0]))}) must be kind initial, got {rows[0][1]!r}")
        for (before, _), (after, kind) in zip(rows, rows[1:]):
            if after > before and kind != step(before, after):
                out.append(f"History {cid} {'.'.join(map(str, after))}: kind {kind!r} is not the semver step from "
                           f"{'.'.join(map(str, before))}, which is {step(before, after)}")
    return out


# ---------------------------------------------------------------- the mechanical floor of a breaking change

MISSING = object()
UPPER = ("maxLength", "maximum", "maxItems", "maxProperties", "exclusiveMaximum", "maxContains")
LOWER = ("minLength", "minimum", "minItems", "minProperties", "exclusiveMinimum", "minContains")
ADDED_OR_CHANGED = ("pattern", "format", "multipleOf")
MAPS = {"properties", "patternProperties", "$defs", "definitions", "dependentSchemas", "paths", "schemas", "responses",
        "content", "components", "requestBodies", "headers", "callbacks", "webhooks", "securitySchemes", "links", "parameters"}
METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
HANDLED = {"type", "enum", "const", "required", "additionalProperties", "items", "prefixItems", "anyOf", "oneOf", "allOf",
           "not", "$ref", "uniqueItems", *UPPER, *LOWER, *ADDED_OR_CHANGED}
IGNORE = {"example", "examples", "default", "description", "title", "$comment", "info", "servers", "externalDocs", "tags", "$schema", "$id"}


def _types(node: dict) -> set[str] | None:
    t = node.get("type", MISSING)
    if isinstance(t, str):
        return {t}
    if isinstance(t, list) and all(isinstance(x, str) for x in t):
        return set(t)
    return None


def _number(x: object) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def breaking(old: object, new: object, at: str = "#", *, is_map: bool = False) -> list[str]:
    """What, between two versions of one schema (or OpenAPI) document, a consumer of the old one can no longer rely on."""
    if isinstance(old, bool) or isinstance(new, bool):
        return [f"{at}: the schema now rejects everything"] if (old is not False and new is False) else []
    if not isinstance(old, dict) or not isinstance(new, dict):
        return []
    out: list[str] = []
    if is_map:
        for key, ov in old.items():
            nv = new.get(key, MISSING)
            if nv is MISSING:
                out.append(f"{at}/{key}: removed")
            elif isinstance(ov, dict):
                out += breaking(ov, nv, f"{at}/{key}")
        return out
    ot, nt = _types(old), _types(new)
    if nt is not None and (ot is None or any(t not in nt and not (t == "integer" and "number" in nt) for t in ot)):
        out.append(f"{at}: the type is narrowed ({sorted(ot) if ot else 'any'} to {sorted(nt)})")
    if isinstance(new.get("enum"), list):
        if not isinstance(old.get("enum"), list):
            out.append(f"{at}: an enum is added")
        else:
            out += [f"{at}: the enum value {v!r} is removed" for v in old["enum"] if v not in new["enum"]]
    if "const" in new and old.get("const", MISSING) != new["const"]:
        out.append(f"{at}: the const is added or changed")
    for key in UPPER:
        if _number(new.get(key)) and (not _number(old.get(key)) or new[key] < old[key]):
            out.append(f"{at}: {key} is added or tightened ({old.get(key)} to {new[key]})")
    for key in LOWER:
        if _number(new.get(key)) and (not _number(old.get(key)) or new[key] > old[key]):
            out.append(f"{at}: {key} is added or tightened ({old.get(key)} to {new[key]})")
    for key in ADDED_OR_CHANGED:
        if key in new and old.get(key, MISSING) != new[key]:
            out.append(f"{at}: {key} is added or changed")
    if new.get("uniqueItems") is True and old.get("uniqueItems") is not True:
        out.append(f"{at}: uniqueItems is added")
    if isinstance(new.get("required"), list):
        before = old.get("required") if isinstance(old.get("required"), list) else []
        out += [f"{at}: {name!r} is newly required" for name in new["required"] if name not in before]
    oap, nap = old.get("additionalProperties", True), new.get("additionalProperties", True)
    if nap is False and oap is not False:
        out.append(f"{at}: additionalProperties is turned false")
    elif isinstance(nap, dict):
        if isinstance(oap, dict):
            out += breaking(oap, nap, f"{at}/additionalProperties")
        elif oap is True:
            out.append(f"{at}: additionalProperties is constrained")
    for key in ("items", "not"):
        if isinstance(new.get(key), (dict, bool)) and key not in old:
            out.append(f"{at}: {key} is added")
        elif key == "items" and isinstance(old.get(key), dict) and isinstance(new.get(key), dict):
            out += breaking(old[key], new[key], f"{at}/items")
    if "$ref" in new and old.get("$ref", MISSING) != new["$ref"]:
        out.append(f"{at}: $ref is added or changed")
    for key in ("anyOf", "oneOf", "allOf", "prefixItems", "items"):
        ol, nl = old.get(key), new.get(key)
        if not isinstance(nl, list):
            continue
        if not isinstance(ol, list):
            out.append(f"{at}: {key} is added")
            continue
        if (key in ("anyOf", "oneOf") and len(nl) < len(ol)) or (key in ("allOf", "prefixItems", "items") and len(nl) > len(ol)):
            out.append(f"{at}: {key} {'loses an alternative' if key in ('anyOf', 'oneOf') else 'gains a member'}")
        for n, (a, b) in enumerate(zip(ol, nl)):
            out += breaking(a, b, f"{at}/{key}/{n}")
    for key, ov in old.items():
        if key in HANDLED or key in IGNORE or key.startswith("x-"):
            continue
        nv = new.get(key, MISSING)
        if key in METHODS and isinstance(ov, dict) and nv is MISSING:
            out.append(f"{at}/{key}: the operation is removed")
        elif key in MAPS and isinstance(ov, dict):
            out += [f"{at}/{key}: removed"] if nv is MISSING else breaking(ov, nv, f"{at}/{key}", is_map=True)
        elif isinstance(ov, dict) and isinstance(nv, dict):
            out += breaking(ov, nv, f"{at}/{key}")
    return out


# ---------------------------------------------------------------- the base ref

def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True)


def base_file(root: Path, ref: str, rel: str) -> bytes | None:
    done = _git(root, "show", f"{ref}:{rel}")
    return done.stdout if done.returncode == 0 else None


def base_findings(root: Path, ref: str, rows: list[dict[str, str]], text: str) -> list[str]:
    """The schemas and versions of the catalog against the same files at ``ref``."""
    try:
        resolved = _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    except OSError as e:
        return [f"--base {ref}: git cannot run ({e})"]
    if resolved.returncode != 0:
        return [f"--base {ref}: cannot be resolved here (not a git checkout, a shallow clone, or the ref was not fetched); "
                "the CI checkout needs `fetch-depth: 0` and the ref must exist (git fetch origin develop)"]
    raw = base_file(root, ref, "docs/contracts/catalog.md")
    if raw is None:
        return []  # no catalog at the base: every contract is a first release
    parsed = parse_catalog(raw.decode("utf-8", errors="replace"))
    if parsed is None:
        return []
    out: list[str] = []
    hist = history_rows(text) or []
    now = {r["id"]: r for r in rows}
    for old in parsed[1]:
        cid, schema = old["id"], old.get("schema file", "").strip()
        base_v = semver(old.get("version", ""))
        if schema.lower() in NONE or base_v is None:
            continue
        row = now.get(cid)
        cur_schema = row.get("schema file", "").strip() if row else ""
        if row is None or cur_schema.lower() in NONE:
            why = "its catalog row is gone" if row is None else "its schema cell is now `-`"
            recorded = any(c[0] == cid and len(c) == 5 and c[4].lower() == "major" and (semver(c[1]) or (0, 0, 0)) > base_v for c in hist)
            if not recorded:
                out.append(f"{cid}: had the schema {schema} at {ref} and it is removed ({why}); a removal is a major step: add a "
                           f"History row of kind major with a version above {old['version']} that records it")
            continue
        cur_v = semver(row["version"])
        if cur_v is None:
            continue  # reported as not x.y.z
        if cur_v < base_v:
            out.append(f"{cid}: the version goes down against the base {ref}, {old['version']} to {row['version']}")
            continue
        before = base_file(root, ref, schema)
        path = root / cur_schema
        if before is None or not path.is_file():
            continue
        if hashlib.sha256(before.replace(b"\r\n", b"\n")).hexdigest() == digest(path):
            continue
        if cur_v == base_v:
            out.append(f"{cid}: the schema {cur_schema} changed against the base {ref} without a version bump (still {row['version']}), "
                       "whatever the lock says; bump the catalog version and add its History row, then --update")
            continue
        try:
            found = breaking(json.loads(before.decode("utf-8")), json.loads(path.read_text(encoding="utf-8")))
        except ValueError as e:
            out.append(f"{cid}: the schema or its version at {ref} is not valid JSON ({e})")
            continue
        if found and step(base_v, cur_v) != "major":
            out.append(f"{cid}: breaking changes need a major bump, the version went {old['version']} to {row['version']} "
                       f"({step(base_v, cur_v)}): " + "; ".join(found[:3]) + (f"; and {len(found) - 3} more" if len(found) > 3 else ""))
    return out


def update(root: Path, rows: list[dict[str, str]], lock_path: Path, lock: dict | None) -> int:
    fresh = build_lock(root, rows)
    refuse: list[str] = []
    changes: list[str] = []
    for cid, entry in sorted(fresh.items()):
        old = (lock or {}).get(cid)
        if old is None:
            changes.append(f"{cid}: added at {entry['version']}")
            continue
        new_v, old_v = semver(entry["version"]), semver(old.get("version", ""))
        if new_v and old_v and new_v < old_v:
            refuse.append(f"{cid}: the version goes down, {old['version']} to {entry['version']}")
        elif entry["version"] == old.get("version") and entry["sha256"] != old.get("sha256"):
            refuse.append(f"{cid}: the schema changed under the same version {entry['version']}; bump the catalog version first")
        elif entry["version"] != old.get("version"):
            changes.append(f"{cid}: version {old.get('version')} to {entry['version']}")
    for cid in sorted(set(lock or {}) - set(fresh)):
        changes.append(f"{cid}: removed from the lock")
    if refuse:
        print("UPDATE REFUSED:")
        for r in refuse:
            print(f"  - {r}")
        return 1
    lock_path.write_text(json.dumps(fresh, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"versions.lock.json written ({len(fresh)} contracts)" + ("".join(f"\n  {c}" for c in changes) if changes else "; nothing changed"))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--base", metavar="REF", help="compare the schemas and versions with the same files at this git ref "
                    "(CI: the push's before SHA or origin/develop, with fetch-depth: 0)")
    ap.add_argument("--update", action="store_true", help="rewrite the lock after a deliberate bump")
    args = ap.parse_args(argv)
    root = args.repo_root.resolve()
    rows, text = catalog_rows(root)
    lock_path = root / "docs" / "contracts" / "versions.lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8")) if lock_path.is_file() else None
    if args.update:
        code = update(root, rows, lock_path, lock)
        if code:
            return code
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    findings = findings_for(root, rows, text, lock, args.base)
    if findings:
        print("CONTRACT VERSIONS CHECK FAILED:")
        for f in findings:
            print(f"  - {f}")
        return 1
    against = f", schemas and versions checked against {args.base}" if args.base else ", offline (no --base: the lock alone is trusted)"
    print(f"check_contract_versions: OK, {len(rows)} contracts, {len(lock or {})} locked, every version has its History entry{against}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
