#!/usr/bin/env python3
"""The manuscripts gate (template 0.13.000; CAOS_MANAGE ``conventions/method-tiers-and-manuscripts.md`` section 2): every CAOS
product has a detailed technical report on Zenodo under its own concept DOI, and each interesting beyond-the-state-of-the-art
method has a manuscript of its own. ``product.json`` declares them in ``manuscripts``, a list of

    {"kind": "technical-report" | "manuscript", "concept_doi": "10.5281/zenodo.<N>", "title": "...", "version": "...",
     "covers": ["BS-1", ...]}

``covers`` names the claims (``BS-<n>``) of the SDD's section ``## Beyond the state of the art`` the entry reports (a technical
report may cover none; a manuscript covers at least one). A product (a tree without ``.template-source``) fails without at least
one ``technical-report``; the template may declare none, and validates what it declares. Static and offline by default:

- the report's ``version`` is ``X.XX.XXX`` (it follows the releases) and is never ahead of ``VERSION``;
- ``--release`` also requires every technical report's version to equal ``VERSION``: run it for a release that changes a method, a
  data source or a result (the rule publishes the new version of the report before or with that release);
- ``--zenodo`` also reads each concept record on zenodo.org (opt-in, needs the network, never CI): the record exists, carries the
  declared concept DOI and its latest version is the declared one.

Standard library only; exit 1 on any finding. Usage: ``python scripts/check_manuscripts.py [repo_root] [--release] [--zenodo]``.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

RULE = "CAOS_MANAGE conventions/method-tiers-and-manuscripts.md"
SENTINEL = ".template-source"
KINDS = ("technical-report", "manuscript")
FIELDS = ("kind", "concept_doi", "title", "version", "covers")
CONCEPT_DOI = re.compile(r"^10\.5281/zenodo\.([1-9]\d*)$")
RELEASE = re.compile(r"^(\d+)\.(\d{2})\.(\d{3})$")
BS_ID = re.compile(r"^BS-\d+$")
BEYOND_SECTION = "Beyond the state of the art"
PLACEHOLDER = {"", "-", "?", "todo", "tbd", "tba", "unknown", "n/a", "na", "none", "placeholder", "..."}
API = "https://zenodo.org/api/records/{}"


def beyond_claims(root: Path) -> set[str] | None:
    """The ``BS-<n>`` identifiers of the SDD's section on the beyond, None when the SDD or the section is absent."""
    sdd = root / "docs" / "design" / "SDD.md"
    if not sdd.is_file():
        return None
    body: list[str] | None = None
    fenced = False
    for line in sdd.read_text(encoding="utf-8").splitlines():
        if re.match(r"^\s*(```+|~~~+)", line):
            fenced = not fenced
        if not fenced and (m := re.match(r"^##\s+(?:\d+\.\s*)?(.+?)\s*$", line)) and not line.startswith("###"):
            if body is not None:
                break
            if m[1].strip().lower() == BEYOND_SECTION.lower():
                body = []
            continue
        if body is not None:
            body.append(line)
    return None if body is None else set(re.findall(r"\bBS-\d+\b", "\n".join(body)))


def release_of(text: str) -> tuple[int, int, int] | None:
    m = RELEASE.match(text.strip()) if isinstance(text, str) else None
    return tuple(int(g) for g in m.groups()) if m else None


def entry_findings(i: int, entry: object) -> list[str]:
    at = f"product.json manuscripts[{i}]"
    if not isinstance(entry, dict):
        return [f"{at} is not an object"]
    out = [f"{at}: the field {key!r} is missing" for key in FIELDS if key not in entry]
    out += [f"{at}: {key!r} is not a field of an entry (kind, concept_doi, title, version, covers)" for key in sorted(set(entry) - set(FIELDS))]
    kind = entry.get("kind")
    if "kind" in entry and kind not in KINDS:
        out.append(f"{at}: kind is {kind!r}, it must be one of {', '.join(KINDS)}")
    doi = entry.get("concept_doi")
    if "concept_doi" in entry and not (isinstance(doi, str) and CONCEPT_DOI.match(doi)):
        out.append(f"{at}: concept_doi {doi!r} is not a Zenodo concept DOI of the form 10.5281/zenodo.<N>")
    title = entry.get("title")
    if "title" in entry and not (isinstance(title, str) and title.strip().lower() not in PLACEHOLDER):
        out.append(f"{at}: title is empty or a placeholder: write the manuscript's title as it is on Zenodo")
    version = entry.get("version")
    if "version" in entry:
        if not (isinstance(version, str) and version.strip().lower() not in PLACEHOLDER):
            out.append(f"{at}: version is empty or not a string: write the version of the Zenodo record")
        elif kind == "technical-report" and release_of(version) is None:
            out.append(f"{at}: version {version!r} is not X.XX.XXX: a technical report follows the product's releases")
    covers = entry.get("covers")
    if "covers" in entry:
        if not (isinstance(covers, list) and all(isinstance(c, str) and BS_ID.match(c) for c in covers)):
            out.append(f"{at}: covers is not a list of claim ids of the form BS-<n>")
        elif kind == "manuscript" and not covers:
            out.append(f"{at}: a manuscript covers at least one claim (covers: [\"BS-1\"]): it reports a beyond-the-state-of-the-art method")
    return out


def findings_of(root: Path, release: bool = False) -> list[str]:
    path = root / "product.json"
    if not path.is_file():
        return ["product.json is missing"]
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"product.json is not valid JSON ({exc})"]
    if not isinstance(doc, dict):
        return ["product.json is not a JSON object"]
    template = (root / SENTINEL).is_file()
    if "manuscripts" not in doc:
        if template:
            return []
        return [f"product.json has no 'manuscripts': a product declares its Zenodo manuscripts, at least one technical report "
                f"(\"kind\": \"technical-report\"), see {RULE} section 2"]
    entries = doc["manuscripts"]
    if not isinstance(entries, list):
        return ["product.json manuscripts is not a list of manuscript entries"]
    out: list[str] = []
    for i, entry in enumerate(entries):
        out += entry_findings(i, entry)
    dicts = [e for e in entries if isinstance(e, dict)]
    seen: dict[str, int] = {}
    for i, e in enumerate(entries):
        doi = e.get("concept_doi") if isinstance(e, dict) else None
        if isinstance(doi, str) and CONCEPT_DOI.match(doi):
            if doi in seen:
                out.append(f"product.json manuscripts lists the concept DOI {doi} twice (entries {seen[doi]} and {i})")
            seen.setdefault(doi, i)
    reports = [e for e in dicts if e.get("kind") == "technical-report"]
    if not template and not reports:
        out.append(f"product.json manuscripts has no technical-report: every product has a detailed technical report on Zenodo "
                   f"(CC BY 4.0, its own concept DOI), see {RULE} section 2")
    claims = beyond_claims(root)
    if claims is not None:
        for i, e in enumerate(entries):
            for c in e.get("covers", []) if isinstance(e, dict) and isinstance(e.get("covers"), list) else []:
                if isinstance(c, str) and BS_ID.match(c) and c not in claims:
                    out.append(f"product.json manuscripts[{i}] covers {c}, which the SDD's section '{BEYOND_SECTION}' does not list")
    version_file = root / "VERSION"
    current = release_of(version_file.read_text(encoding="utf-8")) if version_file.is_file() else None
    if current is not None:
        shown =f"{current[0]}.{current[1]:02d}.{current[2]:03d}"
        for i, e in enumerate(entries):
            if not (isinstance(e, dict) and e.get("kind") == "technical-report"):
                continue
            have = release_of(e.get("version", ""))
            if have is None:
                continue
            if have > current:
                out.append(f"product.json manuscripts[{i}] technical report version {e['version']} is ahead of VERSION {shown}")
            elif release and have != current:
                out.append(f"product.json manuscripts[{i}] technical report is at version {e['version']}, the release is {shown}: "
                           f"a release that changes a method, a data source or a result publishes the new version of the report "
                           f"on Zenodo before or with the release and records it here ({RULE} section 2)")
    return out


def fetch_record(number: int) -> dict | None:
    """The Zenodo record behind a concept id (the API answers with the latest version), None when it does not exist."""
    request = urllib.request.Request(API.format(number), headers={"Accept": "application/json", "User-Agent": "check_manuscripts"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310 (a fixed https URL)
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise RuntimeError(f"cannot read zenodo.org ({exc})") from exc


def zenodo_findings(entries: list[dict], fetch=fetch_record) -> list[str]:
    out: list[str] = []
    for e in entries:
        doi = e.get("concept_doi", "")
        m = CONCEPT_DOI.match(doi) if isinstance(doi, str) else None
        if not m:
            continue
        record = fetch(int(m.group(1)))
        if record is None:
            out.append(f"{doi} is not found on Zenodo: publish the record (tools/zenodo/) or correct the concept DOI")
            continue
        concept = record.get("conceptdoi")
        if concept and concept != doi:
            out.append(f"{doi}: Zenodo says the concept DOI of that record is {concept}")
        latest = (record.get("metadata") or {}).get("version")
        if latest is not None and latest != e.get("version"):
            out.append(f"{doi}: the latest Zenodo version is {latest}, product.json declares {e.get('version')}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(prog="check_manuscripts", description=__doc__.split(chr(10))[0])
    ap.add_argument("root", nargs="?", help="the repository root (default: this script's repository)")
    ap.add_argument("--release", action="store_true", help="also require every technical report's version to equal VERSION")
    ap.add_argument("--zenodo", action="store_true", help="also read the concept records on zenodo.org (opt-in, needs the network, never CI)")
    a = ap.parse_args()
    root = Path(a.root).resolve() if a.root else Path(__file__).resolve().parents[1]
    findings = findings_of(root, a.release)
    entries: list = []
    try:
        entries = json.loads((root / "product.json").read_text(encoding="utf-8")).get("manuscripts", [])
    except (OSError, ValueError, AttributeError):
        pass
    if a.zenodo and not findings:
        try:
            findings += zenodo_findings([e for e in entries if isinstance(e, dict)])
        except RuntimeError as exc:
            findings.append(str(exc))
    if findings:
        print("MANUSCRIPTS CHECK FAILED:")
        for f in findings:
            print(f"  - {f}")
        return 1
    n = len(entries) if isinstance(entries, list) else 0
    print(f"check_manuscripts: OK, {n} manuscript{'s' if n != 1 else ''} declared" + (", records read on Zenodo" if a.zenodo and n else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
