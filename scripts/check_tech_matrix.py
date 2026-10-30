#!/usr/bin/env python3
"""The technology matrix of the SDD is the pinned dependencies, exactly (ADR-0075, ADR-0080; rule 11 section 12).

The SDD section ``Technology and versions`` holds one table ``| component | package | version | use | alternative
considered |``. This guard reads every pin of the Python requirements (every ``requirements*.txt`` at the root,
``data-pipeline/requirements*.txt``, ``notebooks/requirements*.txt``, each ``-r`` include followed, and ``[project].dependencies`` of ``pyproject.toml``
when present) and of ``frontend/package.json`` (``dependencies``, ``devDependencies``, ``optionalDependencies``,
``peerDependencies`` and ``overrides``) and fails, naming each one, when

- a pinned package is absent from the table, or its version differs, or a table row names a package or a version that
  is not pinned;
- a Python requirement is not an exact pin: ``name==X.Y.Z`` with no wildcard and no second specifier, or a git pin
  ``name @ git+https://...@ref`` (compared by its ref). A range, a bare name, an editable (``-e``) and a bare URL line
  are findings;
- the same package is pinned twice with different versions, in one file or across files (the same pin twice is fine);
- a ``package.json`` spec is not what ``frontend/package-lock.json`` records: **ranges stay allowed** there (the repository
  uses them with a lock file), and then the lock is the pin. For each package the spec must equal the lock's root spec
  (``packages[""]``, which is what ``npm ci`` checks), the locked version (``node_modules/<name>``) must satisfy it, and
  the SDD table holds the locked version, never the range. An ``overrides`` entry has no root record in the lock, so it
  must be an exact version.

Python pins stay exact (``==``); only ``package.json`` may carry ranges, and only with a lock that agrees. The range
check implements npm's comparators (exact, ``^``, ``~``, ``>``, ``>=``, ``<``, ``<=``, ``=``, ``x`` and partial versions,
hyphen ranges, ``||``) and rejects a spec it cannot read (a tag, a URL) rather than assuming it holds.

An npm alias, ``"zz-typescript5": "npm:typescript@5.9.3"`` (0.09.000: a product on TypeScript 7 keeps the TypeScript 5 compiler
API that ``openapi-typescript`` needs under another name), is read as ``npm:<package>@<version>``. The version must be exact like
any other pin (an alias with a range is a finding), the lock must record the same spec at its root and the same version at
``node_modules/<alias>`` (under the alias's own name), and the SDD technology table must carry the alias's own name with that
version, in the ``package`` column, like any other package.

Pins are compared by normalised name (lower case, ``_`` and ``.`` as ``-``, extras dropped). Standard library only
(CI installs nothing; ``tomllib`` is in Python 3.11 and later).

Usage: ``python scripts/check_tech_matrix.py [repo_root]``. Exit 0 consistent, 1 on any mismatch.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
SDD = ROOT / "docs" / "design" / "SDD.md"
HEAD = ["component", "package", "version", "use", "alternative considered"]
EXACT = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$")
NAME_RE = r"[A-Za-z0-9][A-Za-z0-9._-]*"
PIN = re.compile(rf"^(?P<name>{NAME_RE})(?:\[[^\]]*\])?\s*==\s*(?P<version>[^\s;#,]+)\s*(?:;[^#]*)?$")
GIT = re.compile(rf"^(?P<name>{NAME_RE})(?:\[[^\]]*\])?\s*@\s*git\+\S+?@(?P<ref>[^\s#;]+)")
NAME = re.compile(rf"^(?P<name>{NAME_RE})")
PY_VERSION = re.compile(r"^[0-9][0-9A-Za-z.+!_-]*$")
ALIAS = re.compile(r"^npm:(?P<package>(?:@[^/@\s]+/)?[^/@\s]+)@(?P<version>\S+)$")
NODE_SECTIONS = ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.strip().lower())


# ------------------------------------------------------------------ Python

def requirement_line(line: str, rel: str, pins: dict[str, tuple[str, str]], findings: list[str]) -> None:
    g = GIT.match(line)
    m = PIN.match(line)
    n = NAME.match(line)
    if line.startswith("-"):
        findings.append(f"{rel}: {line!r} is an editable or an option line that pins nothing (use name==version or a git ref)")
        return
    if g:
        add_pin(pins, norm(g["name"]), g["ref"], rel, findings)
    elif m and "*" not in m["version"] and PY_VERSION.match(m["version"]):
        add_pin(pins, norm(m["name"]), m["version"], rel, findings)
    else:
        label = n["name"] if n else line
        findings.append(f"{rel}: {label!r} is unpinned (use name==version with no wildcard, or a git ref): {line!r}")


def add_pin(pins: dict[str, tuple[str, str]], name: str, version: str, source: str, findings: list[str]) -> None:
    old = pins.get(name)
    if old is not None and old[0] != version:
        findings.append(f"{name}: pinned as {old[0]} in {old[1]} and as {version} in {source} (one package, one version)")
        return
    pins.setdefault(name, (version, source))


def python_files() -> list[Path]:
    found = (sorted(ROOT.glob("requirements*.txt")) + sorted((ROOT / "data-pipeline").glob("requirements*.txt"))
             + sorted((ROOT / "notebooks").glob("requirements*.txt")))  # the notebook environment (template 0.10.000)
    return [p.resolve() for p in found]


def python_pins(findings: list[str]) -> dict[str, tuple[str, str]]:
    """name -> (version, source) for every pin of the requirements files, ``-r`` includes followed."""
    pins: dict[str, tuple[str, str]] = {}
    seen: set[Path] = set()

    def read(path: Path) -> None:
        if path in seen or not path.is_file():
            return
        seen.add(path)
        rel = path.relative_to(ROOT).as_posix()
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.split(" #")[0].strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith(("-r ", "--requirement ")):
                read((path.parent / line.split(None, 1)[1].strip()).resolve())
                continue
            if line.startswith(("-c ", "--constraint ", "--index-url", "--extra-index-url", "-i ", "--find-links", "-f ",
                                "--no-binary", "--only-binary", "--prefer-binary", "--pre")):
                continue  # options that pin nothing and are not an unpinned requirement
            requirement_line(line, rel, pins, findings)

    for path in python_files():
        read(path)
    pyproject = ROOT / "pyproject.toml"
    if pyproject.is_file():
        import tomllib
        project = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {})
        for line in project.get("dependencies", []):
            requirement_line(line.strip(), "pyproject.toml", pins, findings)
    return pins


# ------------------------------------------------------------------ npm semver

VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$")
PARTIAL = re.compile(r"^v?(\d+|[xX*])(?:\.(\d+|[xX*]))?(?:\.(\d+|[xX*]))?(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$")
Semver = tuple[int, int, int, tuple]


def parse_version(text: str) -> Semver | None:
    m = VERSION.match(text.strip())
    if not m:
        return None
    pre = tuple((0, int(p)) if p.isdigit() else (1, p) for p in m[4].split(".")) if m[4] else ()
    return int(m[1]), int(m[2]), int(m[3]), pre


def compare(a: Semver, b: Semver) -> int:
    if a[:3] != b[:3]:
        return -1 if a[:3] < b[:3] else 1
    if a[3] == b[3]:
        return 0
    if not a[3]:
        return 1  # a release is above its own prereleases
    if not b[3]:
        return -1
    return -1 if a[3] < b[3] else 1


def partial(text: str) -> tuple[int | None, int | None, int | None, tuple] | None:
    """A (possibly partial) version as (major, minor, patch, prerelease), None for an x or a missing part."""
    m = PARTIAL.match(text.strip())
    if not m:
        return None
    parts = [None if p is None or p in "xX*" else int(p) for p in m.groups()[:3]]
    pre = tuple((0, int(p)) if p.isdigit() else (1, p) for p in m[4].split(".")) if m[4] else ()
    return parts[0], parts[1], parts[2], pre


def lower_bound(p: tuple) -> Semver:
    return p[0] or 0, p[1] or 0, p[2] or 0, p[3]


def upper_exclusive(p: tuple) -> Semver | None:
    """The first version above everything the partial ``p`` stands for (None: no upper bound, a bare ``*``)."""
    major, minor, patch, _ = p
    if major is None:
        return None
    if minor is None:
        return major + 1, 0, 0, (( 0, 0),)
    if patch is None:
        return major, minor + 1, 0, ((0, 0),)
    return None


def comparators(token: str) -> list[tuple[str, Semver]] | None:
    """One range token (``^1.2.3``, ``~1.2``, ``>=1``, ``1.x`` ...) as a list of (operator, version) all of which must hold."""
    m = re.match(r"^(\^|~>?|>=|<=|>|<|=)?\s*(.+)$", token.strip())
    if not m:
        return None
    op, rest = m[1] or "", m[2]
    p = partial(rest)
    if p is None:
        return None
    low = lower_bound(p)
    major, minor, patch, _ = p
    floor = ((0, 0),)  # the smallest prerelease: ``<1.0.0`` must exclude 1.0.0-alpha only through the ``-0`` rule
    if op in ("", "="):
        if major is None:
            return []
        up = upper_exclusive(p)
        return [(">=", low)] + ([("<", up)] if up else [("=", low)])
    if op == "^":
        if major is None:
            return []
        if major > 0 or minor is None:
            up = (major + 1, 0, 0, floor)
        elif minor > 0 or patch is None:
            up = (0, minor + 1, 0, floor)
        else:
            up = (0, 0, patch + 1, floor)
        return [(">=", low), ("<", up)]
    if op in ("~", "~>"):
        if major is None:
            return []
        up = (major, minor + 1, 0, floor) if minor is not None else (major + 1, 0, 0, floor)
        return [(">=", low), ("<", up)]
    if major is None:
        return [] if op in (">=", "<=") else [("<", (0, 0, 0, ()))]
    if op == ">":
        up = upper_exclusive(p)
        return [(">=", up)] if up else [(">", low)]
    if op == "<=":
        up = upper_exclusive(p)
        return [("<", up)] if up else [("<=", low)]
    return [(op, low)]


def satisfies(version: str, spec: str) -> bool | None:
    """Whether ``version`` satisfies the npm range ``spec``; None when the spec is not a range this guard can read."""
    v = parse_version(version)
    if v is None:
        return None
    result = False
    for alternative in spec.split("||"):
        text = alternative.strip()
        hyphen = re.match(r"^(\S+)\s+-\s+(\S+)$", text)
        if hyphen:
            lo, hi = partial(hyphen[1]), partial(hyphen[2])
            if lo is None or hi is None:
                return None
            up = upper_exclusive(hi)
            tokens: list[tuple[str, Semver]] = [(">=", lower_bound(lo)), *([("<", up)] if up else [("<=", lower_bound(hi))])]
        else:
            tokens = []
            for token in re.findall(r"(?:\^|~>?|>=|<=|>|<|=)?\s*[^\s]+", re.sub(r"(\^|~>?|>=|<=|>|<|=)\s+", r"\1", text)):
                got = comparators(token)
                if got is None:
                    return None
                tokens += got
            if not text:
                tokens = []
        ok = all(_holds(v, op, bound) for op, bound in tokens)
        if ok and v[3] and not any(b[:3] == v[:3] and b[3] for _, b in tokens):
            ok = False  # a prerelease satisfies only a comparator that names a prerelease of the same x.y.z
        result = result or ok
    return result


def _holds(v: Semver, op: str, bound: Semver) -> bool:
    c = compare(v, bound)
    return {">=": c >= 0, ">": c > 0, "<=": c <= 0, "<": c < 0, "=": c == 0}[op]


# ------------------------------------------------------------------ package.json and its lock

def flatten_overrides(node: dict, parent: str | None = None) -> list[tuple[str, str]]:
    """The (package, spec) leaves of an ``overrides`` object: keys are ``pkg`` or ``pkg@selector``, ``"."`` stands for the parent."""
    out: list[tuple[str, str]] = []
    for key, value in node.items():
        name = parent if key == "." and parent else re.sub(r"(?<=.)@[^@/]*$", "", key)
        if isinstance(value, str):
            if not value.startswith("$"):  # "$name" refers to the spec of a dependency, which is checked as one
                out.append((name, value))
        elif isinstance(value, dict):
            out += flatten_overrides(value, name)
    return out


def node_pins(findings: list[str]) -> dict[str, tuple[str, str]]:
    pkg = ROOT / "frontend" / "package.json"
    if not pkg.is_file():
        return {}
    doc = json.loads(pkg.read_text(encoding="utf-8"))
    lock_path = ROOT / "frontend" / "package-lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8")) if lock_path.is_file() else None
    packages: dict = (lock or {}).get("packages", {})
    root_spec: dict = packages.get("", {})
    pins: dict[str, tuple[str, str]] = {}
    here = "frontend/package.json"
    if lock is None:
        findings.append(f"{here}: frontend/package-lock.json is missing, so no spec is pinned (run npm install and commit the lock)")
    for section in NODE_SECTIONS:
        for name, spec in sorted(doc.get(section, {}).items()):
            if lock is None:
                continue
            recorded = root_spec.get(section, {}).get(name)
            if recorded != spec:
                findings.append(f"{name} is unpinned ({spec!r} in {here} {section}): frontend/package-lock.json records "
                                f"{recorded!r} for it at its root, so npm ci and this table disagree")
                continue
            locked = packages.get(f"node_modules/{name}", {}).get("version")
            if not locked:
                findings.append(f"{name} is unpinned ({spec!r}): frontend/package-lock.json has no node_modules/{name} entry")
                continue
            alias = ALIAS.match(spec)
            if alias:
                target = packages.get(f"node_modules/{name}", {}).get("name")
                if not EXACT.match(alias["version"]):
                    findings.append(f"{name}: the alias {spec!r} in {here} must pin an exact version (npm:<package>@X.Y.Z), not a range")
                    continue
                if target not in (None, alias["package"]):
                    findings.append(f"{name}: the alias {spec!r} in {here} names {alias['package']}, the lock installs {target}")
                    continue
                ok = locked == alias["version"]
            else:
                ok = locked == spec if EXACT.match(spec) else satisfies(locked, spec)
            if ok is None:
                findings.append(f"{name}: the spec {spec!r} in {here} is not a version range this guard can check")
            elif not ok:
                findings.append(f"{name}: the locked version {locked} does not satisfy {spec!r} in {here}")
            else:
                add_pin(pins, norm(name), locked, "frontend/package-lock.json", findings)
    for name, spec in flatten_overrides(doc.get("overrides", {})):
        if not EXACT.match(spec):
            findings.append(f"{name}: the override {spec!r} in {here} must be an exact version (the lock has no root record of it)")
        else:
            add_pin(pins, norm(name), spec, f"{here} overrides", findings)
    return pins


# ------------------------------------------------------------------ the SDD table

def table_versions(findings: list[str]) -> dict[str, str] | None:
    if not SDD.is_file():
        findings.append(f"{SDD.relative_to(ROOT).as_posix()} is missing")
        return None
    lines = SDD.read_text(encoding="utf-8").splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.startswith("## ") and "technology and versions" in ln.lower()), None)
    if start is None:
        findings.append("SDD.md has no section 'Technology and versions'")
        return None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    table: dict[str, str] | None = None
    for line in lines[start + 1:end]:
        if not line.strip().startswith("|"):
            if table is not None:
                break
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if table is None:
            if [c.lower() for c in cells] == HEAD:
                table = {}
        elif not all(re.fullmatch(r":?-{3,}:?", c) for c in cells) and len(cells) >= 3:
            package = norm(cells[1].strip("`"))
            if package in table:
                findings.append(f"SDD.md technology table lists {package} more than once")
            table[package] = cells[2].strip("`").strip()
    if table is None:
        findings.append(f"SDD.md 'Technology and versions' has no table with the columns {' | '.join(HEAD)}")
    return table


def main() -> int:
    findings: list[str] = []
    py, node = python_pins(findings), node_pins(findings)
    pins = dict(py)
    for name, (version, source) in node.items():
        add_pin(pins, name, version, source, findings)
    table = table_versions(findings)
    if table is not None:
        for name, (version, source) in sorted(pins.items()):
            if name not in table:
                findings.append(f"{name} {version} is pinned in {source} but absent from the SDD technology table")
            elif table[name] != version:
                findings.append(f"{name}: {source} pins {version}, the SDD technology table says {table[name]}")
        for name, version in sorted(table.items()):
            if name not in pins:
                findings.append(f"{name} {version} is in the SDD technology table but pinned in no requirements file or package.json")
    if findings:
        print("TECH MATRIX CHECK FAILED:")
        for f in findings:
            print(f"  - {f}")
        return 1
    print(f"check_tech_matrix: OK, {len(pins)} pinned dependencies, all in the SDD technology table with the same version")
    return 0


if __name__ == "__main__":
    sys.exit(main())
