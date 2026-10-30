#!/usr/bin/env python3
"""Every committed document against its schema file (docs/contracts/schemas/), with jsonschema alone.

The guard names no document: it reads the contract catalog (``docs/contracts/catalog.md``), whose ``documents`` column says,
per row, which committed files that row's schema governs. A product takes this file verbatim; its catalog is what differs.

A ``documents`` cell is ``-`` (no committed document) or globs relative to the repository root, separated by ``, ``
(``pathlib`` glob semantics: ``*`` within one path segment, ``**`` for any depth, so use it only where a depth varies). A
glob starting with ``!`` excludes what the row's other globs match. On an OpenAPI row (a schema file that is the OpenAPI
document) each glob is written ``path#ComponentName`` and the files validate against that component. Every glob under
``data/`` or ``models/`` is applied twice: at the repository root and at the provider tree ``docs/contracts/fixtures/``.
A row's ``example`` cell is validated too when it is a file under ``docs/contracts/examples/``. A file counts once for its
row, however many of its globs and its example name it.

A committed document that is not JSON (a file whose suffix is not ``.json``: a model file such as ``.onnx`` or ``.pt``, a CSV
table) has no schema to validate against; its contract is its row's ``model io`` or table description, tested by the row's own
contract test. The guard leaves it to that test and requires the row to name one: the ``producer test`` or the ``consumer test``
column must be filled (not empty and not ``-``). It lists these files after the count and does not parse them.

Errors: a file matched by two rows (one committed document has one contract); a file under ``data/derived`` or ``models``
(root or provider tree) that is JSON and that no row covers (it would pass unvalidated); a ``.json`` file that is not JSON or
departs from its schema (the path and the schema are named); a non-JSON document whose row names no test; an absent document of a row whose ``missing-data behavior``
begins ``missing:`` and whose ``documents`` cell is one fixed path (for the template, the index: no inventory, nothing to
validate). A glob that matches nothing is not reported: scripts/check_artifacts.py and scripts/check_readiness.py judge
absence. The generated TypeScript types do not encode a ``pattern`` or a ``minItems``; this check does (review finding F5).
It uses the registry of ``tests/contracts/contract_schemas.py`` (one place resolves a schema reference), so it needs only
``jsonschema`` (4.26.0) and its ``referencing``, no pipeline and no numpy.

Exit 0 and ``documents: N valid``; exit 1 listing each error. Usage: python scripts/check_documents.py [repo_root]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tests" / "contracts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import contract_schemas as cs  # noqa: E402  (the schema registry, shared with the contract tests)
from check_contracts import RELEASE_COLUMNS, parse_catalog, parse_document_glob, split_documents  # noqa: E402

CATALOG_REL = "docs/contracts/catalog.md"
FIXTURES_REL = "docs/contracts/fixtures"
EXAMPLES_REL = "docs/contracts/examples/"
ROOTED = ("data/", "models/")  # globs under these also apply in the provider tree
HOLE_DIRS = ("data/derived", "models")  # a JSON file here must be covered by a row


class Report:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.valid = 0
        self.errors: list[str] = []
        self.unparsed: list[str] = []  # non-JSON documents left to their row's contract test

    def label(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return path.as_posix()

    def check(self, path: Path, schema: str, component: bool = False) -> None:
        """Validate the document at ``path`` against ``schema`` (a schema file name, or an OpenAPI component)."""
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            self.errors.append(f"{self.label(path)}: not readable as JSON ({exc})")
            return
        try:
            found = cs.component_errors(schema, doc) if component else cs.errors(schema, doc)
        except OSError as exc:
            self.errors.append(f"{self.label(path)}: schema [{schema}] cannot be loaded ({exc})")
            return
        if found:
            self.errors += [f"{self.label(path)}: [{schema}] {e}" for e in found]
        else:
            self.valid += 1


def names_a_test(row: dict[str, str]) -> bool:
    """Whether the row's producer test or consumer test cell is filled (not empty, not ``-``)."""
    return any(row.get(column, "").strip().strip("`").strip() not in ("", "-") for column in ("producer test", "consumer test"))


def schema_name(schema_file: str) -> str:
    """``docs/contracts/schemas/<name>.schema.json`` to ``<name>`` (the key of the registry)."""
    name = Path(schema_file.strip().strip("`")).name
    return name[: -len(".schema.json")] if name.endswith(".schema.json") else name


def matches(root: Path, glob: str) -> set[Path]:
    """The files under ``root`` that ``glob`` names (``pathlib`` glob; ``**`` for any depth)."""
    return {p for p in root.glob(glob) if p.is_file()}


def outside_repository(glob: str) -> bool:
    """Whether a glob leaves the repository: absolute, a drive path, a backslash or a ``..`` segment."""
    g = glob.replace("\\", "/")
    return g.startswith("/") or bool(re.match(r"^[A-Za-z]:", g)) or "\\" in glob or ".." in g.split("/")


def row_files(root: Path, entries: list[str]) -> dict[Path, str]:
    """The files a row's globs govern, each with the OpenAPI component (``""`` for none), in the repository and in the
    provider tree; exclusions removed."""
    include: list[tuple[str, str]] = []
    exclude: list[str] = []
    for entry in entries:
        out, glob, component = parse_document_glob(entry)
        for g in [glob] + ([f"{FIXTURES_REL}/{glob}"] if glob.startswith(ROOTED) else []):
            (exclude.append(g) if out else include.append((g, component)))
    drop = {p for g in exclude for p in matches(root, g)}
    found: dict[Path, str] = {}
    for glob, component in include:
        for path in matches(root, glob):
            if path not in drop:
                found[path] = component
    return found


def hole_files(root: Path) -> list[Path]:
    """The JSON files of the bake, the released models and their provider-tree twins."""
    out: list[Path] = []
    for base in HOLE_DIRS:
        for top in (root / base, root / FIXTURES_REL / base):
            out += sorted(top.glob("**/*.json")) if top.is_dir() else []
    return out


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE
    rep = Report(root)
    catalog = root / CATALOG_REL
    try:
        parsed = parse_catalog(catalog.read_text(encoding="utf-8"))
    except OSError as exc:
        parsed = None
        rep.errors.append(f"{CATALOG_REL}: cannot be read ({exc})")
    if parsed is not None:
        header, rows = parsed
        late = [f"{c} (added in template {rel})" for c, rel in RELEASE_COLUMNS.items() if c not in header]
        if late or "schema file" not in header or "id" not in header:
            rep.errors.append(f"{CATALOG_REL}: lacks the column {', '.join(late) or 'id or schema file'}: add it, one cell per row")
        else:
            validate_rows(rep, root, rows)
    elif not rep.errors:
        rep.errors.append(f"{CATALOG_REL}: no contract catalog table found")
    if rep.errors:
        print("documents: INVALID")
        for e in rep.errors:
            print(f"  - {e}")
        return 1
    print(f"documents: {rep.valid} valid")
    if rep.unparsed:
        print(f"documents: {len(rep.unparsed)} not JSON, left to the contract test of their row: {', '.join(rep.unparsed)}")
    return 0


def validate_rows(rep: Report, root: Path, rows: list[dict[str, str]]) -> None:
    claims: dict[Path, list[tuple[str, str, str]]] = {}  # file -> [(row id, schema name, component)]
    by_id = {row.get("id", ""): row for row in rows}
    for row in rows:
        rid, schema_file = row.get("id", ""), row.get("schema file", "")
        entries = split_documents(row.get("documents", ""))
        bad = [e for e in entries if outside_repository(parse_document_glob(e)[1])]
        if bad:
            rep.errors.append(f"{CATALOG_REL}: row {rid} names {', '.join(bad)}, outside the repository (a glob relative to the root, no '..')")
            continue
        files = row_files(root, entries)
        example = row.get("example", "").strip().strip("`")
        if example.startswith(EXAMPLES_REL) and (root / example).is_file():
            # an OpenAPI row validates its example against the component its documents cell names for the same file
            files.setdefault(root / example, "")
        openapi = schema_file.strip().strip("`").endswith("openapi.json")
        for path, component in files.items():
            if openapi and not component:
                continue  # an example of an OpenAPI row with no component named is not validated here
            claims.setdefault(path, []).append((rid, component or schema_name(schema_file), "component" if component else ""))
        fixed = [e for e in entries if not e.startswith("!") and not any(c in e for c in "*?[")]
        if len(entries) == 1 and len(fixed) == 1 and row.get("missing-data behavior", "").strip().lower().startswith("missing:"):
            glob = parse_document_glob(fixed[0])[1]
            if not (root / glob).is_file():
                rep.errors.append(f"{glob}: absent (the catalog row {rid} says missing: nothing to validate without it)")
    for path in sorted(claims):
        by_row = {}
        for rid, schema, component in claims[path]:
            by_row.setdefault(rid, (schema, component))
        if len(by_row) > 1:
            rep.errors.append(f"{rep.label(path)}: claimed by more than one row ({', '.join(sorted(by_row))}): one committed "
                              "document has one contract")
            continue
        (rid, (schema, component)), = by_row.items()
        if path.suffix.lower() != ".json":
            if names_a_test(by_id[rid]):
                rep.unparsed.append(rep.label(path))
            else:
                rep.errors.append(f"{rep.label(path)}: a document that is not JSON is left to the contract test of its row, and the row {rid} "
                                  f"names none: fill its producer test or consumer test column in {CATALOG_REL}")
            continue
        rep.check(path, schema, component=bool(component))
    for path in hole_files(root):
        if path not in claims:
            rep.errors.append(f"{rep.label(path)}: covered by no row of {CATALOG_REL} (documents column): it is not validated")


if __name__ == "__main__":
    sys.exit(main())
