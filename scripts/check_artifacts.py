"""Validate CONTRACT 2 on disk (the pipeline -> web artifact contract) for DinHot: the index lists every case, baked or refused
(a refused case has no manifest and a reason); each baked case's manifest exists, names its trace, the trace exists, is
non-empty, within the 256 KiB lane gate, and its byte size matches the manifest; each lane matches its gate verdict; the
manifest and the trace agree on the case and on the methods; and the units gate (pipeline/core/units.py) holds over the
shipped documents. Stdlib only (runs in CI WITHOUT installing the package). Exit non-zero on any drift.

Used by scripts/smoke.* and by .github/workflows/ci.yml, the mechanical guard that a product can't regress to serving
artifacts that don't match their manifests.
Usage: python scripts/check_artifacts.py [repo_root]"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "data-pipeline"))

from pipeline.core import units  # noqa: E402

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE
DERIVED = ROOT / "data" / "derived"
MANIFESTS = DERIVED / "manifests"
TRACE_BYTES_GATE = 256 * 1024


def declared_absent() -> set[str]:
    """The paths the readiness document declares absent: the ``missing`` of every row whose state is ``partial``
    (catalog, Missing-data states). Empty when the document is absent or unreadable: nothing is tolerated then."""
    try:
        rows = json.loads((DERIVED / "readiness.json").read_text(encoding="utf-8")).get("contracts", [])
        return {m for r in rows if isinstance(r, dict) and r.get("state") == "partial"
                for m in r.get("missing", []) if isinstance(m, str)}
    except (OSError, ValueError, AttributeError):
        return set()


def main() -> int:
    idx_path = MANIFESTS / "index.json"
    if not idx_path.exists():
        print(f"FAIL: missing {idx_path} (run scripts/precompute.sh first)")
        return 1
    index = json.loads(idx_path.read_text(encoding="utf-8"))
    errs: list[str] = []
    tolerated = declared_absent()
    n_art = n_declared_absent = n_refused = 0

    def absent(rel: str, what: str, path: Path) -> None:
        """A declared-absent path is a warning (a partial bake builds); any other absence is drift."""
        nonlocal n_declared_absent
        if rel in tolerated:
            n_declared_absent += 1
            print(f"WARN: {what} {rel} is absent, as readiness.json declares (partial)")
        else:
            errs.append(f"missing {what}: {path}")

    ids = [e.get("case_id") for e in index.get("cases", [])]
    if ids != sorted(ids):
        errs.append("the index entries are not sorted by case_id")
    baked_ids = {e["case_id"] for e in index.get("cases", []) if e.get("status") == "baked"}
    if index.get("default_case") not in baked_ids:
        errs.append(f"default_case {index.get('default_case')!r} is not a baked case of the index")
    for entry in index.get("cases", []):
        cid = entry["case_id"]
        if entry.get("status") == "refused":
            n_refused += 1
            if entry.get("path") is not None or not entry.get("reason"):
                errs.append(f"{cid}: a refused case has no manifest path and carries its reason")
            if (MANIFESTS / f"{cid}.json").exists():
                errs.append(f"{cid}: refused in the index but a manifest exists")
            continue
        mp = DERIVED / entry["path"]
        if not mp.exists():
            absent(entry["path"], "manifest", mp)
            continue
        m = json.loads(mp.read_text(encoding="utf-8"))
        if m.get("case_id") != cid:
            errs.append(f"{cid}: the manifest's case_id is {m.get('case_id')!r}")
        art = m.get("artifact")
        if not isinstance(art, dict) or "path" not in art:
            errs.append(f"{cid}: the manifest names no artifact")
            continue
        n_art += 1
        ap = DERIVED / art["path"]
        if not ap.exists():
            absent(art["path"], "artifact", ap)
            continue
        size = ap.stat().st_size
        if size != art.get("bytes"):
            errs.append(f"byte drift {ap}: manifest={art.get('bytes')} disk={size}")
        if size == 0:
            errs.append(f"empty artifact: {ap}")
        if size > TRACE_BYTES_GATE:
            errs.append(f"{cid}: the trace is {size} bytes, over the {TRACE_BYTES_GATE} byte lane gate")
        if (m.get("gate") or {}).get("lane") != m.get("lane"):
            errs.append(f"lane/gate mismatch: {cid} {art['path']}")
        trace = json.loads(ap.read_text(encoding="utf-8"))
        if trace.get("case_id") != cid:
            errs.append(f"{cid}: the trace's case_id is {trace.get('case_id')!r}")
        if sorted(trace.get("methods", {})) != sorted(m.get("methods", {})):
            errs.append(f"{cid}: the trace and the manifest list different methods")
        if sorted(m.get("methods", {})) != sorted(m.get("params", {}).get("methods", [])):
            errs.append(f"{cid}: the manifest's methods differ from its params' methods")
    errs += [f"units: {p}" for p in units.check_tree(DERIVED)]
    if errs:
        print("CONTRACT 2 DRIFT:")
        for e in errs:
            print("  -", e)
        return 1
    print(f"CONTRACT 2 OK: {len(baked_ids)} baked and {n_refused} refused cases, {n_art} artifacts, manifests <-> artifacts "
          f"consistent, units gate holds" + (f" ({n_declared_absent} declared absent)." if n_declared_absent else "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
